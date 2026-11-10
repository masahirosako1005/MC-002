"""R2 journey ranks. Lifetime balances are never reduced merely by ageing."""
from datetime import datetime, timedelta

VERSION = 'R2'
WINDOW_DAYS = 365
FLOOR_MAX = 4
NAMES = ('新客', '行者', '山伏', '先達', '大先達', '正大先達', '前鬼・後鬼', '別当', '大僧正', '勧進元')
THRESHOLDS = (0, 100, 300, 800, 1500, 2500, 4000, 6000, 9000, 13000)
LEGACY_LEVELS = {1: 1, 2: 3, 3: 4, 4: 5}


def rank(points, recent_points=None):
    """The optional recent value denotes that all points are still recent."""
    lifetime = max(1, sum(points >= threshold for threshold in THRESHOLDS))
    recent = points if recent_points is None else recent_points
    active = max(1, sum(recent >= threshold for threshold in THRESHOLDS))
    return max(min(lifetime, FLOOR_MAX), min(lifetime, active))


def next_demotion(points, recent, current, activities):
    if current <= FLOOR_MAX:
        return None
    for ended_at, value in sorted(activities):
        recent -= value
        if rank(points, recent) < current:
            return (ended_at + timedelta(days=WINDOW_DAYS)).isoformat()
    return None


def evaluate(points, activities, at):
    cutoff = at - timedelta(days=WINDOW_DAYS)
    recent_activities = [(ended_at, value) for ended_at, value in activities if cutoff < ended_at <= at and value > 0]
    recent = sum(value for _, value in recent_activities)
    current = rank(points, recent)
    next_level = current + 1 if current < len(NAMES) else None
    threshold = THRESHOLDS[current] if next_level else None
    return dict(policy_version=VERSION, rank=current, name=NAMES[current - 1], lifetime_points=points,
                recent_points=recent, lifetime_rank=rank(points), guaranteed_rank=min(rank(points), FLOOR_MAX),
                maintenance_points=THRESHOLDS[current - 1] if current > FLOOR_MAX else None,
                next_rank=next_level, next_rank_points=threshold,
                next_lifetime_points_needed=max(0, threshold - points) if threshold is not None else 0,
                next_recent_points_needed=max(0, threshold - recent) if next_level and next_level > FLOOR_MAX else 0,
                next_demotion_at=next_demotion(points, recent, current, recent_activities), evaluated_at=at.isoformat())


def benefit_level(conn, row):
    marker = conn.execute('SELECT value FROM settings WHERE key=?', ('daytrip-benefit-rank:' + row['id'],)).fetchone()
    return row['min_rank'] if marker and marker[0] == VERSION else LEGACY_LEVELS[row['min_rank']]


def benefit_policy(conn, row):
    marker = conn.execute('SELECT value FROM settings WHERE key=?', ('daytrip-benefit-rank:' + row['id'],)).fetchone()
    return VERSION if marker and marker[0] == VERSION else 'D1'


def capture_evidence(entries):
    """Freeze eligible event IDs, so later positive entries cannot repair a hold."""
    grouped = {}
    for row in entries:
        item = grouped.setdefault(row['outing_id'], dict(outing_id=row['outing_id'], ended_at=row['ends_at'], eligible_points=0, ledger_ids=[]))
        item['eligible_points'] += row['eligible_points']
        item['ledger_ids'].append(row['id'])
    return [item for item in grouped.values() if item['eligible_points'] > 0]


def evidence_status(evidence, entries, at):
    negatives = {}
    for row in entries:
        if row['eligible_points'] < 0:
            negatives.setdefault(row['outing_id'], []).append(row)
    activities = []
    for item in evidence:
        old_ids = set(item['ledger_ids'])
        reversed_points = sum(row['eligible_points'] for row in negatives.get(item['outing_id'], []) if row['id'] not in old_ids)
        activities.append((datetime.fromisoformat(item['ended_at']), max(0, item['eligible_points'] + reversed_points)))
    return evaluate(sum(value for _, value in activities), activities, at)


def legacy_eligible_points(entries, held_at):
    """D1 holds used lifetime credit: include old net credit and later reversals only."""
    grouped = {}
    for row in entries:
        if row['eligible_points'] < 0 or datetime.fromisoformat(row['created_at']) <= held_at:
            grouped[row['outing_id']] = grouped.get(row['outing_id'], 0) + row['eligible_points']
    return sum(max(0, value) for value in grouped.values())
