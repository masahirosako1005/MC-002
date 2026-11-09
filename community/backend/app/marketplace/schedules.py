from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def schedule_fields(plan):
    return dict(schedule_type=plan.get('schedule_type','on_request'),
                starts_at=plan.get('starts_at'),ends_at=plan.get('ends_at'))


def schedule_state(plan, current=None):
    if plan.get('schedule_type','on_request') == 'on_request':
        return 'on_request'
    current = current or datetime.now(timezone.utc)
    try:
        starts = datetime.fromisoformat(plan['starts_at'])
        ends = datetime.fromisoformat(plan['ends_at'])
        if starts.tzinfo is None or ends.tzinfo is None:
            return 'invalid'
        if current > ends:
            return 'ended'
        return 'upcoming' if current < starts else 'ongoing'
    except (KeyError,TypeError,ValueError):
        return 'invalid'


def schedule_match(plan, date_start):
    state = schedule_state(plan)
    reasons,excluded,unknowns = [],[],[]
    if state in ('ended','invalid'):
        excluded.append('開催期間が終了しています' if state=='ended' else '開催日時を確認できません')
    elif state == 'on_request':
        unknowns.append('日程は相談')
    elif date_start:
        starts = datetime.fromisoformat(plan['starts_at']).astimezone(JST).date().isoformat()
        ends = datetime.fromisoformat(plan['ends_at']).astimezone(JST).date().isoformat()
        if starts <= date_start <= ends:
            reasons.append('希望日が登録された開催期間内')
            unknowns.append('希望日の出発・空席は事業者に確認が必要')
        else:
            excluded.append('希望日が登録された開催期間外')
    return state,reasons,excluded,unknowns
