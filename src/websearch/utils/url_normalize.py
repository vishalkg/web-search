"""URL canonicalization for deduplication.

The shape of "the same article" varies across engines. Two URLs are
treated as duplicates if their *canonical* form is equal. Canonicalization:

  - lowercase scheme + host
  - strip ``www.`` prefix (host only)
  - drop port if it matches the scheme default (``:80`` for http, ``:443``
    for https)
  - drop fragment (``#section``)
  - drop tracking query parameters (``utm_*``, ``fbclid``, ``gclid``, etc.)
  - sort remaining query params (so ``?a=1&b=2`` == ``?b=2&a=1``)
  - normalize trailing slash on the path

Scheme normalization is deliberately one-way: ``http://`` upgrades to
``https://`` for canonical comparison only — the original URL on the result
is preserved for the agent to fetch.
"""

from typing import Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Tracking parameters that semantically don't change the destination page.
# Conservative list — anything genuinely page-relevant (``q``, ``id``,
# ``page``, etc.) stays.
# Prefix patterns. Trailing underscore is intentional — `_ga_` matches
# Google Analytics 4 measurement IDs (`_ga_ABC123`) without colliding with
# unrelated names like `_galaxy_id` or `_gain`.
_TRACKING_PARAM_PREFIXES = (
    "utm_",
    "ga_",
    "_ga_",
    "_gl_",
    "mtm_",
    "pk_",
    "matomo_",
)
_TRACKING_PARAM_EXACT = frozenset(
    {
        # Common ad/click trackers
        "fbclid",
        "gclid",
        "gclsrc",
        "dclid",
        "msclkid",
        "yclid",
        "twclid",
        "wickedid",
        "icid",
        # Google Analytics legacy single-name params
        "_ga",
        "_gid",
        "_gat",
        "_gac",
        # Mailchimp / email
        "mc_eid",
        "mc_cid",
        # Hubspot
        "_hsenc",
        "_hsmi",
        # This MCP's own tracking — extract_tracking_from_url strips these
        # at fetch time, but if a result re-circulates through dedup we
        # don't want them treated as load-bearing.
        "_src",
        "_sid",
        # Misc — `ref`/`source` are sometimes legit routing on shopping
        # sites, but for dedup purposes they're almost always click
        # attribution. Worst case: two genuinely-different pages collapse.
        "ref",
        "referrer",
        "source",
    }
)

_DEFAULT_PORTS = {"http": 80, "https": 443}


def _strip_tracking_params(query: str) -> str:
    """Remove tracking params, sort the rest, return urlencoded query string."""
    if not query:
        return ""
    kept = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _TRACKING_PARAM_EXACT:
            continue
        if any(lowered.startswith(p) for p in _TRACKING_PARAM_PREFIXES):
            continue
        kept.append((key, value))
    kept.sort()
    return urlencode(kept, doseq=True)


def _normalize_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    # Collapse double slashes anywhere except after the scheme
    while "//" in path:
        path = path.replace("//", "/")
    # Trailing-slash normalization: keep root slash, drop other trailing slashes
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _split_host_port(netloc: str) -> Tuple[str, str]:
    """Return (host, port_str) handling IPv6 brackets and userinfo."""
    # urlparse already lowercased scheme; netloc may contain user@host:port
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    if netloc.startswith("["):
        # IPv6 literal: [::1]:8080
        end = netloc.find("]")
        if end == -1:
            return netloc, ""
        host = netloc[: end + 1]
        rest = netloc[end + 1 :]
        port = rest[1:] if rest.startswith(":") else ""
        return host, port
    if ":" in netloc:
        host, port = netloc.rsplit(":", 1)
        return host, port
    return netloc, ""


def canonicalize_url(url: str) -> str:
    """Return the dedup-canonical form of ``url``. Empty/invalid → input."""
    if not isinstance(url, str) or not url:
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url

    original_scheme = (parsed.scheme or "https").lower()
    # Treat http/https as equivalent for dedup purposes
    canonical_scheme = "https" if original_scheme == "http" else original_scheme

    host, port_str = _split_host_port(parsed.netloc)
    host = _normalize_host(host)
    if port_str:
        try:
            port = int(port_str)
            # Compare against the ORIGINAL scheme's default port — :80 on http
            # and :443 on https are both implicit defaults and should drop.
            if _DEFAULT_PORTS.get(original_scheme) != port:
                host = f"{host}:{port}"
        except ValueError:
            host = f"{host}:{port_str}"
    scheme = canonical_scheme

    if not host:
        return url  # Can't canonicalize relative/malformed URLs

    path = _normalize_path(parsed.path)
    query = _strip_tracking_params(parsed.query)
    # Drop fragments — they don't change the page identity for dedup.
    return urlunparse((scheme, host, path, "", query, ""))
