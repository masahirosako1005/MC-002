"""Offline reference routes for N西市; not GPS tracks or live timetables.

Historical outings retain their own route snapshots in the database.
N西市 distances are explicit planning assumptions for a fictional city.
"""

# N西市 is a fictional destination. These are fixed planning assumptions,
# not measured routes, timetables, straight-line distances, or live navigation.
DESTINATION = {"name": "N西市", "prefecture": "大阪府", "latitude": 34.83, "longitude": 135.50}
ROUTES = [
    {"id": route_id, "origin": origin, "destination": "N西市・中央広場", "mode": "rail",
     "one_way_km": km, "one_way_minutes": minutes,
     "distance_note": "往復の予定を組むための参考値です。実際の経路・交通時間は出発前に確認してください。",
     "source_url": "", "time_source_url": "", "checked_on": "2026-11-10",
     "distance_basis": "fictional_planning_assumption"}
    for route_id, origin, km, minutes in (
        ("osaka-nnishi-reference", "大阪駅", 32.0, 50),
        ("suita-nnishi-reference", "吹田駅", 24.0, 45),
        ("kyoto-nnishi-reference", "京都駅", 38.0, 70),
        ("kobe-nnishi-reference", "神戸三宮駅", 40.0, 75),
        ("sakai-nnishi-reference", "堺駅", 39.0, 70),
    )
]

# Distinct experiences within the same fictional city. Distances remain explicit
# planning assumptions, never evidence of attendance or navigable itineraries.
for slug, destination, title, summary, km, minutes, cover in (
    ('market', '門前市場', '門前市場で昼ごはん', '朝市を歩いて、地元の食材を使った昼ごはんへ。', 31, 50, 'coffee'),
    ('satoyama', '北の里山', '里山の小道を歩く', '案内人と尾根道を歩き、山の茶屋で休憩します。', 36, 65, 'woodland'),
    ('riverside', '西川の河原', '川辺で外ごはん', '川沿いの散策と、河原で作る昼ごはんを組み合わせます。', 33, 55, 'riverside'),
    ('pottery', '土の工房', '土の工房で器づくり', '手びねりの器づくり。焼き上がりの受け取り方法も相談できます。', 30, 50, 'pottery'),
    ('teahouse', '門前の茶屋', '茶屋でお茶と季節のお菓子', 'お茶をいれる体験と、門前通りの小さな店を巡ります。', 32, 50, 'coffee'),
    ('oldroad', '西の古道', '古道と石段を巡る', '歴史案内を聞きながら、古道から見晴らし台まで歩きます。', 37, 65, 'woodland'),
    ('garden', '南の庭園', '庭園の散策と草花の写真', '季節の草花を探して庭園を一周。撮影のあとに休憩できます。', 29, 45, 'garden'),
):
    ROUTES.append({
        'id': 'osaka-nnishi-' + slug, 'origin': '大阪駅',
        'destination': 'N西市・' + destination, 'mode': 'rail',
        'one_way_km': float(km), 'one_way_minutes': minutes,
        'experience_title': title, 'summary': summary, 'cover_id': cover,
        'distance_note': '往復の予定を組むための参考値です。実際の経路・交通時間は出発前に確認してください。',
        'source_url': '', 'time_source_url': '', 'checked_on': '2026-11-10',
        'distance_basis': 'fictional_planning_assumption',
    })

# Curated code-owned catalog; never derive membership from editable place names.
CITY_ROUTE_IDS = frozenset(route['id'] for route in ROUTES)
