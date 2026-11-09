"""Additional local descriptive analysis, with questions/dictionaries fixed first.

Predeclared questions (before this script's first data run):
1. How are the five satisfaction responses distributed? Is a ceiling plausible?
   Compare observed history counts between respondents and nonrespondents.
2. What is the respondent-only stamp-count/satisfaction Spearman association,
   with a fixed-seed 2,000 paired-resample percentile bootstrap interval?
3. How concentrated are exact free-text strings, without exposing their text?
4. Does the acquisition channel mention friends/acquaintances/introduction?
   Separately count fixed topic words in positive-points and request fields.

Do not turn keyword mentions into demand, sentiment, preference or causation.
Do not infer any person's interests, community membership or travel companions.
Only artifacts/community-rationale-statistics.json is written, inside the PJ.
No source rows, names, contact details, free text or hashed user IDs are emitted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median, variance

import numpy as np

from analyze_community_samples import read_sources, parse_date, spearman, SATISFACTION


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("C:/AI-Sprint/sample-data")
OUTPUT = ROOT / "artifacts/community-rationale-statistics.json"
SEED = 20261109
BOOTSTRAP_REPLICATES = 2000
SUPPRESSION_THRESHOLD = 10

# Deliberately fixed before reading the data. No dictionary revision based on
# which result would best support a product direction.
TOPIC_DICTIONARY = {
    "仲間・交流": ("仲間", "友人", "友達", "友だち", "知人", "交流", "出会い", "一緒", "いっしょ"),
    "再訪・次回": ("再訪", "再び", "もう一度", "また行", "また来", "また訪", "また参加", "次回", "次の旅", "リピート"),
    "計画・日程調整": ("計画", "日程", "予定", "調整", "スケジュール", "旅程", "プラン"),
}
FRIEND_WORDS = ("友人", "知人", "友達", "友だち")
INTRODUCTION_PATTERN = re.compile(r"(?:友人|知人|友達|友だち|家族)(?:[・/／](?:友人|知人|友達|友だち|家族))*(?:からの|の|から|による)?紹介")

# Added AFTER the first result (69 positive-points / 39 request mentions).
# This follow-up is exploratory, not part of the initial fixed dictionary.
# Patterns are fixed before running this follow-up and never emit original text.
FOLLOWUP_ACTORS = {
    "家族": r"家族|親子|夫婦|子ども|子供|子連れ",
    "友人・知人・仲間": r"友人|友達|友だち|知人|仲間",
    "スタッフ・案内者": r"スタッフ|ガイド|案内人|係員|店員|従業員",
    "地域住民": r"地域の人|地元の人|地域の方|地元の方|住民",
    "他の参加者": r"他の参加者|ほかの参加者|参加者同士|参加者どうし",
}
FOLLOWUP_MARKERS = {
    "同行・一緒に活動する構文": r"(?:家族|友人|友達|友だち|知人|仲間)(?:と(?:一緒に)?|で|同士で|同士の).{0,20}(?:回|巡|参加|旅行|旅|出かけ|楽し)",
    "肯定表現": r"楽しか|楽しい|楽しめ|よかった|良かった|嬉しか|うれしか|満足",
    "希望表現": r"ほしい|欲しい|してほしい|できると|あると|増や|充実",
    "不要・拒否・否定の明示表現": r"不要|必要[はも]?ない|いらない|望まない|求めない|したくない|行きたくない|苦手|なくていい|楽しめな|不満|嫌",
    "新しい相手の明示表現": r"新しい友人|新たな友人|新しい仲間|新たな仲間|初対面|知らない人",
}


def count_cell(value):
    return value if value == 0 or value >= SUPPRESSION_THRESHOLD else "1〜9（抑制）"


def frequency_table(counts):
    """Suppress a second cell if totals would expose one suppressed small cell."""
    result = {label: count_cell(count) for label, count in counts.items()}
    primary = [label for label, count in counts.items() if 0 < count < SUPPRESSION_THRESHOLD]
    if len(primary) == 1:
        candidates = [label for label, count in counts.items() if count >= SUPPRESSION_THRESHOLD]
        if candidates:
            other = min(candidates, key=lambda label: counts[label])
            result[other] = "補完抑制"
    return result


def quantiles(values):
    return {"n": len(values), "median": float(median(values)),
            "q1": float(np.percentile(values, 25, method="linear")),
            "q3": float(np.percentile(values, 75, method="linear"))}


def described_distribution(values, kind):
    labels = {"stamp_rows": ("0件", "1〜3件", "4〜6件", "7件以上"),
              "stamp_days": ("0日", "1日", "2日", "3日以上"),
              "reward_rows": ("0件", "1件", "2件", "3件以上")}[kind]
    counts = Counter(dict.fromkeys(labels, 0))
    for value in values:
        if kind == "stamp_rows":
            position = 0 if value == 0 else 1 if value <= 3 else 2 if value <= 6 else 3
        else:
            position = min(value, 3)
        counts[labels[position]] += 1
    return {**quantiles(values), "bins": frequency_table(counts)}


def text_concentration(rows, column):
    values = [row[column].strip() for row in rows if row[column].strip()]
    counts = Counter(values)
    frequencies = sorted(counts.values(), reverse=True)
    n = len(values)
    return {
        "nonempty_rows": n, "distinct_exact_strings": count_cell(len(counts)),
        "largest_exact_string_count": count_cell(frequencies[0]) if frequencies else 0,
        "largest_exact_string_share_percent": round(100 * frequencies[0] / n, 2) if n and frequencies[0] >= SUPPRESSION_THRESHOLD else None,
        "top_3_exact_strings_share_percent": round(100 * sum(frequencies[:3]) / n, 2) if n else None,
        "top_5_exact_strings_share_percent": round(100 * sum(frequencies[:5]) / n, 2) if n else None,
        "singleton_string_count": count_cell(sum(value == 1 for value in frequencies)),
        "normalization": "先頭末尾の空白のみ除去。文面も文面ハッシュも保持しない。",
        "interpretation": "頻度集中を測るだけで、実在回答・合成・定型選択肢等の由来や真正性を断定しない。",
    }


def followup_context(rows, column):
    selected = [row[column] for row in rows if any(word in row[column] for word in TOPIC_DICTIONARY["仲間・交流"])]
    actor_counts = {label: sum(bool(re.search(pattern, value)) for value in selected) for label, pattern in FOLLOWUP_ACTORS.items()}
    marker_counts = {label: sum(bool(re.search(pattern, value)) for value in selected) for label, pattern in FOLLOWUP_MARKERS.items()}
    actor_unclassified = sum(not any(re.search(pattern, value) for pattern in FOLLOWUP_ACTORS.values()) for value in selected)
    return {
        "selected_rows": len(selected), "actor_mentions_nonexclusive": {label: count_cell(count) for label, count in actor_counts.items()},
        "expression_matches_nonexclusive": {label: count_cell(count) for label, count in marker_counts.items()},
        "no_recognized_actor_rows": count_cell(actor_unclassified),
        "scope": "初回の仲間・交流辞書に一致した全回答を対象。各パターンは同じ回答で重複し得る。",
        "context_judgment": "機械的な構文/語句の照合であり、原文の人手精読・文脈全体の確定ではない。皮肉、引用、照応、辞書外の否定・対象は未確認。0件は当該パターン未一致を意味する。",
    }


def run():
    tables, file_reports = read_sources()
    users = {row["ユーザーID"].strip(): row for row in tables["users"]}
    after = {row["user_id"].strip(): row for row in tables["after"]}
    if len(after) != len(tables["after"]) or len(users) != len(tables["users"]):
        raise RuntimeError("一人複数行の扱いが未定義です。個票を表示せず停止します。")
    if set(after) - set(users):
        raise RuntimeError("回答に未対応IDがあります。個票を表示せず停止します。")
    for kind, id_column in (("before", "user_id"), ("stamps", "ユーザID"), ("rewards", "user_id")):
        if {row[id_column].strip() for row in tables[kind]} - set(users):
            raise RuntimeError("履歴または登録回答に未対応IDがあります。個票を表示せず停止します。")
    stamp_counts = Counter(row["ユーザID"].strip() for row in tables["stamps"])
    reward_counts = Counter(row["user_id"].strip() for row in tables["rewards"])
    days = defaultdict(set)
    for row in tables["stamps"]:
        parsed = parse_date(row["獲得日時"])
        if parsed is None:
            raise RuntimeError("日時が解釈できません。個票を表示せず停止します。")
        days[row["ユーザID"].strip()].add(parsed.date())
    satisfaction_column = next(column for column in tables["after"][0] if "満足度" in column)
    satisfaction_values = [SATISFACTION.get(row[satisfaction_column].strip()) for row in after.values()]
    if any(value is None for value in satisfaction_values):
        raise RuntimeError("満足度に未定義の順序があります。個票を表示せず停止します。")
    n = len(satisfaction_values)
    response_frequencies = Counter(dict.fromkeys(SATISFACTION, 0))
    response_frequencies.update(row[satisfaction_column].strip() for row in after.values())
    satisfaction = {
        "respondents": n, "nonrespondents": len(users) - n,
        "coverage_percent": round(100 * n / len(users), 2),
        "ordered_mapping": SATISFACTION, "counts": frequency_table(response_frequencies),
        "percent_of_respondents": {label: round(100 * count / n, 2) if count >= SUPPRESSION_THRESHOLD else None for label, count in response_frequencies.items()},
        **{key: value for key, value in quantiles(satisfaction_values).items() if key != "n"},
        "top_category_percent": round(100 * sum(value == 5 for value in satisfaction_values) / n, 2),
        "top_two_categories_percent": round(100 * sum(value >= 4 for value in satisfaction_values) / n, 2),
        "numeric_code_sample_variance": variance(satisfaction_values),
        "numeric_code_mean": mean(satisfaction_values),
        "numeric_code_caution": "平均と標本分散は1〜5への符号化上の補助量。満足の心理量の等間隔性を仮定した解釈はしない。",
        "ceiling_interpretation": "上端の回答率を報告する。上端だけに集中しているかは分布から判断し、天井効果の有無を率だけで検定・断定しない。",
    }
    groups = {"respondents": [user for user in users if user in after], "nonrespondents": [user for user in users if user not in after]}
    metrics = {"stamp_rows": lambda user: stamp_counts[user], "stamp_days": lambda user: len(days[user]), "reward_rows": lambda user: reward_counts[user]}
    comparison = {name: {metric: described_distribution([extract(user) for user in ids], metric) for metric, extract in metrics.items()} for name, ids in groups.items()}
    comparison["median_difference_respondents_minus_nonrespondents"] = {metric: comparison["respondents"][metric]["median"] - comparison["nonrespondents"][metric]["median"] for metric in metrics}
    comparison["interpretation"] = "記述的比較のみ。回答選択の偏りがない証明ではなく、有意差検定・因果推論はしない。履歴の対応行なしは観測件数0であり、実際の活動なしを保証しない。"

    paired = [(stamp_counts[user], SATISFACTION[row[satisfaction_column].strip()]) for user, row in after.items()]
    x, y = zip(*paired)
    point, pair_n = spearman(x, y)
    rng = np.random.default_rng(SEED)
    bootstrap_values = []
    invalid = 0
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = rng.integers(0, pair_n, size=pair_n)
        rho, _ = spearman([x[index] for index in indices], [y[index] for index in indices])
        if rho is None:
            invalid += 1
        else:
            bootstrap_values.append(rho)
    interval = [float(value) for value in np.percentile(bootstrap_values, [2.5, 97.5], method="linear")] if bootstrap_values else None
    association = {
        "variables": ["提供CSV内のスタンプ履歴件数", "満足度の順序値"], "n": pair_n, "rho": point,
        "bootstrap": {"method": "percentile 95% paired nonparametric bootstrap; resample respondent rows with replacement; average ranks for ties", "seed": SEED,
                      "replicates": BOOTSTRAP_REPLICATES, "valid_replicates": len(bootstrap_values), "undefined_constant_replicates": invalid,
                      "numpy_version": np.__version__, "rng_algorithm": type(rng.bit_generator).__name__,
                      "percentile_method": "linear", "interval_95_percent": interval},
        "conditional_assumptions": ["回答者のペアが独立な標本であると仮定した条件付き区間", "非回答者への一般化や選択バイアス補正ではない", "回答が同じ旅行/所属等で依存する場合を評価できない", "合成または定型生成データなら現実人口に対する信頼区間として解釈できない", "観察相関でありスタンプ数の増加が満足度を変える因果効果ではない"],
    }
    good_column = next(column for column in tables["after"][0] if "良かった点" in column)
    request_column = next(column for column in tables["after"][0] if "要望" in column)
    text = {}
    for label, column in [("旅で良かった点", good_column), ("要望", request_column)]:
        counts = {topic: sum(any(word in row[column] for word in keywords) for row in after.values()) for topic, keywords in TOPIC_DICTIONARY.items()}
        text[label] = {"concentration": text_concentration(tables["after"], column), "topic_mention_respondents": {topic: count_cell(count) for topic, count in counts.items()},
                       "exploratory_context_followup": followup_context(tables["after"], column)}
    channel_column = next(column for column in tables["before"][0] if "何で知り" in column)
    channel_values = [row[channel_column] for row in tables["before"]]
    friend_count = sum(any(word in value for word in FRIEND_WORDS) for value in channel_values)
    explicit_count = sum(bool(INTRODUCTION_PATTERN.search(value)) for value in channel_values)
    friend_with_explicit_introduction = sum(any(word in value for word in FRIEND_WORDS) and bool(INTRODUCTION_PATTERN.search(value)) for value in channel_values)
    channel = {
        "respondents": len(channel_values), "column": channel_column,
        "friend_or_acquaintance_mention_count": count_cell(friend_count),
        "friend_or_acquaintance_mention_percent": round(100 * friend_count / len(channel_values), 2) if friend_count >= SUPPRESSION_THRESHOLD else None,
        "explicit_person_introduction_phrase_count": count_cell(explicit_count),
        "friend_mentions_also_matching_explicit_introduction_phrase": count_cell(friend_with_explicit_introduction),
        "friend_mentions_without_matching_explicit_introduction_phrase": count_cell(friend_count - friend_with_explicit_introduction),
        "friend_dictionary": FRIEND_WORDS, "explicit_introduction_regex": INTRODUCTION_PATTERN.pattern,
        "interpretation": "認知経路の選択欄での友人/知人等への言及。旅行同行、関係の強さ、マッチ希望を示さない。紹介の厳密表現一致と広い友人等言及を区別し、未一致を紹介がない証拠としない。",
    }
    context_summary = {
        "review_type": "一次結果後の探索的な全件パターン照合。人手による原文精読ではない。",
        "positive_points": "仲間・交流の言及があっても、同行友人/家族/スタッフ/地域住民/他の参加者のどれかをパターンで特定できない回答は、相手不明のまま残す。新しい旅仲間を望む声と読み替えない。",
        "requests": "友人・知人・仲間の語、同行構文への一致を別々に記録。要望欄にあるという理由だけで自動マッチ需要、肯定、参加意思を確定しない。",
        "negation": "不要・拒否・否定の固定パターン未一致でも、辞書外の否定や文脈上の否定がないとは確定できない。",
        "channel": "友人等の名詞だけの一致と、紹介を明示する構文一致を区別した。人数は認知経路の事実であり、新しい相手とのマッチ需要ではない。",
    }
    checks = []
    for item in file_reports:
        after_hash = hashlib.sha256((SOURCE / item["name"]).read_bytes()).hexdigest()
        checks.append({"file": item["name"], "rows": item["rows"], "sha256_before": item["sha256_before"], "sha256_after": after_hash, "unchanged": item["sha256_before"] == after_hash})
    if not all(item["unchanged"] for item in checks):
        raise RuntimeError("元ファイルの変更を検出したため集計確定を止めます。")
    return {
        "analysis_version": "1.0", "analyzed_at_utc": datetime.now(timezone.utc).isoformat(), "source_checks": checks,
        "predeclared_questions": __doc__, "topic_dictionary_fixed_before_run": TOPIC_DICTIONARY,
        "exploratory_followup_dictionary": {"timing": "69/39件等の一次結果を見た後に追加した探索的確認。初回の事前固定辞書と区別する。追加パターンを固定して全対象へ同じ規則を適用。",
                                           "actor_patterns": FOLLOWUP_ACTORS, "expression_patterns": FOLLOWUP_MARKERS},
        "exploratory_context_summary": context_summary,
        "satisfaction": satisfaction, "response_group_descriptions": comparison,
        "stamp_satisfaction_association": association, "free_text": text, "acquisition_channel": channel,
        "evidence_map": [
            {"status": "肯定・限定的", "claim": "既存の記録数だけで満足の代用指標を決めず、本人の希望や評価を別に取得する理由がある。", "basis": "満足度の分布・活動指標との相関・未回答者の存在を個別に確認できる。新たな入力設計の理由であり講の有効性の証明ではない。"},
            {"status": "肯定・条件付き", "claim": "友人等を通じた認知が観測される場合、既存の人とのつながりを入口候補として検討できる。", "basis": "認知経路の固定辞書集計を参照。認知経路から自動仲間選びの需要や効果を導くことはできない。"},
            {"status": "反証材料・因果の反証ではない", "claim": "スタンプ件数が多いほど満足も高いという単純な単調関係を、今回の回答者データが強く支持するとは言えない。", "basis": {"rho": point, "conditional_interval_95_percent": interval}},
            {"status": "不明", "claim": "講・5人マッチ・好み持越し・協力分担が既存方式より役立つか。", "basis": "介入・比較・マッチ希望・所属・趣味正解・旅行実行のデータがない。別途、本人への確認と比較評価が必要。"},
            {"status": "不明", "claim": "自由記述の意味、正負、回答の真正性、未言及の理由。", "basis": "固定キーワードは文字列の一致だけ。重複集中は由来を断定せず、0言及も需要なしを意味しない。"},
        ],
        "limits": ["二次データの探索的な追加分析。問いと辞書はこの追加集計の前に固定したが、既存の相関結果は既知", "新プラットフォームを採る唯一必然の結論にはならない", "列の意味や完全性は提供CSVの範囲に限定", "特典履歴は利用数でなく観測行数。一覧との227人不一致の原因は未確認", "小セル抑制は形式的な匿名性保証ではない"],
        "privacy": {"minimum_nonzero_count": SUPPRESSION_THRESHOLD, "secondary_suppression_for_single_small_distribution_cell": True,
                    "individual_rows_or_identifiers_written": False, "free_text_or_text_hashes_written": False,
                    "external_data_transmission": False, "source_files_modified": False},
    }


def main():
    if not OUTPUT.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("出力先はPJ内に限定します。")
    result = run()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_unchanged": all(item["unchanged"] for item in result["source_checks"]),
                      "respondents": result["satisfaction"]["respondents"],
                      "rho": result["stamp_satisfaction_association"]["rho"],
                      "bootstrap_interval": result["stamp_satisfaction_association"]["bootstrap"]["interval_95_percent"],
                      "personal_rows_written": False}, ensure_ascii=True))


if __name__ == "__main__":
    main()
