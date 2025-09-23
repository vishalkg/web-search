#!/usr/bin/env python3
"""Test script to compare old vs new deduplication methods."""

import os
import sys
import time
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from websearch.utils.smart_deduplication import compare_deduplication_methods


def create_test_results() -> list:
    """Create test results with known duplicates and domain flooding."""
    return [
        {
            'url': 'https://python.org/tutorial1',
            'title': 'Python Machine Learning Tutorial',
            'snippet': 'Learn machine learning with Python programming language. Comprehensive guide.',
            'quality_score': 8.0,
            'source': 'google'
        },
        {
            'url': 'https://python.org/tutorial2', 
            'title': 'Machine Learning Python Guide',
            'snippet': 'Python machine learning comprehensive tutorial and guide.',
            'quality_score': 7.5,
            'source': 'bing'
        },
        {
            'url': 'https://python.org/tutorial3',
            'title': 'Python ML Basics',
            'snippet': 'Basic machine learning concepts using Python.',
            'quality_score': 7.0,
            'source': 'duckduckgo'
        },
        {
            'url': 'https://medium.com/ml-guide',
            'title': 'Complete Machine Learning Guide',
            'snippet': 'Step-by-step machine learning tutorial with practical examples and code.',
            'quality_score': 8.5,
            'source': 'startpage'
        },
        {
            'url': 'https://towardsdatascience.com/ml-python',
            'title': 'Machine Learning with Python',
            'snippet': 'Advanced machine learning techniques using Python libraries.',
            'quality_score': 9.0,
            'source': 'brave'
        },
        {
            'url': 'https://kaggle.com/learn/ml',
            'title': 'Kaggle Machine Learning Course',
            'snippet': 'Free online machine learning course with hands-on exercises.',
            'quality_score': 8.8,
            'source': 'google'
        },
        {
            'url': 'https://coursera.org/ml-course',
            'title': 'Machine Learning Specialization',
            'snippet': 'University-level machine learning course with certificates.',
            'quality_score': 9.2,
            'source': 'bing'
        },
        {
            'url': 'https://udemy.com/python-ml',
            'title': 'Python for Machine Learning',
            'snippet': 'Complete Python machine learning bootcamp course.',
            'quality_score': 7.8,
            'source': 'duckduckgo'
        }
    ]


def print_comparison_results(comparison: Dict[str, Any]) -> None:
    """Print formatted comparison results."""
    print("🔍 DEDUPLICATION COMPARISON RESULTS")
    print("=" * 50)
    
    old = comparison['old_method']
    new = comparison['new_method']
    improvements = comparison['improvements']
    
    print(f"\n📊 OLD METHOD (Current):")
    print(f"  • Unique domains: {old['unique_domains']}")
    print(f"  • Total results: {old['total_results']}")
    print(f"  • Avg snippet length: {old['avg_snippet_length']:.1f}")
    print(f"  • Domains: {', '.join(old['domain_list'])}")
    
    print(f"\n🧠 NEW METHOD (Smart):")
    print(f"  • Unique domains: {new['unique_domains']}")
    print(f"  • Total results: {new['total_results']}")
    print(f"  • Avg snippet length: {new['avg_snippet_length']:.1f}")
    print(f"  • Domains: {', '.join(new['domain_list'])}")
    
    print(f"\n📈 IMPROVEMENTS:")
    print(f"  • Domain diversity gain: +{improvements['domain_diversity_gain']}")
    print(f"  • Snippet length gain: +{improvements['avg_snippet_length_gain']:.1f}")
    print(f"  • Domain improvement: {improvements['percentage_domain_improvement']:.1f}%")
    
    # Success indicators
    print(f"\n✅ SUCCESS INDICATORS:")
    if improvements['domain_diversity_gain'] > 0:
        print(f"  ✓ Better domain diversity (+{improvements['domain_diversity_gain']} domains)")
    else:
        print(f"  ⚠ No domain diversity improvement")
        
    if improvements['avg_snippet_length_gain'] > 0:
        print(f"  ✓ Richer content (+{improvements['avg_snippet_length_gain']:.1f} chars)")
    else:
        print(f"  ⚠ No content quality improvement")


def test_performance() -> None:
    """Test performance impact of smart deduplication."""
    print("\n⚡ PERFORMANCE TESTING")
    print("=" * 30)
    
    test_results = create_test_results()
    iterations = 100
    
    # Test old method performance
    start_time = time.time()
    for _ in range(iterations):
        from websearch.utils.deduplication import deduplicate_results
        deduplicate_results(test_results.copy(), 10)
    old_time = (time.time() - start_time) / iterations * 1000
    
    # Test new method performance  
    start_time = time.time()
    for _ in range(iterations):
        from websearch.utils.smart_deduplication import SmartDeduplicator
        dedup = SmartDeduplicator()
        dedup.process_results(test_results.copy())
    new_time = (time.time() - start_time) / iterations * 1000
    
    print(f"Old method: {old_time:.2f}ms per search")
    print(f"New method: {new_time:.2f}ms per search")
    print(f"Overhead: +{new_time - old_time:.2f}ms ({((new_time/old_time - 1) * 100):.1f}%)")
    
    if new_time - old_time < 10:
        print("✅ Performance impact acceptable (<10ms)")
    else:
        print("⚠ Performance impact high (>10ms)")


def main():
    """Run comparison tests."""
    print("🧪 SMART DEDUPLICATION TESTING")
    print("=" * 40)
    
    # Create test data
    test_results = create_test_results()
    print(f"📋 Test data: {len(test_results)} results with known duplicates and domain flooding")
    
    # Run comparison
    comparison = compare_deduplication_methods(test_results, 10)
    print_comparison_results(comparison)
    
    # Test performance
    test_performance()
    
    print(f"\n🎯 RECOMMENDATION:")
    improvements = comparison['improvements']
    if improvements['domain_diversity_gain'] > 0 or improvements['avg_snippet_length_gain'] > 0:
        print("✅ Smart deduplication shows improvements - ENABLE recommended")
    else:
        print("⚠ Smart deduplication shows no clear benefits - keep current method")


if __name__ == "__main__":
    main()
