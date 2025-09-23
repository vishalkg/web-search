"""URL tracking utilities for search engine selection metrics."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

# Engine code mapping
ENGINE_CODES = {"ddg": "d", "bing": "b", "startpage": "s"}


def log_search_response(search_query: str, results: List[Dict], search_id: str) -> None:
    """Log search response sent to LLM for comparison with selections"""
    metrics_file = os.path.join(os.path.dirname(__file__), "..", "search-metrics.jsonl")

    # Get engine distribution - include all 5 engines
    distribution = {
        "duckduckgo": 0, "bing": 0, "startpage": 0, 
        "google": 0, "brave": 0, "unknown": 0
    }
    for result in results:
        engine = result.get("source", "unknown")
        distribution[engine] = distribution.get(engine, 0) + 1

    response_data = {
        "event_type": "search_response",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "search_id": search_id,
        "query": search_query,
        "total_results": len(results),
        "engine_distribution": distribution,
        "results": [
            {
                "rank": i + 1,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "source": result.get("source", "unknown"),
                "quality_score": result.get("quality_score", 0)
            }
            for i, result in enumerate(results)
        ]
    }

    try:
        with open(metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(response_data) + "\n")
        logger.info(f"📤 Logged search response: {search_id} ({len(results)} results)")
    except Exception as e:
        logger.error(f"Failed to log search response: {e}")


def add_tracking_to_url(url: str, engine: str, search_id: str) -> str:
    """Add tracking parameters to URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Add tracking params
    params["_src"] = [ENGINE_CODES.get(engine, "u")]
    params["_sid"] = [search_id]

    # Rebuild URL
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def extract_tracking_from_url(url: str) -> Tuple[str, str, str]:
    """Extract tracking info and return clean URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Extract tracking
    source_code = params.pop("_src", ["u"])[0]
    search_id = params.pop("_sid", [""])[0]

    # Map code back to engine name
    engine_map = {v: k for k, v in ENGINE_CODES.items()}
    engine = engine_map.get(source_code, "unknown")

    # Clean URL
    clean_query = urlencode(params, doseq=True)
    clean_url = urlunparse(parsed._replace(query=clean_query))

    return engine, search_id, clean_url


def log_selection_metrics(urls: List[str]) -> None:
    """Log URL selection metrics to file."""
    if not urls:
        return

    metrics_file = os.path.join(os.path.dirname(__file__), "../search-metrics.jsonl")

    selections = []
    for url in urls:
        engine, search_id, clean_url = extract_tracking_from_url(url)
        selections.append(
            {
                "engine": engine,
                "search_id": search_id,
                "url": clean_url,
                "original_url": url,
            }
        )

    event = {
        "event_type": "url_selection",
        "timestamp": datetime.utcnow().isoformat(),
        "selections": selections,
        "total_selected": len(urls),
    }

    try:
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
        with open(metrics_file, "a") as f:
            f.write(json.dumps(event) + "\n")

        # Log summary
        engine_counts = {}
        for sel in selections:
            engine_counts[sel["engine"]] = engine_counts.get(sel["engine"], 0) + 1

        logger.info(f"Selection logged: {engine_counts}")

    except Exception as e:
        logger.error(f"Failed to log selection metrics: {e}")


def generate_search_id() -> str:
    """Generate unique search ID."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
