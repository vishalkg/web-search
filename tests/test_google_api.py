"""Tests for Google Custom Search API integration."""

from unittest.mock import Mock, patch

import pytest

from websearch.engines.google_api import (async_search_google_api,
                                          search_google_api)


class TestGoogleAPISync:
    @patch("websearch.engines.google_api.unified_quota")
    @patch.dict("os.environ", {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "id"})
    @patch("websearch.engines.google_api.build")
    def test_success(self, mock_build, mock_quota):
        mock_quota.can_make_request.return_value = True
        mock_service = Mock()
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "title": "T",
                    "link": "https://example.com",
                    "snippet": "S",
                }
            ]
        }
        mock_build.return_value = mock_service

        results = search_google_api("q", 5)

        assert len(results) == 1
        assert results[0]["source"] == "google"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["rank"] == 1
        mock_quota.record_request.assert_called_once_with("google")

    @patch("websearch.engines.google_api.unified_quota")
    @patch.dict("os.environ", {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ID": "id"})
    def test_quota_exhausted(self, mock_quota):
        mock_quota.can_make_request.return_value = False
        results = search_google_api("q", 5)
        assert results == []
        mock_quota.record_request.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    def test_no_credentials(self):
        results = search_google_api("q", 5)
        assert results == []


class TestGoogleAPIAsync:
    @pytest.mark.asyncio
    @patch("websearch.engines.google_api.search_google_api")
    async def test_async_wrapper_calls_sync(self, mock_sync):
        mock_sync.return_value = [{"title": "T", "url": "u", "snippet": "s"}]
        results = await async_search_google_api("q", 3)
        assert results == mock_sync.return_value
        mock_sync.assert_called_once_with("q", 3)
