"""Tests for the quality-first ranking algorithm."""

import pytest
from src.websearch.core.ranking import quality_first_ranking, get_engine_distribution


def test_quality_first_ranking():
    """Test basic quality-first ranking functionality"""
    # Mock results from different engines
    ddg_results = [
        {"url": "https://example1.com", "title": "DDG Result 1", "snippet": "Good content here"},
        {"url": "https://example2.com", "title": "DDG Result 2", "snippet": "More content"},
    ]
    
    bing_results = [
        {"url": "https://example1.com", "title": "Bing Result 1", "snippet": "Same URL different engine"},
        {"url": "https://example3.com", "title": "Bing Result 3", "snippet": "Unique Bing content"},
    ]
    
    startpage_results = [
        {"url": "https://example4.com", "title": "Startpage Result", "snippet": "Startpage content"},
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
        {"url": "https://example.com", "title": "Much longer and better title", "snippet": "Much more comprehensive snippet with detailed information"},
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
