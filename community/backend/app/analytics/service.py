import json
from collections import Counter
from datetime import UTC, datetime, time, timedelta, timezone

from fastapi import HTTPException

from ..marketplace.service import Marketplace
from .origins import origin_summary
from .schemas import AnalyticsResponse

JST = timezone(timedelta(hours=9))
THRESHOLD = 5
PEOPLE = [('1-2', '1〜2人'), ('3-5', '3〜5人'), ('6-10', '6〜10人'), ('11-20', '11〜20人'), ('21+', '21人以上')]
NIGHTS = [('0', '日帰り'), ('1', '1泊'), ('2', '2泊'), ('3+', '3泊以上')]
BUDGET = [('under-10000', '1万円未満'), ('10000-29999', '1〜3万円未満'), ('30000-49999', '3〜5万円未満'), ('50000+', '5万円以上')]
DEFINITIONS = {
    'consultations': ('件', '期間内に開始した共有相談。終了済みの相談を含みます。'),
    'confirmed_users': ('人', '終了済み開催で実参加申告・他の参加者の確認・事業者確認が揃った利用者の実人数。'),
    'confirmed_visits': ('人回', '確認済み利用者と開催の組合せ数。同じ人の別開催は別に数えます。'),
    'completed_outings': ('回', '確認済みの利用者が1人以上いる終了済み開催数。'),
}


def clock_now():
    return datetime.now(UTC)


def object_json(value):
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError):
        return {}


def timestamp(value):
    try:
        result = datetime.fromisoformat(value)
        return result.astimezone(UTC) if result.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def bounded_rows(rows, field, lower, upper):
    result = []
    for row in rows:
        instant = timestamp(row[field])
        if instant is not None and lower <= instant <= upper:
            result.append(dict(row) | {'instant': instant})
    return result


def totals(consultations, visits):
    return {
        'consultations': len(consultations),
        'confirmed_users': len({row['user_id'] for row in visits}),
        'confirmed_visits': len({(row['outing_id'], row['user_id']) for row in visits}),
        'completed_outings': len({row['outing_id'] for row in visits}),
    }


def metrics(current, previous):
    return {
        key: dict(count=value, previous_count=previous[key], change_count=value - previous[key],
                  change_percent=round((value - previous[key]) * 100 / previous[key], 1) if previous[key] else None,
                  unit=DEFINITIONS[key][0], definition=DEFINITIONS[key][1])
        for key, value in current.items()
    }


def integer(value, maximum, minimum=0):
    return type(value) is int and minimum <= value <= maximum


def people_bin(conditions):
    value = conditions.get('planned_people')
    if not integer(value, 500, 1):
        return None
    return PEOPLE[next((index for index, limit in enumerate((2, 5, 10, 20)) if value <= limit), 4)][0]


def nights_bin(conditions):
    value = conditions.get('nights')
    if not integer(value, 30):
        return None
    return str(value) if value < 3 else '3+'


def budget_bin(conditions):
    value = conditions.get('budget_yen')
    if not integer(value, 100_000_000, 1):
        return None
    if (conditions.get('budget_basis'), conditions.get('budget_scope')) != ('per_person', 'plan_only'):
        return None
    return BUDGET[next((index for index, limit in enumerate((10000, 30000, 50000)) if value < limit), 3)][0]


def distribution(records, label, bins, classify, note=None):
    counts = Counter(classify(row) for row in records)
    missing = counts.pop(None, 0)
    known = len(records) - missing
    if not known:
        status, reason = 'no_data', '対象となる共有条件がありません。'
    elif len(records) < THRESHOLD or any(0 < count < THRESHOLD for count in counts.values()):
        status, reason = 'insufficient_sample', '5人未満の内訳が含まれるため、この項目の分布を表示しません。'
    else:
        status, reason = 'available', None
    if note:
        reason = f'{reason} {note}' if reason else note
    return dict(label=label, status=status, known_count=known, missing_count=missing,
                bins=[dict(key=key, label=name, count=counts[key] if status == 'available' else None) for key, name in bins],
                reason=reason)


def conditions_out(consultations):
    latest = {}
    for row in sorted(consultations, key=lambda row: (row['instant'], row['id']), reverse=True):
        if row['share_active'] and row['selected_by'] not in latest:
            shared = object_json(row['snapshot']).get('shared_conditions')
            latest[row['selected_by']] = shared if isinstance(shared, dict) else {}
    records = list(latest.values())
    return dict(
        population_unit='相談者（各人の期間内最新共有条件）', consultation_count=len(consultations),
        sample_count=len(records), unique_sharers=len(records),
        people=distribution(records, '予定人数', PEOPLE, people_bin),
        nights=distribution(records, '泊数', NIGHTS, nights_bin),
        budget_per_person=distribution(records, '1人あたり・プラン部分の予算', BUDGET, budget_bin,
            'グループ総額・旅全体の予算は対象外で、欠測に含みます。'),
    )


def daily_rows(start, days, consultations, visits):
    result = []
    consultation_days, visit_days = {}, {}
    for rows, grouped in ((consultations, consultation_days), (visits, visit_days)):
        for row in rows:
            grouped.setdefault(row['instant'].astimezone(JST).date(), []).append(row)
    for offset in range(days):
        day = (start + timedelta(days=offset)).date()
        result.append(dict(date=day.isoformat(), **totals(consultation_days.get(day, []), visit_days.get(day, []))))
    return result


class Analytics:
    def __init__(self, database):
        self.db = database
        self.market = Marketplace(database)

    @staticmethod
    def consultations(conn, provider_id, lower, upper):
        # Only the explicitly shared snapshot is read. Private requirements, messages,
        # photographs, preferences and survey files are deliberately absent.
        rows = conn.execute("""SELECT c.id,c.created_at,s.plan_id,s.snapshot,s.selected_by,
                (c.status='open' AND s.status='active' AND p.status='open' AND u.login_enabled=1
                 AND NOT EXISTS(SELECT 1 FROM circle_provider_invitations i
                     WHERE i.consultation_id=c.id AND i.status!='accepted')) AS share_active
            FROM consultations c JOIN plan_selections s ON s.id=c.selection_id
            JOIN provider_plans q ON q.id=s.plan_id AND q.provider_id=s.provider_id
            JOIN travel_parties p ON p.id=s.party_id JOIN users u ON u.id=s.selected_by
            WHERE s.provider_id=? AND julianday(c.created_at)>=julianday(?)
                AND julianday(c.created_at)<=julianday(?)""", (provider_id, lower.isoformat(), upper.isoformat()))
        return bounded_rows(rows, 'created_at', lower, upper)

    @staticmethod
    def visits(conn, provider_id, lower, upper):
        rows = conn.execute("""SELECT o.id AS outing_id,o.plan_id,o.starts_at,o.ends_at,a.user_id
            FROM daytrip_outings o
            JOIN provider_plans q ON q.id=o.plan_id AND q.provider_id=o.provider_id
            JOIN daytrip_participants a ON a.outing_id=o.id
            JOIN daytrip_participants witness ON witness.outing_id=o.id AND witness.user_id=a.confirmed_by
            WHERE o.provider_id=? AND o.status IN ('reporting','confirmed')
                AND a.accepted=1 AND a.claimed=1 AND a.provider_verified=1 AND a.revoked=0
                AND a.confirmed_by!=a.user_id AND witness.accepted=1 AND witness.claimed=1 AND witness.revoked=0
                AND julianday(o.ends_at)>=julianday(?) AND julianday(o.ends_at)<=julianday(?)
                AND julianday(o.starts_at)<julianday(o.ends_at)""", (provider_id, lower.isoformat(), upper.isoformat()))
        return [row for row in bounded_rows(rows, 'ends_at', lower, upper)
                if timestamp(row['starts_at']) is not None and timestamp(row['starts_at']) < row['instant']]

    @staticmethod
    def plans(conn, provider_id, consultations, visits):
        result = []
        for row in conn.execute("SELECT id,body FROM provider_plans WHERE provider_id=? AND status='published' ORDER BY id", (provider_id,)):
            title = object_json(row['body']).get('title')
            result.append(dict(id=row['id'], title=title if isinstance(title, str) else '公開プラン', status='published',
                **totals([item for item in consultations if item['plan_id'] == row['id']],
                         [item for item in visits if item['plan_id'] == row['id']])))
        return result

    def read(self, uid, provider_id, days=30):
        if type(days) is not int or days not in (30, 90, 365):
            raise HTTPException(422, '期間は30日・90日・365日から選んでください。')
        instant = clock_now().astimezone(UTC)
        today = instant.astimezone(JST).date()
        start = datetime.combine(today - timedelta(days=days - 1), time.min, JST)
        previous_start = start - timedelta(days=days)
        with self.db.transaction() as conn:
            self.market.staff(conn, uid, provider_id)
            consultations = self.consultations(conn, provider_id, previous_start, instant)
            visits = self.visits(conn, provider_id, previous_start, instant)
            current_consults = [row for row in consultations if row['instant'] >= start]
            current_visits = [row for row in visits if row['instant'] >= start]
            previous_consults = [row for row in consultations if row['instant'] < start]
            previous_visits = [row for row in visits if row['instant'] < start]
            conditions = conditions_out(current_consults)
            history = self.visits(conn, provider_id, datetime.min.replace(tzinfo=UTC), instant)
            return AnalyticsResponse(
                provider_id=provider_id, generated_at=instant.isoformat(),
                period=dict(days=days, start_date=start.date().isoformat(), end_date=today.isoformat(),
                    previous_start_date=previous_start.date().isoformat(), previous_end_date=(start.date() - timedelta(days=1)).isoformat()),
                summary=metrics(totals(current_consults, current_visits), totals(previous_consults, previous_visits)),
                daily=daily_rows(start, days, current_consults, current_visits),
                plans=self.plans(conn, provider_id, current_consults, current_visits), conditions=conditions,
                origins=origin_summary(conn, provider_id, current_visits, history),
                demographics={key: dict(reason=reason, missing_count=conditions['sample_count']) for key, reason in (
                    ('age', '年齢は本人の許可を得た情報として収集していません。'),
                    ('gender', '性別は本人の許可を得た情報として収集していません。'),
                    ('interests', '個人の関心は事業者への共有対象に含まれていません。'))},
                notes=[
                    '今日の値は取得時刻までです。前期間は直前の同じ日数で、今日に相当する日も終日を含みます。',
                    '利用人数は実参加申告・参加者間の確認・事業者確認が揃った記録です。予約や外部の来店検知ではありません。',
                    '日別・プラン別の実人数には重複があるため、足し合わせても期間全体の実人数にはなりません。',
                    '公開終了プランの過去実績も全体に含みます。プラン一覧は現在公開中のものだけです。',
                    '旅行条件の母数は現在も共有中の相談代表者です。参加予定人数や利用者全員の属性ではありません。',
                ],
            )
