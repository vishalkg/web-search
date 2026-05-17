"""Tests for SSRF/url-validation guard."""

from unittest.mock import patch

import pytest

from websearch.utils.url_validation import (URLValidationError, require_valid_url,
                                            validate_url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/path?q=1",
        "https://en.wikipedia.org/wiki/Python",
    ],
)
def test_public_urls_accepted(url):
    with patch(
        "websearch.utils.url_validation.socket.gethostbyname_ex",
        return_value=("h", [], ["93.184.216.34"]),
    ):
        ok, reason = validate_url(url)
        assert ok, reason


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "",
        "not-a-url",
    ],
)
def test_bad_schemes_rejected(url):
    ok, _ = validate_url(url)
    assert ok is False


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
    ],
)
def test_private_literal_ips_rejected(url):
    ok, reason = validate_url(url)
    assert ok is False
    assert "private" in reason.lower() or "reserved" in reason.lower()


def test_metadata_hostname_rejected():
    ok, reason = validate_url("http://metadata.google.internal/")
    assert ok is False
    assert "metadata" in reason.lower()


def test_dns_resolves_to_private_rejected():
    with patch(
        "websearch.utils.url_validation.socket.gethostbyname_ex",
        return_value=("internal", [], ["10.0.0.5"]),
    ):
        ok, reason = validate_url("http://internal.corp/")
        assert ok is False
        assert "private" in reason.lower() or "reserved" in reason.lower()


def test_require_valid_url_raises():
    with pytest.raises(URLValidationError):
        require_valid_url("file:///etc/passwd")
