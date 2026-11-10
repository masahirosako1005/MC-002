"""Synthetic helper checks only; no source CSV or real response text is read."""
from analyze_community_samples import average_ranks, spearman
from analyze_survey_content import NONE_RE, TOPICS, matches


def test_average_ranks_and_spearman_handle_ties_missing_and_constant_values():
    assert average_ranks([1, 1, 3, 2]) == [1.5, 1.5, 4.0, 3.0]
    assert abs(spearman([1, 2, 3], [3, 2, 1])[0] + 1) < 1e-12
    assert spearman([1, 1], [1, 2]) == (None, 2)
    assert spearman([1, None, 3], [1, 2, 3])[1] == 2


def test_survey_categories_distinguish_no_request_from_specific_requests():
    assert NONE_RE.fullmatch("特になし")
    assert not NONE_RE.fullmatch("特になし。ただし地図がほしい")
    assert "自然・景観" in matches("景色を楽しめた", TOPICS)
    assert "同行・交流" in matches("友人と一緒に参加した", TOPICS)
    assert "交通・駐車" in matches("駐車場を増やしてほしい", TOPICS)
    assert not matches("特になし", TOPICS)
