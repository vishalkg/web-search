"""Optimized result ranking with quality-first algorithm and diversity guarantees."""

import logging
from typing import Any, Dict, List, Optional

from ..utils.deduplication import deduplicate_results
from ..utils.relevance import freshness_score, query_overlap
from ..utils.url_normalize import canonicalize_url

logger = logging.getLogger(__name__)


def quality_first_ranking_fallback(
    google_startpage_results: List[Dict[str, Any]],
    bing_ddg_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Quality-first ranking for 3-engine fallback system.

    ``query``, when provided, enables query-keyword-overlap and freshness
    contributions to ``quality_score``.
    """

    def prepare_engine_results(
        results: List[Dict[str, Any]], engine: str
    ) -> List[Dict[str, Any]]:
        """Prepare results from a single engine."""
        prepared = []
        for i, result in enumerate(results):
            if not result.get("url") or not result.get("title"):
                continue

            prepared_result = result.copy()
            prepared_result["engine"] = engine
            prepared_result["engine_rank"] = i + 1
            prepared.append(prepared_result)

        return prepared

    # Prepare results from all engines
    google_startpage_prepared = prepare_engine_results(
        google_startpage_results, "fallback_primary"
    )
    bing_ddg_prepared = prepare_engine_results(bing_ddg_results, "fallback_secondary")
    brave_prepared = prepare_engine_results(brave_results, "brave")

    logger.info(
        f"Fallback candidate pool: Google/Startpage={len(google_startpage_prepared)}, "
        f"Bing/DDG={len(bing_ddg_prepared)}, Brave={len(brave_prepared)}"
    )

    # Combine all candidates
    all_candidates = google_startpage_prepared + bing_ddg_prepared + brave_prepared

    if not all_candidates:
        logger.warning("No candidates from any engine")
        return []

    # Apply quality scoring and deduplication
    scored_candidates = []
    for candidate in all_candidates:
        score = _calculate_quality_score(
            candidate, candidate.get("engine_rank", 1), query=query
        )
        candidate["quality_score"] = score
        scored_candidates.append(candidate)

    # Deduplicate and rank
    final_results = deduplicate_results(scored_candidates, num_results)

    logger.info(f"Final fallback ranking: {len(final_results)} results")
    return final_results


def quality_first_ranking(
    ddg_results: List[Dict[str, Any]],
    bing_results: List[Dict[str, Any]],
    startpage_results: List[Dict[str, Any]],
    google_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Quality-first candidate pool algorithm.

    1. Take top 4 results from each engine.
    2. Score each with engine-rank base + query-overlap + freshness.
    3. Deduplicate by canonical URL keeping highest-scored version.
    4. Sort by quality score descending and return top ``num_results``.

    ``query`` is optional for backward compatibility; passing it enables
    query-relevance and freshness contributions to ``quality_score``.
    """
    # Take top 4 from each engine for candidate pool
    candidates_per_engine = min(4, num_results // 2)

    def prepare_engine_results(
        results: List[Dict[str, Any]], engine: str
    ) -> List[Dict[str, Any]]:
        """Add engine metadata and ranking to results"""
        prepared = []
        for i, result in enumerate(results[:candidates_per_engine]):
            result_copy = result.copy()
            result_copy["source"] = engine
            result_copy["engine_rank"] = i + 1
            result_copy["quality_score"] = _calculate_quality_score(
                result_copy, i + 1, query=query
            )
            prepared.append(result_copy)
        return prepared

    # Prepare results from all engines
    ddg_prepared = prepare_engine_results(ddg_results, "duckduckgo")
    bing_prepared = prepare_engine_results(bing_results, "bing")
    startpage_prepared = prepare_engine_results(startpage_results, "startpage")
    google_prepared = prepare_engine_results(google_results, "google")
    brave_prepared = prepare_engine_results(brave_results, "brave")

    logger.info(
        f"Candidate pool: DDG={len(ddg_prepared)}, "
        f"Bing={len(bing_prepared)}, Startpage={len(startpage_prepared)}, "
        f"Google={len(google_prepared)}, Brave={len(brave_prepared)}"
    )

    # Combine all candidates
    all_candidates = (
        ddg_prepared
        + bing_prepared
        + startpage_prepared
        + google_prepared
        + brave_prepared
    )

    # Deduplicate keeping highest quality version
    deduped = _deduplicate_by_quality(all_candidates)

    # Sort by quality score (higher is better)
    deduped.sort(key=lambda x: x["quality_score"], reverse=True)

    # Return top results
    final_results = deduped[:num_results]

    logger.info(
        f"Quality ranking: {len(all_candidates)} candidates → "
        f"{len(deduped)} unique → {len(final_results)} final"
    )

    return final_results


def _calculate_quality_score(
    result: Dict[str, Any], engine_rank: int, query: Optional[str] = None
) -> float:
    """Calculate quality score from engine rank, content, query relevance, freshness.

    Components (roughly equal-weight when fully active):
      - base_score: engine_rank position (10 -> 0 across ranks 1..6)
      - content_bonus: ±1 for substantial vs sparse title/snippet
      - relevance_bonus: 0..+4 from query-keyword overlap on title+snippet
      - freshness_bonus: 0..+2 exponential decay on dates parsed from snippet

    Query-blind callers (legacy paths) get the original score unchanged.
    """
    base_score = 10.0 - (engine_rank - 1) * 2.0

    title = result.get("title", "")
    snippet = result.get("snippet", "")
    title_length = len(title)
    snippet_length = len(snippet)

    content_bonus = 0.0
    if title_length > 20:
        content_bonus += 0.5
    if snippet_length > 50:
        content_bonus += 0.5
    if title_length < 10 or snippet_length < 20:
        content_bonus -= 1.0

    relevance_bonus = 0.0
    freshness_bonus = 0.0
    if query:
        overlap = query_overlap(query, title, snippet)
        relevance_bonus = overlap * 4.0
        # Freshness from snippet+title text. Engines vary on where they put
        # the publication date; checking both catches "Python 3.12 released
        # — March 2024" style titles. Half-life of one year keeps multi-
        # year-old articles still relevant for evergreen queries.
        freshness_bonus = freshness_score(f"{title} {snippet}") * 2.0

    return max(
        0.1, base_score + content_bonus + relevance_bonus + freshness_bonus
    )


def _deduplicate_by_quality(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates keeping the highest quality version (canonical key)."""
    url_to_best: Dict[str, Dict[str, Any]] = {}

    for result in results:
        url = result.get("url", "")
        if not url:
            continue
        key = canonicalize_url(url) or url
        quality_score = result["quality_score"]

        if key not in url_to_best or quality_score > url_to_best[key]["quality_score"]:
            url_to_best[key] = result

    return list(url_to_best.values())


def get_engine_distribution(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get distribution of results by engine for monitoring."""
    distribution: Dict[str, int] = {
        "duckduckgo": 0,
        "bing": 0,
        "startpage": 0,
        "google": 0,
        "brave": 0,
    }
    for result in results:
        engine = result.get("source", "unknown")
        distribution[engine] = distribution.get(engine, 0) + 1
    return distribution
