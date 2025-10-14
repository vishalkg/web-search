"""Tests for Brave Search API integration."""

from unittest.mock import Mock, patch

import pytest

from src.websearch.engines.brave_api import search_brave_api


class TestBraveAPI:
    @patch("src.websearch.engines.brave_api.API_KEY", "test_key")
    @patch("src.websearch.engines.brave_api.quota_manager")
    @patch("src.websearch.engines.brave_api.requests.get")
    def test_search_brave_api_success(self, mock_get, mock_quota):
        """Test successful Brave API search."""
        # Mock quota manager
        mock_quota.can_make_request.return_value = True

        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Test Title",
                        "url": "https://example.com",
                        "description": "Test description",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        results = search_brave_api("test query", 10)

        assert len(results) == 1
        assert results[0]["title"] == "Test Title"
        assert results[0]["source"] == "Brave"
        mock_get.assert_called_once()
        mock_quota.record_request.assert_called_once()

    def test_search_brave_api_no_key(self):
        """Test Brave API when key is not configured."""
        with patch("src.websearch.engines.brave_api.API_KEY", None):
            results = search_brave_api("test query", 10)
            assert results == []

    @patch("src.websearch.engines.brave_api.quota_manager")
    def test_search_brave_api_quota_exhausted(self, mock_quota):
        """Test Brave API when quota is exhausted."""
        mock_quota.can_make_request.return_value = False

        results = search_brave_api("test query", 10)

        assert results == []

    @patch("src.websearch.engines.brave_api.quota_manager")
    @patch("src.websearch.engines.brave_api.requests.get")
    def test_search_brave_api_request_error(self, mock_get, mock_quota):
        """Test Brave API request error handling."""
        mock_quota.can_make_request.return_value = True
        mock_get.side_effect = Exception("Network error")

        results = search_brave_api("test query", 10)

        assert results == []
