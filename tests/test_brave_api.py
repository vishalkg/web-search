"""Tests for Brave Search API integration."""

from unittest.mock import Mock, patch

import pytest

from websearch.engines.brave_api import (async_search_brave_api,
                                         search_brave_api)


class TestBraveAPISync:
    @patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "k"})
    @patch("websearch.engines.brave_api.unified_quota")
    @patch("websearch.engines.brave_api.requests.get")
    def test_success(self, mock_get, mock_quota):
        mock_quota.can_make_request.return_value = True
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "T",
                        "url": "https://example.com",
                        "description": "D",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        results = search_brave_api("q", 10)

        assert len(results) == 1
        assert results[0]["source"] == "brave"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["rank"] == 1
        mock_quota.record_request.assert_called_once_with("brave")

    @patch.dict("os.environ", {}, clear=True)
    def test_no_key(self):
        assert search_brave_api("q", 10) == []

    @patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "k"})
    @patch("websearch.engines.brave_api.unified_quota")
    def test_quota_exhausted(self, mock_quota):
        mock_quota.can_make_request.return_value = False
        assert search_brave_api("q", 10) == []
        mock_quota.record_request.assert_not_called()

    @patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "k"})
    @patch("websearch.engines.brave_api.unified_quota")
    @patch("websearch.engines.brave_api.requests.get")
    def test_request_error_returns_empty(self, mock_get, mock_quota):
        mock_quota.can_make_request.return_value = True
        import requests as rq

        mock_get.side_effect = rq.exceptions.ConnectionError("net down")
        assert search_brave_api("q", 10) == []
        mock_quota.record_request.assert_not_called()

    @patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "k"})
    @patch("websearch.engines.brave_api.unified_quota")
    @patch("websearch.engines.brave_api.requests.get")
    def test_rate_limit_429_returns_empty(self, mock_get, mock_quota):
        mock_quota.can_make_request.return_value = True
        import requests as rq

        mock_response = Mock()
        mock_response.status_code = 429
        err = rq.exceptions.HTTPError("429")
        err.response = mock_response
        mock_response.raise_for_status.side_effect = err
        mock_get.return_value = mock_response
        assert search_brave_api("q", 10) == []
        mock_quota.record_request.assert_not_called()


class TestBraveAPIAsync:
    @pytest.mark.asyncio
    @patch.dict("os.environ", {}, clear=True)
    async def test_async_no_key(self):
        assert await async_search_brave_api("q", 5) == []
