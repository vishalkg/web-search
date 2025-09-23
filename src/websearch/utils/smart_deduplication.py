"""Smart result deduplication with domain diversity and semantic similarity."""

import logging
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def jaccard_similarity_3gram(text1: str, text2: str) -> float:
    """Calculate 3-gram Jaccard similarity between two texts."""
    if not text1 or not text2:
        return 0.0

    # Normalize text
    text1 = re.sub(r'[^\w\s]', ' ', text1.lower()).strip()
    text2 = re.sub(r'[^\w\s]', ' ', text2.lower()).strip()

    if len(text1) < 3 or len(text2) < 3:
        return 1.0 if text1 == text2 else 0.0

    # Generate 3-grams (word-based, not character-based)
    def get_3grams(text: str) -> Set[str]:
        words = text.split()
        if len(words) < 3:
            # For short texts, use word-level similarity
            return set(words)
        return {' '.join(words[i:i+3]) for i in range(len(words) - 2)}

    grams1 = get_3grams(text1)
    grams2 = get_3grams(text2)

    if not grams1 and not grams2:
        return 1.0
    if not grams1 or not grams2:
        return 0.0

    intersection = len(grams1 & grams2)
    union = len(grams1 | grams2)

    return intersection / union if union > 0 else 0.0


def extract_domain(url: str) -> str:
    """Extract normalized domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain:  # Valid URL with netloc
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        else:  # Invalid URL, return original
            return url.lower()
    except Exception:
        # For invalid URLs, return the original string lowercased
        return url.lower()


def calculate_content_quality(result: Dict[str, Any]) -> float:
    """Calculate content quality score based on snippet richness."""
    base_score = result.get('quality_score', 0.0)

    snippet = result.get('snippet', '')
    title = result.get('title', '')

    # Rich snippet bonuses
    quality_bonus = 0.0

    # Length bonus (longer snippets usually more informative)
    if len(snippet) >= 100:
        quality_bonus += 0.2
    elif len(snippet) >= 50:
        quality_bonus += 0.1

    # Structured content indicators
    if any(indicator in snippet.lower() for indicator in ['•', ':', '|', '—', '–']):
        quality_bonus += 0.1

    # Avoid thin content
    if len(snippet) < 20 or not snippet.strip():
        quality_bonus -= 0.3

    # Title quality
    if len(title) > 10 and not title.isupper():
        quality_bonus += 0.05

    return min(base_score + quality_bonus, 10.0)


def enforce_domain_diversity(
    results: List[Dict[str, Any]], max_per_domain: int = 2
) -> List[Dict[str, Any]]:
    """Enforce domain diversity while preserving quality ranking."""
    if not results:
        return results

    domain_counts = defaultdict(int)
    filtered_results = []

    for result in results:
        url = result.get('url', '')
        domain = extract_domain(url)

        if domain_counts[domain] < max_per_domain:
            domain_counts[domain] += 1
            filtered_results.append(result)

    logger.info(f"Domain diversity: {len(domain_counts)} unique domains, "
                f"filtered {len(results) - len(filtered_results)} results")

    return filtered_results


def semantic_deduplication(
    results: List[Dict[str, Any]], similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Remove semantically similar results using title/snippet similarity."""
    if not results:
        return results

    deduplicated = []

    for candidate in results:
        candidate_title = candidate.get('title', '')
        candidate_snippet = candidate.get('snippet', '')

        is_duplicate = False

        for existing in deduplicated:
            existing_title = existing.get('title', '')
            existing_snippet = existing.get('snippet', '')

            # Check title similarity
            title_similarity = jaccard_similarity_3gram(candidate_title, existing_title)

            # Check snippet similarity
            snippet_similarity = jaccard_similarity_3gram(
                candidate_snippet, existing_snippet
            )

            # Consider duplicate if either title or snippet is highly similar
            if (title_similarity >= similarity_threshold or
                    snippet_similarity >= similarity_threshold):
                is_duplicate = True
                logger.debug(
                    f"Semantic duplicate detected: "
                    f"title_sim={title_similarity:.2f}, "
                    f"snippet_sim={snippet_similarity:.2f}"
                )
                break

        if not is_duplicate:
            deduplicated.append(candidate)

    logger.info(f"Semantic deduplication: {len(results)} → {len(deduplicated)} results")
    return deduplicated


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze result quality metrics for comparison."""
    if not results:
        return {'unique_domains': 0, 'avg_snippet_length': 0, 'total_results': 0}

    domains = set()
    snippet_lengths = []

    for result in results[:10]:  # Analyze top 10
        url = result.get('url', '')
        domain = extract_domain(url)
        domains.add(domain)

        snippet = result.get('snippet', '')
        snippet_lengths.append(len(snippet))

    return {
        'unique_domains': len(domains),
        'avg_snippet_length': (
            sum(snippet_lengths) / len(snippet_lengths)
            if snippet_lengths else 0
        ),
        'total_results': len(results),
        'domain_list': list(domains)
    }


class SmartDeduplicator:
    """Smart result deduplication with domain diversity and semantic similarity."""

    def __init__(
        self, similarity_threshold: float = 0.7, max_per_domain: int = 2
    ):
        self.similarity_threshold = similarity_threshold
        self.max_per_domain = max_per_domain

    def process_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply smart deduplication pipeline to search results."""
        if not results:
            return results

        logger.info(f"Smart deduplication starting with {len(results)} results")

        # Step 1: Update content quality scores
        for result in results:
            result['quality_score'] = calculate_content_quality(result)

        # Step 2: Re-sort by updated quality scores
        results_sorted = sorted(
            results, key=lambda x: x.get('quality_score', 0), reverse=True
        )

        # Step 3: Apply semantic deduplication
        deduplicated = semantic_deduplication(
            results_sorted, self.similarity_threshold
        )

        # Step 4: Enforce domain diversity
        final_results = enforce_domain_diversity(
            deduplicated, self.max_per_domain
        )

        logger.info(
            f"Smart deduplication complete: "
            f"{len(results)} → {len(final_results)} results"
        )

        return final_results


def compare_deduplication_methods(
    results: List[Dict[str, Any]], num_results: int
) -> Dict[str, Any]:
    """Compare old vs new deduplication methods side by side."""
    from ..utils.deduplication import deduplicate_results

    # Original method (current implementation)
    old_results = deduplicate_results(results.copy(), num_results)

    # New smart method
    smart_dedup = SmartDeduplicator()
    new_results = smart_dedup.process_results(results.copy())[:num_results]

    # Analyze both
    old_analysis = analyze_results(old_results)
    new_analysis = analyze_results(new_results)

    # Calculate improvements
    domain_improvement = (
        new_analysis['unique_domains'] - old_analysis['unique_domains']
    )
    snippet_improvement = (
        new_analysis['avg_snippet_length'] - old_analysis['avg_snippet_length']
    )

    return {
        'old_method': old_analysis,
        'new_method': new_analysis,
        'improvements': {
            'domain_diversity_gain': domain_improvement,
            'avg_snippet_length_gain': snippet_improvement,
            'percentage_domain_improvement': (
                (domain_improvement / old_analysis['unique_domains'] * 100)
                if old_analysis['unique_domains'] > 0 else 0
            )
        }
    }


# Feature flag configuration
def is_smart_deduplication_enabled() -> bool:
    """Check if smart deduplication is enabled via environment variable."""
    return os.getenv('ENABLE_SMART_DEDUPLICATION', 'false').lower() == 'true'


def is_comparison_mode_enabled() -> bool:
    """Check if comparison mode is enabled for A/B testing."""
    return os.getenv('DEDUPLICATION_COMPARISON_MODE', 'false').lower() == 'true'
