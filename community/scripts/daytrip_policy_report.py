"""Reproducible D1 policy scenarios, not measured travel or revenue effects."""

import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "community/backend"))
from app.daytrip.service import RULES, rank  # noqa: E402
from app.daytrip.ranks import NAMES, VERSION
from app.daytrip.catalog import ROUTES  # noqa: E402


def main():
    route = ROUTES[0]
    distance = int(min(Decimal(str(route["one_way_km"])) * 2, RULES["distance_cap_km"]) // 10)
    regular = RULES["base_points"] + distance
    leader = regular + RULES["leader_points"]
    scenarios = []
    for count in (1, 2, 3, 5, 10):
        for role, total in (("一般参加", regular * count), ("毎回先達", leader * count), ("3人で先達を交代", regular * count + RULES["leader_points"] * ((count + 2) // 3))):
            scenarios.append(dict(completed=count, role=role, points=total, rank=rank(total)))
    # Hypothetical provider budget, not a seeded or offered benefit.
    price, percent, cap, count = 6000, 5, 500, 20
    discount = min(price * percent // 100, cap, price)
    report = dict(rule_version=RULES["version"], rank_policy_version=VERSION, route_id=route["id"],
                  assumptions=["別日に実施し全行程を確認", "すべての活動が直近365日内", "取消なし", "先達本人承諾と他参加者確認あり", "金銭特典資格には事業者の利用確認が別途必要", "実際の参加者・再訪率・売上の測定ではない"],
                  regular_points=regular, leader_points=leader, scenarios=scenarios,
                  cost_scenario=dict(price_yen=price, percent=percent, per_user_cap_yen=cap,
                                     max_uses=count, discount_yen=discount, total_yen=price-discount,
                                     cost_if_all_used_yen=discount*count, absolute_budget_cap_yen=cap*count))
    target = ROOT / "community/artifacts/daytrip-policy"
    target.mkdir(parents=True, exist_ok=True)
    (target / "scenarios.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# D1 ポイント・特典費用の試算", "", "実利用の測定ではない。全活動が直近365日内・別日開催・全行程参加・取消なしの計算比較。階級はR2。資格点には事業者の利用確認が必要。", "", f"{route['origin']}→{route['destination']} 片道{route['one_way_km']}kmでは参加者{regular}点、先達{leader}点。距離の20〜40km範囲では距離加点は4〜8点に留まり、基本100点と先達50点を中心に評価する。", "", "|確認済み開催数|役割|累積点|階級|", "|---:|---|---:|---:|"]
    lines.extend(f"|{row['completed']}|{row['role']}|{row['points']}|{NAMES[row['rank']-1]}|" for row in scenarios)
    lines += ["", "## 費用の仮定", "", f"一人料金{price:,}円、{percent}%、一人上限{cap:,}円、{count}枠を事業者が設定した場合、割引は{discount}円/人、適用後{price-discount:,}円。全枠利用時の割引負担は{discount*count:,}円。単価が変わっても設定上限の総額は{cap*count:,}円。この条件の特典を初期公開するものではない。", "", "## 判断と未測定", "", "近距離でも反復参加で段階が上がり、先達は同じ回数で早く進む。距離だけの水増し効果を抑える配分とする。先達になる人の偏り・作業時間・負担感、参加者の理解、実際の再訪率や事業者収益は未測定。今後の利用調査で確認し、試算値を実績として発表しない。"]
    (ROOT / "docs/DAYTRIP-POLICY-SCENARIOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"rule": RULES["version"], "scenarios": len(scenarios), "regular": regular, "leader": leader, "artifact": str(target / "scenarios.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
