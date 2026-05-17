"""Result deduplication utilities.

URL deduplication uses :func:`url_normalize.canonicalize_url` so trivially
different URLs (tracking params, ``www.`` prefix, scheme differences,
trailing slashes) collapse to the same dedup key. Title comparison stays
naive (lowercased + stripped) to catch cases where the same article appears
under slightly different URLs.
"""

import logging
from typing import Any, Dict, List

from .url_normalize import canonicalize_url

logger = logging.getLogger(__name__)


def deduplicate_results(
    all_results: List[Dict[str, Any]], num_results: int
) -> List[Dict[str, Any]]:
    """Deduplicate and rank results by quality score."""
    if not all_results:
        return []

    # Sort by quality score (descending) so the best variant of a duplicate wins
    sorted_results = sorted(
        all_results, key=lambda x: x.get("quality_score", 0), reverse=True
    )

    seen_urls = set()
    seen_titles = set()
    final_results = []

    for result in sorted_results:
        if len(final_results) >= num_results:
            break

        url = result.get("url", "")
        title = result.get("title", "").lower().strip()

        canonical = canonicalize_url(url) if url else ""

        if (canonical and canonical in seen_urls) or (title and title in seen_titles):
            continue

        if canonical:
            seen_urls.add(canonical)
        if title:
            seen_titles.add(title)

        result["rank"] = len(final_results) + 1
        final_results.append(result)

    logger.info(f"Deduplicated {len(all_results)} → {len(final_results)} results")
    return final_results
