"""Free monthly drawing using locally distributed, one-time provider codes."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta, timezone

from fastapi import HTTPException

from ..database import identifier
from ..daytrip.service import Daytrip
from ..marketplace.service import Marketplace

JST = timezone(timedelta(hours=9))
TERMS = ['無料・月1回（日本時間、全事業者共通）', '現地で配布する10分有効のコードを使用します。GPSによる位置確認ではありません。',
         '当選券は発行事業者のみで30日有効。換金・譲渡・他割引との併用はできません。', '抽選は相互確認と事業者の利用確認済み実績による特典資格階級を使います。',
         '事業者の月予算内で発行します。残予算300円未満では抽選を開始できません。']


def clock_now():
    return datetime.now(UTC)


def month_of(moment):
    return moment.astimezone(JST).strftime('%Y-%m')


def odds(level):
    probabilities = (50, 40, 10, 0) if level <= 3 else (30, 40, 25, 5) if level <= 6 else (10, 30, 40, 20)
    return [dict(amount_yen=value, probability_percent=chance) for value, chance in zip((0, 100, 200, 300), probabilities, strict=True)]


def sample(level):
    value = secrets.randbelow(100)
    total = 0
    for row in odds(level):
        total += row['probability_percent']
        if value < total:
            return row['amount_yen']
    raise RuntimeError('Invalid probability table')


def code_hash(conn, code):
    key = conn.execute("SELECT value FROM settings WHERE key='omikuji-code-pepper'").fetchone()[0]
    return hmac.new(bytes.fromhex(key), code.encode('ascii'), hashlib.sha256).hexdigest()


def policy(conn, pid, at):
    provider = conn.execute('SELECT id,name FROM providers WHERE id=? AND active=1', (pid,)).fetchone()
    if provider is None:
        raise HTTPException(404, '事業者が見つかりません。')
    row = conn.execute('SELECT * FROM omikuji_policies WHERE provider_id=?', (pid,)).fetchone()
    issued = conn.execute('SELECT COALESCE(SUM(amount_yen),0) FROM omikuji_draws WHERE provider_id=? AND month=?', (pid, month_of(at))).fetchone()[0]
    budget = row['monthly_budget_yen'] if row else 0
    return dict(id=pid, name=provider['name'], enabled=bool(row and row['enabled']), monthly_budget_yen=budget,
                issued_yen=issued, remaining_yen=max(0, budget-issued), version=row['version'] if row else 0)


def ready(conn, pid, at):
    value = policy(conn, pid, at)
    if not value['enabled'] or value['remaining_yen'] < 300:
        raise HTTPException(409, '事業者のおみくじ受付が停止中、または今月の予算が不足しています。')
    return value


def reward_out(conn, row, at):
    reward = conn.execute('SELECT * FROM omikuji_rewards WHERE draw_id=?', (row['id'],)).fetchone()
    if reward is None:
        return None
    status = 'redeemed' if reward['redeemed_at'] else 'expired' if datetime.fromisoformat(reward['expires_at']) <= at else 'available'
    return dict(id=reward['id'], provider_id=row['provider_id'], provider_name=row['provider_name'], title=f"おみくじ{row['amount_yen']}円引き",
                amount_yen=row['amount_yen'], status=status, expires_at=reward['expires_at'], redeemed_at=reward['redeemed_at'], created_at=row['created_at'])


def draw_out(conn, row, at):
    return {key: row[key] for key in ('id', 'provider_id', 'provider_name', 'month', 'amount_yen', 'rank_level', 'created_at')} | dict(reward=reward_out(conn, row, at))


DRAW_QUERY = 'SELECT d.*,p.name AS provider_name FROM omikuji_draws d JOIN providers p ON p.id=d.provider_id '


class Omikuji:
    def __init__(self, database):
        self.db = database
        self.market = Marketplace(database)

    def me(self, uid):
        at = clock_now()
        with self.db.transaction() as conn:
            personal, eligible = Daytrip.rank_states(conn, uid, at=at)
            rows = conn.execute(DRAW_QUERY + 'WHERE d.user_id=? ORDER BY d.created_at DESC LIMIT 36', (uid,)).fetchall()
            already = conn.execute('SELECT 1 FROM omikuji_draws WHERE user_id=? AND month=?', (uid, month_of(at))).fetchone()
            return dict(month=month_of(at), can_draw=already is None, rank=dict(level=eligible['rank'], name=eligible['name']), personal_rank=dict(level=personal['rank'], name=personal['name']),
                        odds=odds(eligible['rank']), draws=[draw_out(conn, row, at) for row in rows], terms=TERMS)

    def provider(self, uid):
        at = clock_now()
        with self.db.transaction() as conn:
            ids = [row[0] for row in conn.execute('SELECT s.provider_id FROM provider_staff s JOIN providers p ON p.id=s.provider_id WHERE s.user_id=? AND s.active=1 AND p.active=1', (uid,))]
            rows = conn.execute(DRAW_QUERY + 'JOIN provider_staff s ON s.provider_id=d.provider_id WHERE s.user_id=? AND s.active=1 AND p.active=1 AND d.amount_yen>0 ORDER BY d.created_at DESC LIMIT 100', (uid,)).fetchall()
            return dict(month=month_of(at), providers=[policy(conn, pid, at) for pid in ids], rewards=[reward_out(conn, row, at) for row in rows])

    def configure(self, uid, data):
        at = clock_now()
        with self.db.transaction(True) as conn:
            self.market.staff(conn, uid, data['provider_id'])
            old = policy(conn, data['provider_id'], at)
            if old['version'] != data['version']:
                raise HTTPException(409, '設定が更新されています。再読込してください。')
            if data['monthly_budget_yen'] < old['issued_yen'] or (data['enabled'] and data['monthly_budget_yen'] < 300):
                raise HTTPException(409, '予算は発行済み額以上、有効化時は300円以上にしてください。')
            conn.execute('INSERT INTO omikuji_policies VALUES(?,?,?,?,?) ON CONFLICT(provider_id) DO UPDATE SET enabled=excluded.enabled,monthly_budget_yen=excluded.monthly_budget_yen,version=excluded.version,updated_at=excluded.updated_at',
                         (data['provider_id'], int(data['enabled']), data['monthly_budget_yen'], old['version']+1, at.isoformat()))
            return policy(conn, data['provider_id'], at)

    def issue_code(self, uid, pid):
        at = clock_now()
        with self.db.transaction(True) as conn:
            self.market.staff(conn, uid, pid)
            current = ready(conn, pid, at)
            active = conn.execute('SELECT COUNT(*) FROM omikuji_codes WHERE provider_id=? AND consumed_at IS NULL AND expires_at>?', (pid, at.isoformat())).fetchone()[0]
            if active >= 20:
                raise HTTPException(429, '有効なコードが20件あります。利用または期限切れを待ってください。')
            code = self.fresh_code(conn)
            expires = (at + timedelta(minutes=10)).isoformat()
            conn.execute('INSERT INTO omikuji_codes VALUES(?,?,?,?,?,NULL,?)', (identifier(), pid, code_hash(conn, code), at.isoformat(), expires, uid))
            return dict(code=code, expires_at=expires, provider_id=pid, provider_name=current['name'])

    @staticmethod
    def fresh_code(conn):
        for _ in range(20):
            code = f'{secrets.randbelow(1_000_000):06d}'
            if conn.execute('SELECT 1 FROM omikuji_codes WHERE code_hash=?', (code_hash(conn, code),)).fetchone() is None:
                return code
        raise HTTPException(503, 'コードを作成できませんでした。時間をおいてください。')

    @staticmethod
    def attempt(conn, uid, at):
        window = int(at.timestamp()) // 60
        row = conn.execute('SELECT * FROM omikuji_attempts WHERE user_id=?', (uid,)).fetchone()
        count = row['attempts'] if row and row['window'] == window else 0
        if count >= 5:
            raise HTTPException(429, 'コードの試行が続いています。1分後に試してください。', headers={'Retry-After':'60'})
        conn.execute('INSERT INTO omikuji_attempts VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET window=excluded.window,attempts=excluded.attempts', (uid, window, count+1))

    def draw(self, uid, data):
        at = clock_now()
        with self.db.transaction(True) as conn:
            prior = conn.execute(DRAW_QUERY + 'WHERE d.user_id=? AND d.client_request_id=?', (uid, data['client_request_id'])).fetchone()
            if prior:
                saved_hash = conn.execute('SELECT code_hash FROM omikuji_codes WHERE id=?', (prior['code_id'],)).fetchone()[0]
                if not secrets.compare_digest(saved_hash, code_hash(conn, data['code'])):
                    raise HTTPException(400, '同じ送信番号でコードを変更することはできません。')
                return draw_out(conn, prior, at)
            self.attempt(conn, uid, at)
            try:
                return self.perform_draw(conn, uid, data, at)
            except HTTPException as caught:
                # Commit the failed PIN attempt while leaving code/draw/budget unchanged.
                error = caught
        raise error

    @staticmethod
    def perform_draw(conn, uid, data, at):
        if conn.execute('SELECT 1 FROM omikuji_draws WHERE user_id=? AND month=?', (uid, month_of(at))).fetchone():
            raise HTTPException(409, '今月のおみくじは実施済みです。')
        code = conn.execute('SELECT * FROM omikuji_codes WHERE code_hash=? AND consumed_at IS NULL AND expires_at>?', (code_hash(conn, data['code']), at.isoformat())).fetchone()
        if code is None:
            raise HTTPException(404, 'コードが無効、使用済み、または期限切れです。')
        ready(conn, code['provider_id'], at)
        _, eligible = Daytrip.rank_states(conn, uid, at=at)
        amount = sample(eligible['rank'])
        did = identifier()
        conn.execute('INSERT INTO omikuji_draws VALUES(?,?,?,?,?,?,?,?,?)', (did, uid, code['provider_id'], month_of(at), code['id'], data['client_request_id'], amount, eligible['rank'], at.isoformat()))
        conn.execute('UPDATE omikuji_codes SET consumed_at=? WHERE id=?', (at.isoformat(), code['id']))
        if amount:
            conn.execute('INSERT INTO omikuji_rewards(id,draw_id,expires_at) VALUES(?,?,?)', (identifier(), did, (at+timedelta(days=30)).isoformat()))
        row = conn.execute(DRAW_QUERY + 'WHERE d.id=?', (did,)).fetchone()
        return draw_out(conn, row, at)

    def redeem(self, uid, rid, data):
        at = clock_now()
        with self.db.transaction(True) as conn:
            row = conn.execute(DRAW_QUERY + 'JOIN omikuji_rewards r ON r.draw_id=d.id WHERE r.id=?', (rid,)).fetchone()
            if row is None:
                raise HTTPException(404, '特典が見つかりません。')
            self.market.staff(conn, uid, row['provider_id'])
            reward = reward_out(conn, row, at)
            if reward['status'] != 'available':
                raise HTTPException(409, 'この特典は利用済み、または期限切れです。')
            if data['purchase_yen'] < row['amount_yen'] or data['no_other_discount'] is not True:
                raise HTTPException(422, '利用額と他割引を併用しないことを確認してください。')
            conn.execute('UPDATE omikuji_rewards SET redeemed_at=?,redeemed_by=?,purchase_yen=?,no_other_discount=1 WHERE id=? AND redeemed_at IS NULL', (at.isoformat(), uid, data['purchase_yen'], rid))
            return reward_out(conn, row, at)
