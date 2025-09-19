"""Tests for Google Search API integration."""

import pytest
from unittest.mock import Mock, patch

from src.websearch.engines.google_api import search_google_api
from src.websearch.utils.quota import GoogleQuotaManager


class TestGoogleAPI:
    def test_quota_manager_new_day(self):
        """Test quota manager resets on new day."""
        manager = GoogleQuotaManager()
        assert manager.can_make_request()

    @patch('src.websearch.engines.google_api.build')
    @patch('src.websearch.engines.google_api.quota_manager')
    def test_search_google_api_success(self, mock_quota, mock_build):
        """Test successful Google API search."""
        # Mock quota manager
        mock_quota.can_make_request.return_value = True
        
        # Mock Google API response
        mock_service = Mock()
        mock_cse = Mock()
        mock_service.cse.return_value = mock_cse
        mock_list = Mock()
        mock_cse.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [
                {
                    "title": "Test Title",
                    "link": "https://example.com",
                    "snippet": "Test snippet"
                }
            ]
        }
        mock_build.return_value = mock_service
        
        results = search_google_api("test query", 10)
        
        assert len(results) == 1
        assert results[0]["title"] == "Test Title"
        assert results[0]["source"] == "Google"
        mock_quota.record_request.assert_called_once()

    @patch('src.websearch.engines.google_api.quota_manager')
    def test_search_google_api_quota_exhausted(self, mock_quota):
        """Test Google API when quota is exhausted."""
        mock_quota.can_make_request.return_value = False
        
        results = search_google_api("test query", 10)
        
        assert results == []
        mock_quota.record_request.assert_not_called()
