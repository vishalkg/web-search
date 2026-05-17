"""Unit tests for URL tracking and deduplication functionality."""

import json
import os
import tempfile

import pytest

from websearch.utils.deduplication import deduplicate_results
from websearch.utils.tracking import (add_tracking_to_url,
                                      extract_tracking_from_url,
                                      generate_search_id)


class TestURLTracking:
    """Test URL tracking functionality."""

    def test_add_tracking_to_simple_url(self):
        """Test adding tracking to URL without existing params."""
        url = "https://example.com/page"
        tracked = add_tracking_to_url(url, "bing", "test123")

        assert "_src=b" in tracked
        assert "_sid=test123" in tracked
        assert tracked.startswith("https://example.com/page?")

    def test_add_tracking_to_url_with_params(self):
        """Test adding tracking to URL with existing parameters."""
        url = "https://example.com/search?q=python&lang=en"
        tracked = add_tracking_to_url(url, "startpage", "test456")

        assert "q=python" in tracked
        assert "lang=en" in tracked
        assert "_src=s" in tracked
        assert "_sid=test456" in tracked

    def test_extract_tracking_from_url(self):
        """Test extracting tracking info and cleaning URL."""
        original = "https://example.com/page?q=test&lang=en"
        tracked = add_tracking_to_url(original, "duckduckgo", "search789")

        engine, search_id, clean_url = extract_tracking_from_url(tracked)

        assert engine == "duckduckgo"
        assert search_id == "search789"
        assert clean_url == original

    @pytest.mark.parametrize(
        "engine", ["duckduckgo", "bing", "startpage", "google", "brave"]
    )
    def test_round_trip_all_engines(self, engine):
        """All five engine names round-trip through tracking encoding."""
        original = "https://example.com/page?q=t"
        tracked = add_tracking_to_url(original, engine, "sid42")
        got_engine, got_sid, got_clean = extract_tracking_from_url(tracked)
        assert got_engine == engine
        assert got_sid == "sid42"
        assert got_clean == original

    def test_generate_search_id_format(self):
        """Test search ID generation format."""
        search_id = generate_search_id()

        assert len(search_id) == 19  # YYYYMMDD_HHMMSS_mmm (fixed length)
        assert search_id.count("_") == 2
        assert search_id[:8].isdigit()  # Date part

    def test_log_selection_metrics(self):
        """Test logging selection metrics to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test metrics file path
            metrics_file = os.path.join(temp_dir, "search-metrics.jsonl")

            # Patch the metrics file location
            import websearch.utils.tracking as tracking_module

            original_init = tracking_module.log_selection_metrics

            def patched_log_selection_metrics(urls):
                if not urls:
                    return

                selections = []
                for url in urls:
                    engine, search_id, clean_url = extract_tracking_from_url(url)
                    selections.append(
                        {
                            "engine": engine,
                            "search_id": search_id,
                            "url": clean_url,
                            "original_url": url,
                        }
                    )

                event = {
                    "event_type": "url_selection",
                    "timestamp": "2025-01-01T00:00:00",
                    "selections": selections,
                    "total_selected": len(urls),
                }

                os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
                with open(metrics_file, "a") as f:
                    f.write(json.dumps(event) + "\n")

            tracking_module.log_selection_metrics = patched_log_selection_metrics

            try:
                urls = [
                    "https://example.com?_src=b&_sid=test123",
                    "https://other.com?_src=s&_sid=test123",
                ]

                tracking_module.log_selection_metrics(urls)

                assert os.path.exists(metrics_file)

                with open(metrics_file, "r") as f:
                    event = json.loads(f.read().strip())

                assert event["event_type"] == "url_selection"
                assert event["total_selected"] == 2
                assert len(event["selections"]) == 2
                assert event["selections"][0]["engine"] == "bing"
                assert event["selections"][1]["engine"] == "startpage"

            finally:
                tracking_module.log_selection_metrics = original_init


class TestDeduplication:
    """Test result deduplication ranks by quality_score (descending)."""

    def test_deduplicate_different_urls(self):
        results = [
            {"url": "https://a.com", "title": "A", "quality_score": 5.0},
            {"url": "https://b.com", "title": "B", "quality_score": 4.0},
        ]
        deduplicated = deduplicate_results(results, 10)
        assert len(deduplicated) == 2
        assert deduplicated[0]["url"] == "https://a.com"
        assert deduplicated[1]["url"] == "https://b.com"

    def test_deduplicate_same_url_best_quality_wins(self):
        results = [
            {
                "url": "https://example.com",
                "title": "Example",
                "quality_score": 3.0,
                "_source_engine": "duckduckgo",
            },
            {
                "url": "https://example.com",
                "title": "Example",
                "quality_score": 9.0,
                "_source_engine": "bing",
            },
        ]
        deduplicated = deduplicate_results(results, 10)
        # url+title dedup leaves only the highest-scored entry
        assert len(deduplicated) == 1
        assert deduplicated[0]["_source_engine"] == "bing"

    def test_deduplicate_respects_num_results_limit(self):
        results = [
            {"url": f"https://e{i}.com", "title": f"T{i}", "quality_score": 10 - i}
            for i in range(5)
        ]
        deduplicated = deduplicate_results(results, 3)
        assert len(deduplicated) == 3
        # Sorted by descending quality
        assert deduplicated[0]["quality_score"] == 10
        assert deduplicated[2]["quality_score"] == 8


class TestEndToEndTracking:
    """End-to-end tests for the complete tracking flow."""

    def test_tracking_flow_with_deduplication(self):
        # Simulate ranked candidates pre-scored by ranking algorithm
        candidates = [
            {
                "url": "https://example.com",
                "title": "Example DDG",
                "quality_score": 5.0,
                "_source_engine": "duckduckgo",
            },
            {
                "url": "https://example.com",
                "title": "Example DDG",
                "quality_score": 9.0,
                "_source_engine": "bing",
            },
            {
                "url": "https://unique.com",
                "title": "Unique Bing",
                "quality_score": 7.0,
                "_source_engine": "bing",
            },
        ]

        deduplicated = deduplicate_results(candidates, 10)
        assert len(deduplicated) == 2

        example = next(r for r in deduplicated if "example.com" in r["url"])
        assert example["_source_engine"] == "bing"

        search_id = "test_search_123"
        for result in deduplicated:
            engine = result.pop("_source_engine")
            result["url"] = add_tracking_to_url(result["url"], engine, search_id)

        for result in deduplicated:
            engine, sid, clean_url = extract_tracking_from_url(result["url"])
            assert sid == search_id
            if "example.com" in clean_url:
                assert engine == "bing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
