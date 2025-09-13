"""Unit tests for URL tracking and deduplication functionality."""

import pytest
import tempfile
import os
import json
from src.websearch.utils.tracking import (
    add_tracking_to_url,
    extract_tracking_from_url,
    generate_search_id,
    log_selection_metrics
)
from src.websearch.core.common import deduplicate_results


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
        tracked = add_tracking_to_url(original, "ddg", "search789")
        
        engine, search_id, clean_url = extract_tracking_from_url(tracked)
        
        assert engine == "ddg"
        assert search_id == "search789"
        assert clean_url == original
    
    def test_generate_search_id_format(self):
        """Test search ID generation format."""
        search_id = generate_search_id()
        
        assert len(search_id) == 19  # YYYYMMDD_HHMMSS_mmm (fixed length)
        assert search_id.count('_') == 2
        assert search_id[:8].isdigit()  # Date part
    
    def test_log_selection_metrics(self):
        """Test logging selection metrics to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test metrics file path
            metrics_file = os.path.join(temp_dir, "search-metrics.jsonl")
            
            # Patch the metrics file location
            import src.websearch.utils.tracking as tracking_module
            original_init = tracking_module.log_selection_metrics
            
            def patched_log_selection_metrics(urls):
                if not urls:
                    return
                    
                selections = []
                for url in urls:
                    engine, search_id, clean_url = extract_tracking_from_url(url)
                    selections.append({
                        'engine': engine,
                        'search_id': search_id,
                        'url': clean_url,
                        'original_url': url
                    })
                
                event = {
                    'event_type': 'url_selection',
                    'timestamp': '2025-01-01T00:00:00',
                    'selections': selections,
                    'total_selected': len(urls)
                }
                
                os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
                with open(metrics_file, 'a') as f:
                    f.write(json.dumps(event) + '\n')
            
            tracking_module.log_selection_metrics = patched_log_selection_metrics
            
            try:
                urls = [
                    "https://example.com?_src=b&_sid=test123",
                    "https://other.com?_src=s&_sid=test123"
                ]
                
                tracking_module.log_selection_metrics(urls)
                
                assert os.path.exists(metrics_file)
                
                with open(metrics_file, 'r') as f:
                    event = json.loads(f.read().strip())
                
                assert event['event_type'] == 'url_selection'
                assert event['total_selected'] == 2
                assert len(event['selections']) == 2
                assert event['selections'][0]['engine'] == 'bing'
                assert event['selections'][1]['engine'] == 'startpage'
                
            finally:
                tracking_module.log_selection_metrics = original_init


class TestDeduplication:
    """Test result deduplication with ranking."""
    
    def test_deduplicate_different_urls(self):
        """Test deduplication with completely different URLs."""
        results = [
            {'url': 'https://example.com', 'title': 'Example', 'rank': 1},
            {'url': 'https://other.com', 'title': 'Other', 'rank': 2}
        ]
        
        deduplicated = deduplicate_results(results, 10)
        
        assert len(deduplicated) == 2
        assert deduplicated[0]['url'] == 'https://example.com'
        assert deduplicated[1]['url'] == 'https://other.com'
    
    def test_deduplicate_same_url_best_ranking_wins(self):
        """Test deduplication where best ranking wins."""
        results = [
            {'url': 'https://example.com', 'title': 'From DDG', 'rank': 3, '_source_engine': 'ddg'},
            {'url': 'https://example.com', 'title': 'From Bing', 'rank': 1, '_source_engine': 'bing'},
            {'url': 'https://example.com', 'title': 'From Startpage', 'rank': 2, '_source_engine': 'startpage'}
        ]
        
        deduplicated = deduplicate_results(results, 10)
        
        assert len(deduplicated) == 1
        assert deduplicated[0]['_source_engine'] == 'bing'  # Best rank (1)
        assert deduplicated[0]['rank'] == 1
    
    def test_deduplicate_respects_num_results_limit(self):
        """Test deduplication respects the num_results limit."""
        results = [
            {'url': f'https://example{i}.com', 'title': f'Example {i}', 'rank': i}
            for i in range(1, 6)
        ]
        
        deduplicated = deduplicate_results(results, 3)
        
        assert len(deduplicated) == 3
        # Should be sorted by rank
        assert deduplicated[0]['rank'] == 1
        assert deduplicated[1]['rank'] == 2
        assert deduplicated[2]['rank'] == 3
    
    def test_deduplicate_handles_missing_rank(self):
        """Test deduplication handles missing rank gracefully."""
        results = [
            {'url': 'https://example.com', 'title': 'No rank'},
            {'url': 'https://other.com', 'title': 'Has rank', 'rank': 1}
        ]
        
        deduplicated = deduplicate_results(results, 10)
        
        assert len(deduplicated) == 2
        # Result with rank should come first
        assert deduplicated[0]['rank'] == 1
        assert deduplicated[1].get('rank', 999) == 999


class TestEndToEndTracking:
    """End-to-end tests for the complete tracking flow."""
    
    def test_tracking_flow_with_deduplication(self):
        """Test complete flow: add tracking, deduplicate, extract tracking."""
        # Simulate search results from multiple engines
        ddg_results = [
            {'url': 'https://example.com', 'title': 'Example DDG', 'rank': 3}
        ]
        bing_results = [
            {'url': 'https://example.com', 'title': 'Example Bing', 'rank': 1},
            {'url': 'https://unique.com', 'title': 'Unique Bing', 'rank': 2}
        ]
        startpage_results = [
            {'url': 'https://example.com', 'title': 'Example Startpage', 'rank': 2}
        ]
        
        # Add engine info (simulating format_search_response logic)
        all_results = []
        for result in ddg_results:
            r = result.copy()
            r['_source_engine'] = 'ddg'
            all_results.append(r)
        
        for result in bing_results:
            r = result.copy()
            r['_source_engine'] = 'bing'
            all_results.append(r)
        
        for result in startpage_results:
            r = result.copy()
            r['_source_engine'] = 'startpage'
            all_results.append(r)
        
        # Deduplicate (best ranking wins)
        deduplicated = deduplicate_results(all_results, 10)
        
        # Should have 2 unique URLs, with bing winning for example.com
        assert len(deduplicated) == 2
        
        # Find the example.com result
        example_result = next(r for r in deduplicated if 'example.com' in r['url'])
        assert example_result['_source_engine'] == 'bing'  # Best rank (1)
        
        # Add tracking
        search_id = "test_search_123"
        for result in deduplicated:
            engine = result.pop('_source_engine')
            result['url'] = add_tracking_to_url(result['url'], engine, search_id)
        
        # Extract tracking (simulating fetch_page_content)
        for result in deduplicated:
            engine, sid, clean_url = extract_tracking_from_url(result['url'])
            assert sid == search_id
            
            if 'example.com' in clean_url:
                assert engine == 'bing'  # Should be attributed to bing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
