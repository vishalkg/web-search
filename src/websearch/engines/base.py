"""Base search engine functionality."""

import logging
from typing import Any, Callable, Dict, List

from bs4 import BeautifulSoup
from requests.exceptions import (ConnectionError, HTTPError, RequestException,
                                 Timeout)

from ..utils.http import make_request

logger = logging.getLogger(__name__)


def search_engine_base(
    url: str, parser_func: Callable, source_name: str, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Base function for search engine implementations"""
    try:
        response = make_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
        results = parser_func(soup, num_results)
        logger.info(f"{source_name} found {len(results)} results")
        return results
    except Timeout:
        logger.error(f"{source_name} search timed out")
        return []
    except ConnectionError as e:
        logger.error(f"{source_name} search connection error: {str(e)}")
        return []
    except HTTPError as e:
        status_code = e.response.status_code if hasattr(e, "response") else "unknown"
        logger.error(f"{source_name} search HTTP error {status_code}: {str(e)}")
        return []
    except RequestException as e:
        logger.error(f"{source_name} search request error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"{source_name} search failed with unexpected error: {str(e)}")
        return []
