"""Tests for query-overlap and freshness signals used in ranking."""

from datetime import datetime, timedelta, timezone

import pytest

from websearch.utils.relevance import (freshness_score, parse_snippet_date,
                                       query_overlap)

NOW = datetime(2026, 5, 17, tzinfo=timezone.utc)


# ---------- query_overlap ----------


def test_full_overlap_returns_one():
    assert query_overlap("python programming", "python programming tutorial") == 1.0


def test_partial_overlap():
    score = query_overlap("python machine learning", "python tutorial")
    # 1 of 3 query tokens matches
    assert score == pytest.approx(1 / 3)


def test_zero_overlap():
    assert query_overlap("javascript", "python golang rust") == 0.0


def test_empty_query_returns_zero():
    assert query_overlap("", "anything") == 0.0


def test_stopwords_dont_count():
    """'the python' should match 'python in production' fully — 'the' is dropped."""
    assert query_overlap("the python", "python in production") == 1.0


def test_case_insensitive():
    assert query_overlap("PYTHON", "Python tutorial") == 1.0


def test_overlap_across_multiple_fields():
    """Tokens are unioned across all candidate fields."""
    score = query_overlap("python golang", "python tutorial", "golang basics")
    assert score == 1.0


def test_overlap_all_stopwords_returns_zero():
    """A query that is entirely stopwords has no usable tokens → 0.0."""
    assert query_overlap("the and of", "python tutorial") == 0.0


# ---------- parse_snippet_date ----------


def test_parse_iso_date():
    d = parse_snippet_date("Released 2024-03-15 with new features", now=NOW)
    assert d == datetime(2024, 3, 15, tzinfo=timezone.utc)


def test_parse_long_month_name():
    d = parse_snippet_date("Posted on January 22, 2026", now=NOW)
    assert d == datetime(2026, 1, 22, tzinfo=timezone.utc)


def test_parse_short_month_name():
    d = parse_snippet_date("Mar 5, 2026 — breaking news", now=NOW)
    assert d == datetime(2026, 3, 5, tzinfo=timezone.utc)


def test_parse_dmY_format():
    d = parse_snippet_date("Updated 22 Apr 2025", now=NOW)
    assert d == datetime(2025, 4, 22, tzinfo=timezone.utc)


def test_parse_relative_days_ago():
    d = parse_snippet_date("Posted 3 days ago", now=NOW)
    assert d == NOW - timedelta(days=3)


def test_parse_indefinite_a_year_ago():
    """`a year ago` is unambiguous — kept."""
    assert parse_snippet_date("released a year ago", now=NOW) == NOW - timedelta(days=365)


def test_parse_indefinite_an_hour_ago():
    assert parse_snippet_date("posted an hour ago", now=NOW) == NOW - timedelta(hours=1)


def test_today_substring_does_not_match():
    """Regression: `today`/`yesterday`/`last week` substrings would inflate
    freshness for stale entertainment/editorial content. Only explicit forms
    (N units ago, a/an UNIT ago, dated text) should match."""
    assert parse_snippet_date("Today Show interview with Bezos", now=NOW) is None
    assert parse_snippet_date("Best deals available today only", now=NOW) is None
    assert parse_snippet_date(
        "John Oliver's Last Week Tonight episode 5", now=NOW
    ) is None
    assert parse_snippet_date("Last year, the company...", now=NOW) is None


def test_most_recent_date_wins():
    """When a snippet contains multiple parseable dates (reference + pub date),
    the most recent should be returned — the publication date is what
    freshness should reflect."""
    text = "Compares behavior to Jan 22, 2020 release; published Mar 5, 2026"
    assert parse_snippet_date(text, now=NOW) == datetime(2026, 3, 5, tzinfo=timezone.utc)


def test_parse_no_date_returns_none():
    assert parse_snippet_date("just some text with no date", now=NOW) is None


def test_parse_empty_returns_none():
    assert parse_snippet_date("", now=NOW) is None


def test_parse_rejects_implausible_year():
    """A year way in the future shouldn't be accepted as the article date."""
    assert parse_snippet_date("see also: 9999-12-31", now=NOW) is None


# ---------- freshness_score ----------


def test_freshness_today_via_explicit_date_is_one():
    """Using an explicit date matching now → freshness ~1.0.
    Bare 'today' is intentionally not parsed (substring false positives)."""
    text = NOW.strftime("Updated %Y-%m-%d")
    assert freshness_score(text, now=NOW) == pytest.approx(1.0)


def test_freshness_one_year_old_is_half():
    text = "Released May 17, 2025"
    score = freshness_score(text, now=NOW, half_life_days=365.0)
    assert score == pytest.approx(0.5, abs=0.01)


def test_freshness_decays_with_age():
    fresh = freshness_score("Jan 1, 2026", now=NOW)
    stale = freshness_score("Jan 1, 2020", now=NOW)
    assert fresh > stale > 0


def test_freshness_no_date_returns_zero():
    """No date = no signal (neither boost nor penalty)."""
    assert freshness_score("just text", now=NOW) == 0.0


def test_freshness_future_dates_clamped():
    """Future-dated content shouldn't blow up the score."""
    score = freshness_score("publishing 2027-01-01", now=NOW)
    assert score == pytest.approx(1.0)
