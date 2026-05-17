"""Tests for response-size and redirect limits in utils/http.py."""

from unittest.mock import patch

import pytest

import websearch.utils.http as http_mod
from websearch.utils.http import (ResponseTooLargeError, make_request,
                                  make_request_async)


class _FakeAsyncResponse:
    def __init__(self, headers=None, body_chunks=None, charset="utf-8", status=200):
        self.headers = headers or {}
        self._body_chunks = body_chunks or []
        self.charset = charset
        self.status = status
        self.content = self  # response.content.iter_chunked() lives on .content

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    def raise_for_status(self):
        return None

    async def iter_chunked(self, _size):
        for chunk in self._body_chunks:
            yield chunk


class _FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


@pytest.mark.asyncio
async def test_async_content_length_header_rejects_oversized():
    big = http_mod.MAX_RESPONSE_BYTES + 1
    resp = _FakeAsyncResponse(headers={"Content-Length": str(big)})
    with patch("websearch.utils.http.get_session", return_value=_FakeSession(resp)):
        with pytest.raises(ResponseTooLargeError):
            await make_request_async("https://example.com/")


@pytest.mark.asyncio
async def test_async_streaming_overflow_rejects():
    chunk = b"x" * 100_000
    n_chunks = (http_mod.MAX_RESPONSE_BYTES // len(chunk)) + 2
    resp = _FakeAsyncResponse(body_chunks=[chunk] * n_chunks)
    with patch("websearch.utils.http.get_session", return_value=_FakeSession(resp)):
        with pytest.raises(ResponseTooLargeError):
            await make_request_async("https://example.com/")


@pytest.mark.asyncio
async def test_async_under_limit_succeeds():
    resp = _FakeAsyncResponse(body_chunks=[b"hello world"])
    with patch("websearch.utils.http.get_session", return_value=_FakeSession(resp)):
        text = await make_request_async("https://example.com/")
    assert text == "hello world"


@pytest.mark.asyncio
async def test_async_rejects_private_url_before_dispatch():
    """Fast validation must short-circuit before any HTTP call."""
    from websearch.utils.url_validation import URLValidationError

    with patch("websearch.utils.http.get_session") as mock_get_session:
        with pytest.raises(URLValidationError):
            await make_request_async("http://127.0.0.1/")
    mock_get_session.assert_not_called()


def test_sync_streaming_overflow_rejects(monkeypatch):
    """Sync make_request size cap. Use a fake response object."""

    class _FakeResp:
        def __init__(self):
            self.closed = False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=None):
            for _ in range((http_mod.MAX_RESPONSE_BYTES // 100_000) + 2):
                yield b"x" * 100_000

        def close(self):
            self.closed = True

    fake = _FakeResp()
    monkeypatch.setattr(http_mod.requests_session, "get", lambda *a, **kw: fake)
    with pytest.raises(ResponseTooLargeError):
        make_request("https://example.com/")
    assert fake.closed is True


def test_sync_rejects_private_url_before_dispatch(monkeypatch):
    """Sync path must also short-circuit on bad URL."""
    from websearch.utils.url_validation import URLValidationError

    called = {"n": 0}

    def _spy(*_a, **_kw):
        called["n"] += 1

    monkeypatch.setattr(http_mod.requests_session, "get", _spy)
    with pytest.raises(URLValidationError):
        make_request("http://127.0.0.1/")
    assert called["n"] == 0
