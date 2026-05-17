"""Tests for the quality-first ranking algorithm."""

import pytest

from websearch.core.ranking import (get_engine_distribution,
                                    quality_first_ranking)


def test_quality_first_ranking():
    """Test basic quality-first ranking functionality"""
    # Mock results from different engines
    ddg_results = [
        {
            "url": "https://example1.com",
            "title": "DDG Result 1",
            "snippet": "Good content here",
        },
        {
            "url": "https://example2.com",
            "title": "DDG Result 2",
            "snippet": "More content",
        },
    ]

    bing_results = [
        {
            "url": "https://example1.com",
            "title": "Bing Result 1",
            "snippet": "Same URL different engine",
        },
        {
            "url": "https://example3.com",
            "title": "Bing Result 3",
            "snippet": "Unique Bing content",
        },
    ]

    startpage_results = [
        {
            "url": "https://example4.com",
            "title": "Startpage Result",
            "snippet": "Startpage content",
        },
    ]

    google_results = []
    brave_results = []

    # Test ranking
    results = quality_first_ranking(
        ddg_results, bing_results, startpage_results, google_results, brave_results, 5
    )

    # Should have unique URLs only
    urls = [r["url"] for r in results]
    assert len(urls) == len(set(urls)), "Should have no duplicate URLs"

    # Should have source attribution
    for result in results:
        assert "source" in result
        assert result["source"] in ["duckduckgo", "bing", "startpage"]
        assert "quality_score" in result
        assert result["quality_score"] > 0


def test_engine_distribution():
    """Test engine distribution calculation"""
    results = [
        {"source": "duckduckgo", "url": "https://example1.com"},
        {"source": "duckduckgo", "url": "https://example2.com"},
        {"source": "bing", "url": "https://example3.com"},
        {"source": "startpage", "url": "https://example4.com"},
    ]

    distribution = get_engine_distribution(results)

    assert distribution["duckduckgo"] == 2
    assert distribution["bing"] == 1
    assert distribution["startpage"] == 1


def test_deduplication_keeps_best():
    """Test that deduplication keeps the highest quality result"""
    ddg_results = [
        {"url": "https://example.com", "title": "Short", "snippet": "Brief"},
    ]

    bing_results = [
        {
            "url": "https://example.com",
            "title": "Much longer and better title",
            "snippet": "Much more comprehensive snippet with detailed information",
        },
    ]

    startpage_results = []
    google_results = []
    brave_results = []

    results = quality_first_ranking(
        ddg_results, bing_results, startpage_results, google_results, brave_results, 5
    )

    # Should only have one result (deduplicated)
    assert len(results) == 1

    # Should keep the higher quality one (Bing with longer content)
    assert results[0]["source"] == "bing"
    assert "Much longer" in results[0]["title"]


def test_canonical_dedup_collapses_tracking_variants():
    """Same article reached via different tracking-param URLs should dedup."""
    ddg_results = [
        {
            "url": "https://example.com/article?utm_source=ddg",
            "title": "The Article",
            "snippet": "x",
        }
    ]
    bing_results = [
        {
            "url": "https://www.example.com/article",
            "title": "The Article",
            "snippet": "x",
        }
    ]
    results = quality_first_ranking(ddg_results, bing_results, [], [], [], 5)
    assert len(results) == 1


def test_query_relevance_boosts_keyword_match():
    """Result with all query keywords beats a same-rank result with none."""
    ddg_results = [
        {
            "url": "https://noise.com",
            "title": "Cooking recipes",
            "snippet": "How to bake bread",
        },
        {
            "url": "https://relevant.com",
            "title": "Python async tutorial",
            "snippet": "Complete guide to python async",
        },
    ]
    results = quality_first_ranking(
        ddg_results, [], [], [], [], 5, query="python async"
    )
    # Relevant result must rank above noise.com despite same engine_rank tier
    assert results[0]["url"] == "https://relevant.com"


def test_freshness_boosts_recent_content():
    """Same-rank results from different engines: fresh > stale."""
    # Place the stale one as ddg rank-1 and the fresh one as bing rank-1 so
    # the engine_rank base score is identical and the freshness signal is
    # the deciding factor.
    ddg_results = [
        {
            "url": "https://stale.com",
            "title": "Python async tutorial",
            "snippet": "Python async tutorial published Jan 1, 2018",
        }
    ]
    bing_results = [
        {
            "url": "https://fresh.com",
            "title": "Python async tutorial",
            "snippet": "Python async tutorial published 2 days ago",
        }
    ]
    results = quality_first_ranking(
        ddg_results, bing_results, [], [], [], 5, query="python async tutorial"
    )
    # Same titles → title-dedup keeps best-scored. Fresh wins on freshness boost.
    assert results[0]["url"] == "https://fresh.com"


def test_query_blind_call_works():
    """Legacy callers without query argument still produce reasonable scores."""
    ddg_results = [{"url": "https://x.com", "title": "x", "snippet": "x"}]
    results = quality_first_ranking(ddg_results, [], [], [], [], 5)
    assert len(results) == 1
    assert results[0]["quality_score"] > 0
