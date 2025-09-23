"""Result deduplication utilities."""

import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def deduplicate_results(
    all_results: List[Dict[str, Any]], num_results: int
) -> List[Dict[str, Any]]:
    """Deduplicate and rank results by quality score."""
    if not all_results:
        return []

    # Sort by quality score (descending)
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

        # Normalize URL for comparison
        try:
            parsed = urlparse(url)
            normalized_url = f"{parsed.netloc}{parsed.path}".lower()
        except Exception:
            normalized_url = url.lower()

        # Skip if we've seen this URL or very similar title
        if normalized_url in seen_urls or title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(title)

        # Add rank for final results
        result["rank"] = len(final_results) + 1
        final_results.append(result)

    logger.info(f"🔄 Deduplicated {len(all_results)} → {len(final_results)} results")
    return final_results
