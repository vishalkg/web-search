"""HTTP utilities and request handling."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12

# Configure session with connection pooling and retries
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)

requests_session = requests.Session()
requests_session.mount("http://", adapter)
requests_session.mount("https://", adapter)
requests_session.headers.update({"User-Agent": DEFAULT_USER_AGENT})


def make_request(url: str, timeout: int = REQUEST_TIMEOUT) -> requests.Response:
    """Make HTTP request with connection pooling, retries and error handling"""
    response = requests_session.get(url, timeout=timeout)
    response.raise_for_status()
    return response
