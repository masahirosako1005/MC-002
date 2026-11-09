"""Read five supplied CSVs locally; emit aggregates only, never personal rows.

This is a design-data audit, not a profile inference or community assignment.
Only fixed project reports and one aggregate plot are written. Source files are never modified.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from statistics import correlation, StatisticsError


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("C:/AI-Sprint/sample-data")
OUTPUT = ROOT / "artifacts/community-sample-summary.json"
REPORT = ROOT / "docs/COMMUNITY-SAMPLE-ANALYSIS.md"
CORRELATIONS = ROOT / "artifacts/community-correlation-summary.json"
FIGURE = ROOT / "outputs/community-data-correlations.png"
SATISFACTION = {"大変不満": 1, "やや不満": 2, "普通": 3, "やや満足": 4, "大変満足": 5}
FILES = {
    "after": ("08_アンケート回答_参加後.csv", "user_id"),
    "before": ("09_アンケート回答_登録時.csv", "user_id"),
    "stamps": ("12_スタンプ獲得履歴.csv", "ユーザID"),
    "users": ("13_ユーザー一覧.csv", "ユーザーID"),
    "rewards": ("18_特典獲得履歴.csv", "user_id"),
}
TEXT_TOPICS = {
    "自然・景観": ("自然", "景色", "風景", "山", "海", "川", "花", "紅葉"),
    "食事": ("食事", "食べ", "料理", "グルメ", "ランチ", "カフェ", "居酒屋"),
    "歴史・文化": ("歴史", "文化", "神社", "寺", "美術", "博物館"),
    "体験・活動": ("体験", "活動", "登山", "ハイキング", "サイクリング", "ボードゲーム"),
    "移動・案内": ("移動", "案内", "アクセス", "駐車", "地図", "交通"),
}
MIN_CATEGORY_COUNT = 10


def protected_count(value: int) -> int | str:
    return value if value == 0 or value >= MIN_CATEGORY_COUNT else "1〜9（非表示）"


def safe_categories(counts: Counter) -> dict:
    # Fixed broad labels only. No raw response value becomes a JSON key.
    return {label: protected_count(count) for label, count in counts.items()}


def age_band(value: str) -> str:
    match = re.fullmatch(r"\s*(\d{1,3})\s*(?:歳|代)?(?:以上)?\s*", value)
    if not match:
        return "形式不明・未回答"
    age = int(match.group(1))
    if age < 0 or age > 119:
        return "形式不明・未回答"
    if age < 20:
        return "20歳未満"
    if age >= 70:
        return "70歳以上"
    return f"{age // 10 * 10}代"


def parse_date(value: str):
    try:
        return datetime.fromisoformat(value.strip().replace("/", "-").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def read_sources():
    tables = {}
    file_reports = []
    for kind, (name, id_column) in FILES.items():
        raw = (SOURCE / name).read_bytes()
        encoding = None
        for candidate in ("utf-8-sig", "cp932"):
            try:
                decoded = raw.decode(candidate)
                encoding = candidate
                break
            except UnicodeDecodeError:
                continue
        if encoding is None:
            raise RuntimeError("サンプルの文字コードを解釈できません。個票は出力しません。")
        reader = csv.DictReader(io.StringIO(decoded))
        headers = reader.fieldnames or []
        if id_column not in headers:
            raise RuntimeError("サンプルのID列構成が変わっています。個票は出力しません。")
        rows = list(reader)
        malformed = sum(None in row or any(value is None for value in row.values()) for row in rows)
        if malformed:
            raise RuntimeError("サンプルに列数不一致があります。個票は出力しません。")
        ids = [row[id_column].strip() for row in rows]
        tables[kind] = rows
        file_reports.append({
            "kind": kind, "name": name, "encoding": encoding,
            "sha256_before": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "headers": headers,
            "id_column": id_column, "unique_users": len(set(ids) - {""}),
            "missing_ids": sum(not value for value in ids),
            "duplicate_complete_rows": len(rows) - len({tuple(row[column] for column in headers) for row in rows}),
            "nonempty_by_column": {column: protected_count(sum(bool(row[column].strip()) for row in rows)) for column in headers},
        })
    return tables, file_reports


def analyze():
    tables, files = read_sources()
    users = {row["ユーザーID"].strip(): row for row in tables["users"]}
    ids = {kind: {row[id_column].strip() for row in tables[kind] if row[id_column].strip()}
           for kind, (_, id_column) in FILES.items()}
    joins = {kind: {"matched_unique_users": len(values & ids["users"]),
                    "unmatched_unique_users": len(values - ids["users"]),
                    "master_users_without_rows": len(ids["users"] - values)} for kind, values in ids.items() if kind != "users"}
    before_by_id = {row["user_id"].strip(): row for row in tables["before"]}
    age_counts = Counter(age_band(row["年代"].strip()) for row in tables["users"])
    age_mismatch = sum(age_band(users[user]["年代"]) != age_band(row["2489_年齢"])
                       for user, row in before_by_id.items() if user in users)

    stamp_counts = Counter(row["ユーザID"].strip() for row in tables["stamps"])
    reward_counts = Counter(row["user_id"].strip() for row in tables["rewards"])
    days = defaultdict(set)
    unique_spots = set()
    dates = []
    invalid_dates = 0
    for row in tables["stamps"]:
        parsed = parse_date(row["獲得日時"])
        if parsed is None:
            invalid_dates += 1
        else:
            days[row["ユーザID"].strip()].add(parsed.date().isoformat())
            dates.append(parsed)
        unique_spots.add(row["スポット名"].strip())
    day_counts = Counter({"履歴なし": 0, "1日": 0, "2日以上": 0})
    for user in users:
        count = len(days[user])
        day_counts["履歴なし" if count == 0 else "1日" if count == 1 else "2日以上"] += 1
    stamp_mismatch = reward_mismatch = invalid_totals = 0
    for user, row in users.items():
        try:
            stamp_mismatch += int(row["スタンプ獲得数"]) != stamp_counts[user]
            reward_mismatch += int(row["特典獲得数"]) != reward_counts[user]
        except ValueError:
            invalid_totals += 1

    after_headers = next(item["headers"] for item in files if item["kind"] == "after")
    free_columns = [column for column in after_headers if "良かった点" in column or "要望" in column]
    topic_users = {topic: set() for topic in TEXT_TOPICS}
    free_nonempty = {}
    for column in free_columns:
        free_nonempty[column] = protected_count(sum(bool(row[column].strip()) for row in tables["after"]))
    for row in tables["after"]:
        text = "\n".join(row[column] for column in free_columns)
        for topic, words in TEXT_TOPICS.items():
            if any(word in text for word in words):
                topic_users[topic].add(row["user_id"].strip())
    text_summary = {
        "nonempty_by_field": free_nonempty,
        "fixed_keyword_topic_respondents": {topic: protected_count(len(values)) for topic, values in topic_users.items()},
        "method": "固定キーワードの部分一致。自由記述2列を合算しID単位で重複除去。複数カテゴリ該当あり。肯定/否定/要望を区別せず、好み・趣味の判定ではない。",
        "keywords": TEXT_TOPICS,
        "minimum_reported_nonzero_category_count": MIN_CATEGORY_COUNT,
        "exact_hobby_labels_present": False,
    }
    for item in files:
        after = hashlib.sha256((SOURCE / item["name"]).read_bytes()).hexdigest()
        item["sha256_after"] = after
        item["unchanged"] = after == item["sha256_before"]
    if not all(item["unchanged"] for item in files):
        raise RuntimeError("読込中に元ファイルが変化しました。集計を確定しません。")
    summary = {
        "analyzed_at_utc": datetime.now(timezone.utc).isoformat(), "source_directory": str(SOURCE),
        "source_unchanged": True, "analysis_scope": "ローカル実読込・全行集計。個人嗜好推定/集団割当/写真生成なし。",
        "files": files, "user_count": len(users), "joins": joins,
        "master_duplicate_user_rows": len(tables["users"]) - len(users),
        "registration_duplicate_user_rows": len(tables["before"]) - len(before_by_id),
        "age_bands": safe_categories(age_counts), "age_band_mismatch_between_user_and_registration": protected_count(age_mismatch),
        "history": {"stamp_rows": len(tables["stamps"]), "reward_rows": len(tables["rewards"]),
                    "unique_spot_name_values": len(unique_spots - {""}), "invalid_stamp_dates": invalid_dates,
                    "stamp_month_range": [min(dates).strftime("%Y-%m"), max(dates).strftime("%Y-%m")] if dates else None,
                    "users_by_distinct_stamp_days": safe_categories(day_counts),
                    "master_stamp_count_mismatch_users": protected_count(stamp_mismatch),
                    "master_reward_count_mismatch_users": protected_count(reward_mismatch), "invalid_master_count_rows": invalid_totals},
        "survey_after": {"respondents": len(ids["after"]), "registered_users": len(users),
                         "response_coverage_percent": round(100 * len(ids["after"] & ids["users"]) / len(users), 1) if users else None,
                         **text_summary},
        "availability": {"photo_files_in_source_directory": sum(path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".avif"} for path in SOURCE.iterdir() if path.is_file()),
                         "community_membership_columns": False, "confirmed_hobby_tag_columns": False,
                         "travel_preference_columns": False, "preference_portability_consent_columns": False,
                         "match_participation_consent_columns": False, "trip_id_columns": False,
                         "source_of_availability_findings": "今回の5CSVの全ヘッダーを確認。自由記述中の言及を専用項目や正解ラベルと扱わない。画像の件数は指定ディレクトリ直下の対応拡張子による。"},
        "privacy": {"raw_identifiers_retained": False, "raw_free_text_retained": False, "individual_rows_retained": False,
                    "cross_tabs_published": False, "individual_preference_inference": False, "community_assignment": False,
                    "external_transmission": False,
                    "suppression": "非ゼロで10人/件未満のカテゴリは数値非表示。小集団との交差集計は作らない。個人識別子をハッシュ化して出力することもない。これは匿名性の形式保証ではない。"},
    }
    return summary, tables


def average_ranks(values):
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    begin = 0
    while begin < len(ordered):
        end = begin + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[begin]]:
            end += 1
        rank = (begin + 1 + end) / 2
        for position in range(begin, end):
            ranks[ordered[position]] = rank
        begin = end
    return ranks


def spearman(left, right):
    pairs = [(a, b) for a, b in zip(left, right) if a is not None and b is not None]
    if len(pairs) < 2:
        return None, len(pairs)
    try:
        rho = correlation(average_ranks([a for a, _ in pairs]), average_ranks([b for _, b in pairs]))
    except StatisticsError:
        return None, len(pairs)
    return max(-1.0, min(1.0, rho)), len(pairs)


def correlations(tables, summary):
    assert average_ranks([1, 1, 3, 2]) == [1.5, 1.5, 4.0, 3.0]
    assert abs(spearman([1, 2, 3], [3, 2, 1])[0] + 1) < 1e-12
    assert spearman([1, 1], [1, 2]) == (None, 2)
    assert spearman([1, None, 3], [1, 2, 3])[1] == 2
    users = [row["ユーザーID"].strip() for row in tables["users"]]
    counts = Counter(row["ユーザID"].strip() for row in tables["stamps"])
    rewards = Counter(row["user_id"].strip() for row in tables["rewards"])
    days, spots = defaultdict(set), defaultdict(set)
    for row in tables["stamps"]:
        user = row["ユーザID"].strip()
        parsed = parse_date(row["獲得日時"])
        if parsed is not None:
            days[user].add(parsed.date())
        if row["スポット名"].strip():
            spots[user].add(row["スポット名"].strip())
    column = next(name for name in tables["after"][0] if "満足度" in name)
    satisfaction = {row["user_id"].strip(): SATISFACTION.get(row[column].strip()) for row in tables["after"]}
    unknown_answers = sum(row[column].strip() not in SATISFACTION for row in tables["after"])
    variables = [
        {"id": "stamp_rows", "label": "スタンプ履歴件数", "plot_label": "スタンプ\n履歴件数", "source": "12_スタンプ獲得履歴.csv の利用者別行数", "unit": "件"},
        {"id": "stamp_days", "label": "スタンプ記録日数", "plot_label": "スタンプ\n記録日数", "source": "12_スタンプ獲得履歴.csv 獲得日時の日付の異なり数", "unit": "日"},
        {"id": "distinct_spots", "label": "異なるスポット数", "plot_label": "異なる\nスポット数", "source": "12_スタンプ獲得履歴.csv スポット名の異なる値の数。施設IDによる同定ではない", "unit": "種類"},
        {"id": "reward_rows", "label": "特典履歴件数", "plot_label": "特典\n履歴件数", "source": "18_特典獲得履歴.csv の利用者別行数。利用・消費を確認する列はない", "unit": "件"},
    ]
    vectors = [[counts[user] for user in users], [len(days[user]) for user in users],
               [len(spots[user]) for user in users], [rewards[user] for user in users]]
    if unknown_answers == 0 and len(set(satisfaction.values()) - {None}) >= 2:
        variables.append({"id": "satisfaction", "label": "満足度（順序尺度）", "plot_label": "満足度\n（順序尺度）", "source": "08_アンケート回答_参加後.csv アンケート①(満足度を教えてください)", "unit": "順序"})
        vectors.append([satisfaction.get(user) for user in users])
    pairs = []
    rho_matrix, n_matrix = [], []
    for i, first in enumerate(variables):
        rhos, ns = [], []
        for j, second in enumerate(variables):
            rho, n = spearman(vectors[i], vectors[j])
            rhos.append(rho)
            ns.append(n)
            if i <= j:
                pairs.append({"first": first["id"], "second": second["id"], "n": n, "rho": rho,
                              "status": "computed" if rho is not None else "undefined_insufficient_or_constant"})
        rho_matrix.append(rhos)
        n_matrix.append(ns)
    return {
        "analyzed_at_utc": summary["analyzed_at_utc"], "method": "Spearman rho: Pearson correlation of average ranks; ties use average ranks; pairwise complete observations.",
        "source_sha256": {item["name"]: item["sha256_before"] for item in summary["files"]},
        "population": len(users), "variables": variables, "pairs": pairs, "rho_matrix": rho_matrix, "n_matrix": n_matrix,
        "satisfaction_mapping": SATISFACTION, "satisfaction_unknown_rows": unknown_answers,
        "satisfaction_respondents": sum(value is not None for value in satisfaction.values()),
        "satisfaction_missing_master_users": sum(user not in satisfaction for user in users),
        "satisfaction_response_counts": safe_categories(Counter(row[column].strip() for row in tables["after"] if row[column].strip() in SATISFACTION)),
        "missingness": "履歴の対応行なしは『提供ファイル内で観測した件数0』。実際の活動なし/完全な収録を保証しない。満足度未回答は欠測としてペア単位で除外し、0補完しない。",
        "count_discrepancy": {"master_reward_count_mismatch_users": summary["history"]["master_reward_count_mismatch_users"], "decision": "特典は一覧の集計列でなく履歴行数を使用。差の原因・集計期間・取消状態は未確認。"},
        "limitations": ["探索的・記述的な相関で、因果を示さない", "スタンプ件数/記録日数/スポット数は同じ履歴から派生し構造的に関連する", "特典獲得とスタンプ条件の制度上の関係は未確認", "満足度は回答者に偏る可能性がある", "趣味適合、人物の相性、再訪率へ読み替えない", "無分散・n不足は計算不可。p値や有意性判定を表示しない", "個票・散布図・識別子を出力しない"],
    }


def render_correlations(data, summary):
    # A local static scientific plot; no remote fonts or analytics endpoints.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np

    candidates = [Path("C:/Windows/Fonts/meiryo.ttc"), Path("C:/Windows/Fonts/YuGothR.ttc"),
                  Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    font_path = next((path for path in candidates if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("日本語フォントが見つかりません。図の生成を止めます。")
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=str(font_path)).get_name(),
                         "axes.unicode_minus": False, "font.size": 12})
    figure = plt.figure(figsize=(11.5, 11), facecolor="#f8fafb")
    axis = figure.add_axes((0.17, 0.26, 0.64, 0.55))
    values = np.array([[np.nan if value is None else value for value in row] for row in data["rho_matrix"]])
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad("#dfe5e9")
    image = axis.imshow(values, vmin=-1, vmax=1, cmap=cmap)
    labels = [item["plot_label"] for item in data["variables"]]
    axis.set_xticks(range(len(labels)), labels, fontsize=11)
    axis.set_yticks(range(len(labels)), labels, fontsize=11)
    axis.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False, length=0, pad=11)
    axis.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
    axis.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    axis.grid(which="minor", color="#f8fafb", linewidth=3)
    axis.tick_params(which="minor", length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)
    for i, row in enumerate(data["rho_matrix"]):
        for j, rho in enumerate(row):
            label = "計算不可" if rho is None else "ρ ≈ 0.00" if abs(rho) < 0.005 else f"ρ = {rho:+.2f}"
            color = "white" if rho is not None and abs(rho) >= 0.65 else "#182833"
            axis.text(j, i, f"{label}\nn = {data['n_matrix'][i][j]}", ha="center", va="center", fontsize=12, color=color, linespacing=1.8)
    color_axis = figure.add_axes((0.85, 0.285, 0.022, 0.49))
    bar = figure.colorbar(image, cax=color_axis, ticks=[-1, -0.5, 0, 0.5, 1])
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0, labelsize=10)
    bar.set_label("順位相関 ρ", fontsize=11, labelpad=12)
    figure.text(0.07, 0.955, "旅行記録の相関", fontsize=25, fontweight="bold", color="#122c3d")
    figure.text(0.07, 0.912, f"提供CSV {data['population']}人 ｜ Spearman順位相関 ｜ 各セルに係数と対応人数", fontsize=12, color="#465b67")
    figure.text(0.07, 0.878, f"履歴の4指標は{data['population']}人。満足度との比較は回答のある{data['satisfaction_respondents']}人。", fontsize=11, color="#465b67")
    notes = [
        "読み方：＋は同じ方向、−は逆方向。0に近いほど単調な関係が弱い。",
        f"同順位は平均順位。満足度は5段階の順序として扱い、未回答{data['satisfaction_missing_master_users']}人は除外。",
        "履歴がない場合の0は、提供ファイル内の記録0件。実際の活動なしを意味しない。",
        f"特典は履歴行数を使用。一覧の集計列と{summary['history']['master_reward_count_mismatch_users']}人で不一致があり、原因は未確認。",
        "件数・日数・スポット数は同じ履歴から派生するため、構造的に関連する。",
        "因果関係・趣味の相性・再訪率を示す図ではない。個人の点や識別子は表示しない。",
    ]
    for index, line in enumerate(notes):
        figure.text(0.07, 0.205 - index * 0.027, line, fontsize=10, color="#344b59")
    figure.text(0.07, 0.025, "出典：C:/AI-Sprint/sample-data の利用者・履歴・参加後アンケートCSV。集計条件とハッシュは分析文書参照。", fontsize=8.6, color="#526874")
    figure.savefig(FIGURE, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)
    data["plot"] = {"path": "outputs/community-data-correlations.png", "library": "matplotlib", "version": matplotlib.__version__,
                    "dimensions_pixels": [2070, 1980], "font": font_path.name}


def render_report(s, association):
    lines = ["# 閉じた旅行コミュニティ構想に向けたサンプル分析", "",
             "## 確認した事実", "",
             f"実読込時刻（UTC）：{s['analyzed_at_utc']}。参照元は `C:/AI-Sprint/sample-data`。今回、5CSVを全行読み込み、旧集計の転記ではなく再集計した。元ファイルは読込前後のSHA-256が5件とも一致した。", "",
             "| ファイル | 行数 | 異なる利用者ID数 | ユーザー一覧と未対応のID数 |", "|---|---:|---:|---:|"]
    for item in s["files"]:
        unmatched = s["joins"].get(item["kind"], {}).get("unmatched_unique_users", "対象外")
        lines.append(f"| {item['name']} | {item['rows']:,} | {item['unique_users']:,} | {unmatched} |")
    lines += ["", f"ユーザー一覧の重複ID行は{s['master_duplicate_user_rows']}件、登録時回答の重複ID行は{s['registration_duplicate_user_rows']}件。IDの列名は異なるため、下記の対応で照合した。氏名・メール・LINE個人IDによる照合は行っていない。", "",
              "| ファイル | 照合列 |", "|---|---|"]
    lines += [f"| {item['name']} | `{item['id_column']}` |" for item in s["files"]]
    lines += ["", "### 確認した列名", "", "以下は列の名前のみ。氏名・連絡先・LINE個人IDの値、自由記述原文、個票は記載しない。", ""]
    lines += [f"- **{item['name']}**：" + "、".join(f"`{column}`" for column in item["headers"]) for item in s["files"]]
    lines += ["", "### 年代と履歴の集団集計", "", "年代はユーザー一覧の年代列を20歳未満・10歳刻み・70歳以上に正規化した。年代を趣味や活動能力の推定には使っていない。", "", "| 年代区分 | 人数 |", "|---|---:|"]
    lines += [f"| {key} | {value} |" for key, value in sorted(s["age_bands"].items())]
    h = s["history"]
    lines += ["", f"登録時回答の年齢列とユーザー一覧の年代列を同じ区分で照合した不一致は{s['age_band_mismatch_between_user_and_registration']}人。これは同一人物・年齢の真正性を保証する確認ではない。", "",
              f"スタンプ履歴は{h['stamp_rows']:,}件、特典履歴は{h['reward_rows']:,}件。スタンプの異なるスポット名の値は{h['unique_spot_name_values']}種類。スタンプ日時の解釈不能は{h['invalid_stamp_dates']}件。記録月の範囲は{'〜'.join(h['stamp_month_range'] or ['不明'])}。", "",
              "| 異なるスタンプ記録日 | 利用者数 |", "|---|---:|"]
    lines += [f"| {key} | {value} |" for key, value in h["users_by_distinct_stamp_days"].items()]
    lines += ["", f"ユーザー一覧の獲得数と対応履歴行数の不一致：スタンプ{h['master_stamp_count_mismatch_users']}人、特典{h['master_reward_count_mismatch_users']}人。獲得数の整数変換失敗は{h['invalid_master_count_rows']}件。", "",
              "日付の異なる記録は、独立した旅行や現地への再訪を証明しない。旅行ID・同行者ID・旅行目的・現地確認の強度がないため、再訪率やグループ旅行履歴へ変換しない。", "",
              "### 参加後アンケート", "",
              f"異なる回答者は{s['survey_after']['respondents']}人、登録利用者{s['user_count']}人に対するカバー率は{s['survey_after']['response_coverage_percent']}%。未回答者の評価・興味は不明であり、回答を全員へ一般化しない。", "",
              "| 自由記述列 | 非空件数 |", "|---|---:|"]
    lines += [f"| {key} | {value} |" for key, value in s["survey_after"]["nonempty_by_field"].items()]
    lines += ["", "自由記述は原文を表示・保存せず、あらかじめ定義した広いカテゴリのキーワード言及だけを集計した。良かった点と要望の両列を対象とするため、肯定・否定・希望が混在する。以下は趣味の正解ラベルでも、個人の好みの推定でもない。", "",
              "| 固定カテゴリへの言及 | 異なる回答者数 |", "|---|---:|"]
    lines += [f"| {key} | {value} |" for key, value in s["survey_after"]["fixed_keyword_topic_respondents"].items()]
    lines += ["", "複数カテゴリへの該当を許すため合計は回答者数と一致しない。部分一致なので誤検出・見落としがあり、分析モデルの精度評価には使わない。10件未満の非ゼロカテゴリは数値を表示せず、年代等との交差集計も作成していない。", "",
              "## 新設計に使えること", "",
              "| 確認した入力 | 使える設計・検証 | 適用しないこと |", "|---|---|---|",
              "| 500人の利用者と複数CSVのID対応 | 所属・本人ID・写真・嗜好を別エンティティで保持する設計、履歴取込の参照整合性 | 500人を同じコミュニティ、同期、サークルとみなすこと |",
              "| 年代の広い分布 | 年代に依存しない操作・読みやすさの検証計画の母集団情報 | 年代から趣味、体力、親密度、旅行相性を推論すること |",
              "| スタンプ・特典と日時 | 訪問記録/特典/提案/旅行参加を分ける設計、保存と計算の履歴保持 | スポットの訪問から登山好き、飲酒習慣、宗教などを決めること |",
              "| 満足度・自由記述の存在と回答欠測 | 本人による趣味タグの採否・訂正・評価を別途尋ねる導線、情報不足状態 | 自由記述を無確認で恒久的な嗜好プロフィールへ取り込むこと |",
              "| 居住地/職業/認知経路の項目 | 必要な利用目的・取得同意・未回答許容を見直す材料 | 職業を会社や所属groupに置換、認知経路を友人関係と解釈すること |", "",
              "新設計の写真→候補タグ→本人が確認した好み→持越し許可→同じコミュニティ内の参加同意→少人数旅行提案という流れに、今回の個票を自動で割り当てない。年代や訪問回数の集計を使って『200人から旅行好き5人を特定できた』と報告しない。", "",
              "## 不足しているデータ", "",
              "5CSVの全列確認では、写真の参照列、所属コミュニティ、所属期間・招待、本人確定の趣味タグ、旅行の好み、好みの持越し許可、マッチ参加同意、旅行IDはない。指定フォルダ直下の画像拡張子ファイルは" + str(s["availability"]["photo_files_in_source_directory"]) + "件だった。", "",
              "- 写真タグ精度：使用許可のある写真と本人または独立評価者による正解ラベルが必要。登山・ボードゲーム・居酒屋などの正解データは今回のCSVには定義されていない。",
              "- クロスコミュニティ持越し：同じ本人の所属移動と、どの好みをどの利用先へ許可したかの記録が必要。",
              "- 5人程度のマッチ：参加希望、辞退、情報不足を区別する回答と、日程・予算・活動条件が必要。現データから所属や友人関係を補完しない。",
              "- 提案品質：提案の納得度、参加承諾、計画確定、本人が申告した実旅行を別々に記録する必要がある。",
              "- 再訪効果：旅行ID、訪問の確認方法、評価期間が必要。既存スタンプの日付差は代用指標としても別名で扱う。", "",
              "## 再現方法と保護", "",
              "`scripts/analyze_community_samples.py` をPJのPythonで実行すると、この文書、`artifacts/community-sample-summary.json`、`artifacts/community-correlation-summary.json`、`outputs/community-data-correlations.png` を書き出す。CSVは読取専用。個人IDはメモリー内の照合にだけ使用し、仮名IDも保存しない。氏名・メール・LINE ID・自由記述原文・個人別プロフィール・合成グループ・合成写真は出力しない。データの外部送信やAPI呼出はない。作図用Matplotlib/NumPyはPJの.venvへ導入した。", "",
              "### 元ファイルのSHA-256", "", "| ファイル | 読込前SHA-256 | 読込後一致 |", "|---|---|---|"]
    lines += [f"| {item['name']} | `{item['sha256_before']}` | {'一致' if item['unchanged'] else '不一致'} |" for item in s["files"]]
    lines += ["", "全列の非空件数、ID対応件数、前後のハッシュ実値はJSONに保持する。小カテゴリ抑制は開示を減らす手段であり、形式的な匿名性の保証ではない。今回の集計は試験用データが実際の人口や旅行者を代表することも保証しない。", "",
              "## 相関グラフ", "",
              "![旅行記録の相関](../outputs/community-data-correlations.png)", "",
              "出力：`outputs/community-data-correlations.png`。数値の正本：`artifacts/community-correlation-summary.json`。個人の散布図は作成していない。", "",
              "### 変数と欠測の定義", "",
              "| 変数 | 定義 |", "|---|---|"]
    lines += [f"| {item['label']} | {item['source']} |" for item in association["variables"]]
    lines += ["", association["missingness"], "",
              f"満足度の順序を判定できた回答は{association['satisfaction_respondents']}人、ユーザー一覧にいる未回答者は{association['satisfaction_missing_master_users']}人。順序は『大変不満=1、やや不満=2、普通=3、やや満足=4、大変満足=5』。5段階の等間隔性を仮定せず順位相関に用いる。未知の回答ラベルは{association['satisfaction_unknown_rows']}件。", "",
              f"特典CSVは獲得履歴であり、実際の利用・消費を示す列はない。図の特典変数を『利用数』とは呼ばない。一覧の『特典獲得数』と履歴行数が{s['history']['master_reward_count_mismatch_users']}人で一致しないため、履歴側の観測行数として限定して扱う。理由は未確認で、データ誤り・期間差・取消等を勝手に決めつけない。", "",
              "### 計算方法", "",
              "500人をIDで対応付け、変数の各組で両方の値がある人だけを使用する。各変数を平均順位（同値は同順位の平均）へ変換し、順位のPearson相関をSpearmanのρとする。無分散または対応人数2未満は計算不可。セルのnは組ごとの対応人数。欠測を0に補完せず、p値・有意性の印は付けない。既知の逆順・同順位・無分散・欠測例で計算の基本動作を確認した。", "",
              "| 変数の組 | n | Spearman ρ |", "|---|---:|---:|"]
    names = {item["id"]: item["label"] for item in association["variables"]}
    for pair in association["pairs"]:
        if pair["first"] == pair["second"]:
            continue
        value = "計算不可" if pair["rho"] is None else f"{pair['rho']:+.4f}"
        lines.append(f"| {names[pair['first']]} × {names[pair['second']]} | {pair['n']} | {value} |")
    lines += ["", "### 解釈と設計への反映", "",
              "スタンプの件数・記録日数・異なるスポット数は同じ履歴から作るため、互いに独立な好みの証拠ではない。将来の推薦でこれらを重ねて重み付けすると活動量を過剰に評価するおそれがある。特典との関係も獲得条件の制度設計によって生じる可能性があり、因果とは扱わない。満足度との相関は回答者に限った関係であり、未回答者に一般化しない。", "",
              "この図から人物の趣味・相性・所属・再訪率は得られない。新プラットフォームでは、本人が確認した好み・参加意思・日程や予算の条件を別途取得し、既存の活動量だけで旅行メンバーを選ばない。", ""]
    return "\n".join(lines)


def main():
    for target in (OUTPUT, REPORT, CORRELATIONS, FIGURE):
        if not target.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("出力はPJ内に限定します。")
    summary, tables = analyze()
    association = correlations(tables, summary)
    render_correlations(association, summary)
    # Verify the originals again after the complete analysis/plotting work.
    for item in summary["files"]:
        item["sha256_after"] = hashlib.sha256((SOURCE / item["name"]).read_bytes()).hexdigest()
        if item["sha256_after"] != item["sha256_before"]:
            raise RuntimeError("処理中に元ファイルが変化しました。集計を確定しません。")
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CORRELATIONS.write_text(json.dumps(association, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(summary, association), encoding="utf-8")
    print(json.dumps({"files_read": len(summary["files"]), "users": summary["user_count"],
                      "source_unchanged": summary["source_unchanged"], "individual_rows_output": False}, ensure_ascii=True))


if __name__ == "__main__":
    main()
