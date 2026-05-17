"""Tests for URL canonicalization used by deduplication."""

import pytest

from websearch.utils.url_normalize import canonicalize_url


@pytest.mark.parametrize(
    "a,b",
    [
        # Scheme equivalence
        ("http://example.com/", "https://example.com/"),
        # Trailing slash
        ("https://example.com/foo", "https://example.com/foo/"),
        ("https://example.com/foo/", "https://example.com/foo"),
        # www prefix
        ("https://www.example.com/x", "https://example.com/x"),
        # Case-insensitive host
        ("https://Example.COM/x", "https://example.com/x"),
        # Fragment ignored
        ("https://example.com/x#section", "https://example.com/x"),
        # Default ports stripped
        ("https://example.com:443/x", "https://example.com/x"),
        ("http://example.com:80/x", "https://example.com/x"),
    ],
)
def test_equivalent_urls_canonicalize_identically(a, b):
    assert canonicalize_url(a) == canonicalize_url(b)


@pytest.mark.parametrize(
    "url,expected_in_canonical",
    [
        ("https://example.com/x?utm_source=newsletter", "example.com/x"),
        ("https://example.com/x?fbclid=abc&id=42", "id=42"),
        ("https://example.com/x?gclid=xyz", "example.com/x"),
        ("https://example.com/x?_src=b&_sid=42", "example.com/x"),
        ("https://example.com/x?mc_eid=foo&page=2", "page=2"),
    ],
)
def test_tracking_params_stripped(url, expected_in_canonical):
    canonical = canonicalize_url(url)
    assert "utm_" not in canonical
    assert "fbclid" not in canonical
    assert "gclid" not in canonical
    assert "_src" not in canonical
    assert "mc_eid" not in canonical
    assert expected_in_canonical in canonical


def test_real_query_params_preserved():
    """Page-relevant params (id, q, page) must NOT be stripped."""
    canonical = canonicalize_url("https://example.com/search?q=python&page=3")
    assert "q=python" in canonical
    assert "page=3" in canonical


def test_query_params_sorted():
    """Same-set-different-order queries collapse to one key."""
    a = canonicalize_url("https://example.com/x?a=1&b=2")
    b = canonicalize_url("https://example.com/x?b=2&a=1")
    assert a == b


def test_non_default_port_preserved():
    canonical = canonicalize_url("https://example.com:8443/x")
    assert ":8443" in canonical


def test_empty_and_invalid_inputs_dont_crash():
    assert canonicalize_url("") == ""
    assert canonicalize_url("not-a-url") == "not-a-url"  # bare string passthrough
    assert canonicalize_url(None) == ""  # type: ignore[arg-type]


def test_double_slashes_collapsed():
    assert canonicalize_url("https://example.com//foo//bar") == canonicalize_url(
        "https://example.com/foo/bar"
    )


def test_userinfo_stripped_for_dedup():
    """user@host shouldn't make a URL distinct."""
    assert canonicalize_url("https://user@example.com/x") == canonicalize_url(
        "https://example.com/x"
    )


def test_galaxy_id_not_stripped_by_ga_prefix():
    """Regression: tightened `_ga_` prefix must not match `_galaxy_id`."""
    canonical = canonicalize_url("https://example.com/x?_galaxy_id=42")
    assert "_galaxy_id=42" in canonical


def test_ga4_measurement_id_stripped():
    """The real GA4 param shape `_ga_ABC123` should still drop."""
    canonical = canonicalize_url("https://example.com/x?_ga_ABC123=1.2.3")
    assert "_ga_" not in canonical


def test_legacy_ga_params_stripped():
    """Single-name analytics params (_ga, _gid, _gat, _gac) drop via exact list."""
    for param in ("_ga", "_gid", "_gat", "_gac"):
        canonical = canonicalize_url(f"https://example.com/x?{param}=1")
        assert param not in canonical, f"{param} should have been stripped"


def test_canonical_root_url_keeps_trailing_slash():
    """Pin the canonical form for a bare-host URL."""
    assert canonicalize_url("https://example.com").endswith("/")
    assert canonicalize_url("https://example.com/") == canonicalize_url(
        "https://example.com"
    )
