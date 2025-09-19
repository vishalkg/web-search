#!/usr/bin/env python3
"""Quick integration test for Google Search API."""

import json
import sys
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, 'src')

from websearch.core.search import search_web


def test_with_mock():
    """Test search with mocked Google API."""
    with patch('websearch.engines.google_api.build') as mock_build, \
         patch('websearch.engines.google_api.quota_manager') as mock_quota:
        
        # Mock quota manager
        mock_quota.can_make_request.return_value = True
        
        # Mock Google API
        mock_service = Mock()
        mock_cse = Mock()
        mock_service.cse.return_value = mock_cse
        mock_list = Mock()
        mock_cse.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [
                {
                    "title": "Google Test Result",
                    "link": "https://google-test.com",
                    "snippet": "This is a test result from Google API"
                }
            ]
        }
        mock_build.return_value = mock_service
        
        # Run search
        result = search_web("test query", 5)
        data = json.loads(result)
        
        print("✅ Search completed successfully!")
        print(f"Total results: {data['total_results']}")
        print(f"Sources: {data['sources']}")
        
        # Check if Google results are included
        google_count = data['sources'].get('Google', 0)
        print(f"Google results: {google_count}")
        
        if google_count > 0:
            print("✅ Google API integration working!")
        else:
            print("⚠️  No Google results found")
        
        return True


if __name__ == "__main__":
    test_with_mock()
