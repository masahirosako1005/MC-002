from collections import defaultdict
from datetime import datetime, time, timedelta

from fastapi import HTTPException

from ..residence.catalog import DESTINATION
from . import city_scope
from .city_privacy import REASON, counts, first_days, origins, safe_period
from .city_schemas import CityAnalyticsResponse
from .service import JST

DEFINITIONS = {
    'visitors': ('人', '対象期間に市内の確認済み利用がある実人数。事業者をまたぐ重複を除きます。'),
    'returning_visitors': ('人', '当期の利用より前の別の日本時間の日にも市内の確認済み利用がある実人数。'),
    'visit_days': ('人日', '利用者と日本時間の利用日の組合せ数。同日他店の利用を重ねて数えません。'),
    'participations': ('人回', '利用者と開催の組合せ数。同日でも別開催は別に数えます。'),
}


def summary(current, previous, current_safe, previous_safe):
    result = {}
    for key, (unit, definition) in DEFINITIONS.items():
        both = current_safe and previous_safe
        result[key] = dict(count=current[key] if current_safe else None,
            previous_count=previous[key] if previous_safe else None,
            change_count=current[key] - previous[key] if both else None,
            change_percent=round((current[key] - previous[key]) * 100 / previous[key], 1) if both and previous[key] else None,
            unit=unit, definition=definition,
            status='available' if current_safe else 'insufficient_sample', reason=None if both else REASON)
    return result


def daily(rows, earliest, start, days, period_safe):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['day']].append(row)
    allowed = period_safe and all(safe_period(items, earliest) for items in grouped.values())
    items = []
    for offset in range(days):
        day = start.date() + timedelta(days=offset)
        values = counts(grouped.get(day, []), earliest)
        items.append(dict(date=day.isoformat(), **{key: value if allowed else None for key, value in values.items()}))
    return dict(status=('available' if rows else 'no_data') if allowed else 'insufficient_sample',
                reason=None if allowed else REASON, items=items)


def provider_breakdown(providers, rows, allowed):
    items = []
    for provider in providers:
        records = [row for row in rows if row['provider_id'] == provider['id']]
        values = dict(visitors=len({row['user_id'] for row in records}),
            participations=len({(row['user_id'], row['outing_id']) for row in records}),
            completed_outings=len({row['outing_id'] for row in records}))
        items.append(provider | {key: value if allowed else None for key, value in values.items()})
    return dict(status=('available' if rows else 'no_data') if allowed else 'insufficient_sample',
                reason=None if allowed else REASON, items=items)


def trend_buckets(rows, earliest, start, days, interval):
    result = []
    for offset in range(0, days, interval):
        first = start.date() + timedelta(days=offset)
        last = start.date() + timedelta(days=min(days, offset + interval) - 1)
        records = [row for row in rows if first <= row['day'] <= last]
        result.append((dict(date=first.isoformat(), end_date=last.isoformat(), **counts(records, earliest)),
                       safe_period(records, earliest)))
    return result


def trend(rows, earliest, start, days, period_safe):
    if not period_safe:
        return dict(status='insufficient_sample', reason=REASON, interval_days=days, items=[])
    for interval in dict.fromkeys((7, 14, 30, days)):
        buckets = trend_buckets(rows, earliest, start, days, interval)
        if all(allowed for _, allowed in buckets):
            return dict(status='available' if rows else 'no_data', reason=None, interval_days=interval,
                        items=[item for item, _ in buckets])
    # The full-period case above is safe whenever period_safe is true.
    return dict(status='insufficient_sample', reason=REASON, interval_days=days, items=[])


class CityAnalytics:
    def __init__(self, database):
        self.db = database

    def read(self, uid, provider_id, days=30):
        if type(days) is not int or days not in (30, 90, 365):
            raise HTTPException(422, '期間は30日・90日・365日から選んでください。')
        at = city_scope.clock_now()
        today = at.astimezone(JST).date()
        start = datetime.combine(today - timedelta(days=days - 1), time.min, JST)
        previous_start = start - timedelta(days=days)
        with self.db.transaction() as conn:
            providers = city_scope.registered_providers(conn, uid, provider_id, self.db)
            history = city_scope.city_visits(conn, at)
            earliest = first_days(history)
            current = [row for row in history if row['instant'] >= start]
            previous = [row for row in history if previous_start <= row['instant'] < start]
            current_safe, previous_safe = safe_period(current, earliest), safe_period(previous, earliest)
            return CityAnalyticsResponse(
                city=DESTINATION, generated_at=at.isoformat(),
                period=dict(days=days, start_date=start.date().isoformat(), end_date=today.isoformat(),
                    previous_start_date=previous_start.date().isoformat(), previous_end_date=(start.date() - timedelta(days=1)).isoformat()),
                provider_count=len(providers), published_plan_count=sum(row['published_plan_count'] for row in providers),
                plan_categories=city_scope.plan_categories(conn),
                summary=summary(counts(current, earliest), counts(previous, earliest), current_safe, previous_safe),
                daily=daily(current, earliest, start, days, current_safe),
                trend=trend(current, earliest, start, days, current_safe),
                providers=provider_breakdown(providers, current, current_safe),
                origins=origins(city_scope.profiles(conn), current, earliest, current_safe),
                notes=[
                    '対象はサーバー設定でN西市に登録され、有効な事業者です。プランや表示名の地域文字列では所属を決めません。',
                    'N西市の対象経路で記録された終了済み開催だけを集計します。旧地域の履歴や未確認の予定を市の成果へ置き換えません。',
                    '利用実績は参加者と事業者の確認記録であり、外部で検知した人流ではありません。',
                    '事業者別実人数は重複するため、市全体の実人数を求めるために足し合わせないでください。',
                    '公開分野は公開プランのタグの本数です。複数の分野を持つプランをそれぞれ数えるため合計はプラン総数と一致しません。利用者の属性ではありません。',
                    '5人未満の集団や初回・再訪・事業者の組合せに少数がある場合、全体又は内訳全体の数値を非表示にします。0と非表示は異なります。',
                    '少人数セルの非表示であり、重なる期間や取得時刻の差、別に知る参加者情報からの推測まで防ぐ匿名化保証はありません。',
                    '今日の値は取得時刻までです。前期間は直前の同じ日数です。相談本文・写真・私的条件や個人IDは含みません。',
                ],
            )
