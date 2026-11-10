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
