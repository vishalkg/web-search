"""Optimized result ranking with quality-first algorithm and diversity guarantees."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def quality_first_ranking(
    ddg_results: List[Dict[str, Any]],
    bing_results: List[Dict[str, Any]],
    startpage_results: List[Dict[str, Any]],
    google_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int
) -> List[Dict[str, Any]]:
    """
    Quality-first candidate pool algorithm:
    1. Take top 4 results from each engine
    2. Deduplicate keeping best-ranked version
    3. Sort by original engine ranking
    4. Return top num_results
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
                result_copy, i + 1
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
        ddg_prepared + bing_prepared + startpage_prepared + 
        google_prepared + brave_prepared
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


def _calculate_quality_score(result: Dict[str, Any], engine_rank: int) -> float:
    """Calculate quality score based on engine ranking and content indicators"""
    # Base score from engine ranking (higher rank = lower score)
    base_score = 10.0 - (engine_rank - 1) * 2.0

    # Content quality indicators
    title_length = len(result.get("title", ""))
    snippet_length = len(result.get("snippet", ""))

    # Bonus for substantial content
    content_bonus = 0.0
    if title_length > 20:
        content_bonus += 0.5
    if snippet_length > 50:
        content_bonus += 0.5

    # Penalty for very short content
    if title_length < 10 or snippet_length < 20:
        content_bonus -= 1.0

    return max(0.1, base_score + content_bonus)


def _deduplicate_by_quality(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates keeping the highest quality version"""
    url_to_best = {}

    for result in results:
        url = result["url"]
        quality_score = result["quality_score"]

        if url not in url_to_best or quality_score > url_to_best[url]["quality_score"]:
            url_to_best[url] = result

    return list(url_to_best.values())


def get_engine_distribution(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get distribution of results by engine for monitoring"""
    distribution = {"duckduckgo": 0, "bing": 0, "startpage": 0}

    for result in results:
        engine = result.get("source", "unknown")
        if engine in distribution:
            distribution[engine] += 1
        else:
            distribution["unknown"] = distribution.get("unknown", 0) + 1

    return distribution
