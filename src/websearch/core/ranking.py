"""Optimized result ranking with quality-first algorithm and diversity guarantees."""

import logging
from typing import Any, Dict, List

from ..utils.deduplication import deduplicate_results
from ..utils.smart_deduplication import (
    SmartDeduplicator, is_smart_deduplication_enabled,
    is_comparison_mode_enabled, compare_deduplication_methods
)

logger = logging.getLogger(__name__)


def quality_first_ranking_fallback(
    google_startpage_results: List[Dict[str, Any]],
    bing_ddg_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int
) -> List[Dict[str, Any]]:
    """Quality-first ranking for 3-engine fallback system."""

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
    bing_ddg_prepared = prepare_engine_results(
        bing_ddg_results, "fallback_secondary"
    )
    brave_prepared = prepare_engine_results(brave_results, "brave")

    logger.info(
        f"Fallback candidate pool: Google/Startpage={len(google_startpage_prepared)}, "
        f"Bing/DDG={len(bing_ddg_prepared)}, Brave={len(brave_prepared)}"
    )

    # Combine all candidates
    all_candidates = (
        google_startpage_prepared + bing_ddg_prepared + brave_prepared
    )

    if not all_candidates:
        logger.warning("No candidates from any engine")
        return []

    # Apply quality scoring and deduplication
    scored_candidates = []
    for candidate in all_candidates:
        score = _calculate_quality_score(candidate, candidate.get("engine_rank", 1))
        candidate["quality_score"] = score
        scored_candidates.append(candidate)

    # Choose deduplication method based on feature flag
    if is_comparison_mode_enabled():
        # Comparison mode: log both methods but use original
        comparison = compare_deduplication_methods(scored_candidates, num_results)
        logger.info(f"🔬 Deduplication comparison: {comparison}")
        final_results = deduplicate_results(scored_candidates, num_results)
    elif is_smart_deduplication_enabled():
        # Use smart deduplication
        smart_dedup = SmartDeduplicator()
        final_results = smart_dedup.process_results(scored_candidates)[:num_results]
        logger.info("🧠 Using smart deduplication")
    else:
        # Use original deduplication
        final_results = deduplicate_results(scored_candidates, num_results)
        logger.info("📝 Using original deduplication")

    logger.info(f"🏆 Final fallback ranking: {len(final_results)} results")
    return final_results


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

    # Choose deduplication method based on feature flag
    if is_comparison_mode_enabled():
        # Comparison mode: log both methods but use original
        comparison = compare_deduplication_methods(all_candidates, num_results)
        logger.info(f"🔬 5-Engine deduplication comparison: {comparison}")
        # Use original method for comparison mode
        deduped = _deduplicate_by_quality(all_candidates)
        deduped.sort(key=lambda x: x["quality_score"], reverse=True)
        final_results = deduped[:num_results]
    elif is_smart_deduplication_enabled():
        # Use smart deduplication
        smart_dedup = SmartDeduplicator()
        final_results = smart_dedup.process_results(all_candidates)[:num_results]
        logger.info("🧠 Using smart deduplication for 5-engine ranking")
    else:
        # Use original deduplication
        deduped = _deduplicate_by_quality(all_candidates)
        deduped.sort(key=lambda x: x["quality_score"], reverse=True)
        final_results = deduped[:num_results]
        logger.info("📝 Using original deduplication for 5-engine ranking")

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
