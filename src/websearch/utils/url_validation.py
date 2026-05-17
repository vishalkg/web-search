"""URL validation to prevent SSRF and malformed-URL attacks.

The MCP server accepts arbitrary URLs from the LLM. Without validation, a
prompt-injected URL could point at private/loopback addresses, internal
services on cloud metadata endpoints, or unsupported schemes.
"""

import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse

ALLOWED_SCHEMES = frozenset({"http", "https"})


class URLValidationError(ValueError):
    """Raised when a URL fails validation checks."""


# pylint: disable=too-many-return-statements,too-many-boolean-expressions
def _is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/loopback/link-local address.

    Returns True if any A/AAAA record is in a non-public range. False if the
    host is a public address or DNS resolution fails (let the request fail
    naturally rather than blocking on transient DNS errors).
    """
    try:
        # gethostbyname_ex returns (canonical, aliases, ip_list)
        _, _, ip_list = socket.gethostbyname_ex(host)
    except (socket.gaierror, socket.herror, UnicodeError):
        return False

    for ip_str in ip_list:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True
    return False


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate URL for safety. Returns (ok, reason)."""
    if not isinstance(url, str) or not url:
        return False, "URL must be a non-empty string"

    try:
        parsed = urlparse(url)
    except ValueError as e:
        return False, f"Malformed URL: {e}"

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' not allowed (use http/https)"

    if not parsed.netloc:
        return False, "URL missing host"

    host = parsed.hostname or ""
    if not host:
        return False, "URL missing hostname"

    # Reject literal-IP shortcuts immediately
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"IP address '{host}' is in a private/reserved range"
    except ValueError:
        pass

    # Block AWS/GCP/Azure metadata endpoints by hostname even if not IP
    if host.lower() in {"metadata.google.internal", "metadata"}:
        return False, f"Cloud metadata host '{host}' is blocked"

    if _is_private_ip(host):
        return False, f"Host '{host}' resolves to a private/reserved address"

    return True, ""


def require_valid_url(url: str) -> None:
    """Raise URLValidationError if URL is invalid."""
    ok, reason = validate_url(url)
    if not ok:
        raise URLValidationError(reason)


def validate_url_fast(url: str) -> Tuple[bool, str]:
    """Cheap subset of validate_url that skips DNS resolution.

    Catches scheme/literal-IP/metadata-hostname mistakes synchronously without
    blocking. Intended as a defense-in-depth check inside async code paths
    where a full DNS-based validation has already happened upstream.
    """
    if not isinstance(url, str) or not url:
        return False, "URL must be a non-empty string"
    try:
        parsed = urlparse(url)
    except ValueError as e:
        return False, f"Malformed URL: {e}"
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' not allowed (use http/https)"
    if not parsed.netloc:
        return False, "URL missing host"
    host = parsed.hostname or ""
    if not host:
        return False, "URL missing hostname"
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"IP address '{host}' is in a private/reserved range"
    except ValueError:
        pass
    if host.lower() in {"metadata.google.internal", "metadata"}:
        return False, f"Cloud metadata host '{host}' is blocked"
    return True, ""


def require_valid_url_fast(url: str) -> None:
    """Non-blocking variant of require_valid_url for async paths."""
    ok, reason = validate_url_fast(url)
    if not ok:
        raise URLValidationError(reason)
