"""HTTP utilities and request handling."""

import logging

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import (CONTENT_TIMEOUT, MAX_REDIRECTS, MAX_RESPONSE_BYTES,
                      USER_AGENT)
from .connection_pool import get_session
from .url_validation import require_valid_url, require_valid_url_fast

logger = logging.getLogger(__name__)


class ResponseTooLargeError(Exception):
    """Raised when an HTTP response body exceeds MAX_RESPONSE_BYTES."""


# Configure sync session with connection pooling and retries
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)

requests_session = requests.Session()
requests_session.mount("http://", adapter)
requests_session.mount("https://", adapter)
requests_session.headers.update({"User-Agent": USER_AGENT})
# Set once at module load — never mutate the shared session per-request.
requests_session.max_redirects = MAX_REDIRECTS


def make_request(url: str, timeout: int = CONTENT_TIMEOUT) -> requests.Response:
    """Make sync HTTP request with bounded redirects and response size."""
    require_valid_url(url)
    response = requests_session.get(url, timeout=timeout, stream=True)
    try:
        response.raise_for_status()
        # Drain bytes with a hard cap to avoid OOM on hostile servers.
        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            content.extend(chunk)
            if len(content) > MAX_RESPONSE_BYTES:
                raise ResponseTooLargeError(
                    f"Response exceeded {MAX_RESPONSE_BYTES} bytes"
                )
        # _content is a private attribute of requests.Response, but accessing it
        # is the supported way to swap a streamed body in. See requests #2155.
        response._content = bytes(content)  # pylint: disable=protected-access
        return response
    except BaseException:
        response.close()
        raise


async def make_request_async(url: str, timeout: int = CONTENT_TIMEOUT) -> str:
    """Async HTTP request using global pool, with redirect and size limits."""
    # Fast (non-DNS) check; the LLM-facing tool runs the full DNS check.
    require_valid_url_fast(url)
    session = get_session()
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with session.get(
        url,
        timeout=client_timeout,
        max_redirects=MAX_REDIRECTS,
        allow_redirects=True,
    ) as response:
        response.raise_for_status()

        # Honor Content-Length up front when present
        cl = response.headers.get("Content-Length")
        if cl is not None:
            try:
                if int(cl) > MAX_RESPONSE_BYTES:
                    raise ResponseTooLargeError(
                        f"Content-Length {cl} exceeds {MAX_RESPONSE_BYTES}"
                    )
            except ValueError:
                pass

        # Stream body with a running cap
        chunks = bytearray()
        async for chunk in response.content.iter_chunked(64 * 1024):
            chunks.extend(chunk)
            if len(chunks) > MAX_RESPONSE_BYTES:
                raise ResponseTooLargeError(
                    f"Response exceeded {MAX_RESPONSE_BYTES} bytes"
                )

        # Decode using charset hints when available
        encoding = response.charset or "utf-8"
        try:
            return chunks.decode(encoding, errors="replace")
        except LookupError:
            return chunks.decode("utf-8", errors="replace")
