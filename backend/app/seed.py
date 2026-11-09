import hashlib
import json
import sqlite3
from datetime import datetime

from .clock import SEASONS, SEASON_NAMES, catalog_year


CITY = "平城京市"
SPOTS = (
    ("watergate", "四季の水門", "水路のまち", "gate", "三つの水門を動かし、季節の水路に水を届ける。", 12, 20, "GATE-314", 8, 18, ""),
    ("sakura", "桜社", "桜の門前", "shrine", "門前を歩き、願いを記す。次の節目も、自分の希望で選べる。", 8, 20, "SAKURA-428", 8, 18, ""),
    ("coast", "凪の海辺", "海のまち", "coast", "春の砂浜、夏の海、秋の水面、冬の釣り。四季で変わる海を訪ねる。", 25, 30, "COAST-582", 8, 17, "2"),
    ("conference", "水都国際会議館", "会議のまち", "conference", "会議の合間に歩ける場所から、次はゆっくり訪れる旅へ。", 0, 10, "MEET-763", 8, 20, ""),
)

EXPERIENCES = (
    ("gate-spring", "watergate", "花を運ぶ水路", "spring", "桜の花びらを三つの庭へ送る、春の水門の謎。", "3〜5月", 20, "puzzle"),
    ("gate-summer", "watergate", "夕涼みの水路", "summer", "水を分けて日陰の庭を冷やす、夏の水門の謎。", "6〜8月", 20, "puzzle"),
    ("gate-autumn", "watergate", "紅葉を映す水路", "autumn", "朱・金・碧の庭に水を届ける、秋の水門の謎。", "9〜11月", 20, "puzzle"),
    ("gate-winter", "watergate", "灯りをつなぐ水路", "winter", "三つの灯りに水を送る、冬の水門の謎。", "12〜2月", 20, "puzzle"),
    ("shrine-wish", "sakura", "桜社で安産を願う", "all", "安産祈願を希望する人が選ぶ参拝。時期は自分の予定に合わせる。", "希望する時期に", 20, "event"),
    ("shrine-birth", "sakura", "桜社のお宮参り", "all", "希望する家族が選ぶ、お宮参りの旅。時期は家族の予定に合わせて相談する。", "希望する時期に", 30, "event"),
    ("shrine-shichigosan", "sakura", "桜社の七五三", "autumn", "秋の門前で節目を祝う。七五三を希望する人のための候補。", "9〜11月", 30, "event"),
    ("shrine-winter", "sakura", "冬の門前さんぽ", "winter", "灯りのともる門前を歩き、今年の旅を振り返る。", "12〜2月", 20, "activity"),
    ("coast-spring", "coast", "春の潮干狩り", "spring", "砂浜で貝を探す。潮の時間と開催日を確かめて出かける。", "3〜5月", 60, "activity"),
    ("coast-summer", "coast", "夏の海水浴", "summer", "凪の浜で海水浴。開設時間と海の状態を確認して楽しむ。", "6〜8月", 60, "activity"),
    ("coast-autumn", "coast", "秋の水面をSUPで進む", "autumn", "秋の海を岸から眺め、案内人とSUPへ。火曜休み。", "9〜11月", 60, "activity"),
    ("coast-winter", "coast", "冬の堤防で釣り", "winter", "冬の海辺を歩き、堤防の釣りを楽しむ。火曜休み。", "12〜2月", 60, "activity"),
    ("conference-spring", "conference", "会議の合間に春の水都を知る", "spring", "会議館の展示で水路と桜のまちを知り、次の行き先を選ぶ。", "3〜5月", 10, "activity"),
    ("conference-summer", "conference", "会議の合間に夏の水都を知る", "summer", "館内のまち案内から、夕涼みの水路や海辺へ旅をつなぐ。", "6〜8月", 10, "activity"),
    ("conference-autumn", "conference", "会議の合間に秋の水都を知る", "autumn", "館内のまち案内で紅葉の水路を知る。空き時間に歩ける道を探す。", "9〜11月", 10, "activity"),
    ("conference-winter", "conference", "会議の合間に冬の水都を知る", "winter", "館内のまち案内で灯りの水路を知り、次の旅の候補を残す。", "12〜2月", 10, "activity"),
)

SOLUTIONS = {
    "spring": {"beginner": [2, 3, 1], "advanced": [4, 2, 3]},
    "summer": {"beginner": [3, 1, 2], "advanced": [2, 4, 1]},
    "autumn": {"beginner": [1, 2, 3], "advanced": [3, 1, 4]},
    "winter": {"beginner": [2, 1, 4], "advanced": [1, 4, 2]},
}


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def seed_static(connection: sqlite3.Connection) -> None:
    for spot in SPOTS:
        values = list(spot)
        values[7] = fingerprint(values[7])
        connection.execute(
            "INSERT OR IGNORE INTO spots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values
        )
    connection.executemany(
        "INSERT OR IGNORE INTO experiences VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)", EXPERIENCES
    )


def seed_games(connection: sqlite3.Connection, current: datetime) -> None:
    for season in SEASONS:
        year = catalog_year(current, season)
        for difficulty in ("beginner", "advanced"):
            first, second, third = SOLUTIONS[season][difficulty]
            if difficulty == "beginner":
                clue = f"三つの水門の合計は{first + second + third}。碧の水門は{third}。朱の水門は{first}。残る水を金の水門へ。"
                hint = "朱と碧を先に合わせ、合計からその二つを引くと金の水門が決まります。"
            else:
                difference = second - first
                relation = f"金は朱より{difference}多い" if difference >= 0 else f"朱は金より{-difference}多い"
                clue = f"三つの合計は{first + second + third}。{relation}。朱＋金の2倍＋碧の3倍は{first + 2 * second + 3 * third}。"
                hint = "合計の式を重みつきの式から引くと、金＋碧の2倍が分かります。朱と金の差も使いましょう。"
            title = f"{SEASON_NAMES[season]}の水門・{'はじめて' if difficulty == 'beginner' else '奥の水路'}"
            puzzle = {"title": title, "instruction": "朱・金・碧の水門を0から5で合わせ、水を流してください。", "labels": ["朱の水門", "金の水門", "碧の水門"], "max_value": 5, "clue": clue}
            connection.execute(
                "INSERT OR IGNORE INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"gate-{season}-{difficulty}-{year}-v1", "watergate", title, season, difficulty,
                 "季節の水路に合う水量を探す。現地のしおりで訪問を記録してから挑戦。",
                 f"{year}.1", year, json.dumps(puzzle, ensure_ascii=False), json.dumps([first, second, third]), hint),
            )
