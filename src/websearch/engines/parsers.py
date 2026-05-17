"""Search result parsers for different engines.

Each parser tries the engine's stable CSS class selector first, then falls
back to a tag-based heuristic if the class selector finds nothing. The
fallback exists because search engines change their HTML layout every few
months — without it, an unannounced DOM change would silently return zero
results from that engine until someone noticed in production.

A `parser_failure` log line is emitted whenever the primary selector finds
nothing, so dashboards can alert on rising failure rates.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, cast

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def _log_parser_failure(
    engine: str, primary_selector: str, fallback_used: bool
) -> None:
    """Emit a structured warning when an engine's primary selector misses."""
    logger.warning(
        "parser_failure engine=%s primary_selector=%s fallback_used=%s",
        engine,
        primary_selector,
        fallback_used,
    )


def _extract_text(tag: Optional[Tag]) -> Optional[str]:
    if tag is None or not isinstance(tag, Tag):
        return None
    text = tag.get_text(strip=True)
    return text or None


def _extract_href(tag: Optional[Tag]) -> Optional[str]:
    if tag is None or not isinstance(tag, Tag):
        return None
    href = tag.get("href")
    if not href:
        return None
    href = href if isinstance(href, str) else (href[0] if href else None)
    if not href or not href.startswith(("http://", "https://")):
        return None
    return href


def _build_result(
    title: Optional[str],
    url: Optional[str],
    snippet: Optional[str],
    source: str,
    rank: int,
) -> Optional[Dict[str, Any]]:
    if not title or not url:
        return None
    return {
        "title": title,
        "url": url,
        "snippet": snippet or "No description",
        "source": source,
        "rank": rank,
    }


# Engine domains we filter from fallback results so site nav links to the
# engine's own pages don't pollute the result list.
_ENGINE_DOMAINS = {
    "duckduckgo": ("duckduckgo.com",),
    "bing": ("bing.com", "microsoft.com"),
    "startpage": ("startpage.com",),
}

# Tags that indicate non-result content; <h2>s inside these are skipped.
_NAV_ANCESTOR_TAGS = frozenset({"nav", "header", "footer", "aside"})


def _is_under_nav_ancestor(tag: Tag) -> bool:
    parent = tag.parent
    while parent is not None and isinstance(parent, Tag):
        if parent.name in _NAV_ANCESTOR_TAGS:
            return True
        parent = parent.parent
    return False


def _matches_engine_domain(url: str, source: str) -> bool:
    domains = _ENGINE_DOMAINS.get(source, ())
    if not domains:
        return False
    lowered = url.lower()
    return any(d in lowered for d in domains)


def _generic_tag_fallback(
    soup: BeautifulSoup, num_results: int, source: str
) -> List[Dict[str, Any]]:
    """Tag-based extraction used when an engine's class selector breaks.

    Strategy: walk every `<h2><a href=...>` (the universally stable shape of
    a search result heading) and pair it with the nearest sibling `<p>` for
    the snippet. Filters out:
      - <h2>s nested inside <nav>/<header>/<footer>/<aside> (site chrome)
      - links pointing back at the engine's own domain (related searches,
        category links, etc.)
    Deliberately conservative — preferring an empty result over polluted
    nav/footer entries that would mislead the LLM downstream.
    """
    results: List[Dict[str, Any]] = []
    for heading in soup.find_all("h2"):
        if len(results) >= num_results:
            break
        if not isinstance(heading, Tag):
            continue
        if _is_under_nav_ancestor(heading):
            continue
        link = heading.find("a")
        title = _extract_text(cast(Optional[Tag], link))
        url = _extract_href(cast(Optional[Tag], link))
        if not title or not url:
            continue
        if _matches_engine_domain(url, source):
            continue
        # Look for snippet in following siblings, then in the parent's <p>
        snippet_tag: Optional[Tag] = None
        sib = heading.find_next_sibling("p")
        if sib and isinstance(sib, Tag):
            snippet_tag = sib
        elif heading.parent is not None:
            parent_p = heading.parent.find("p")
            if parent_p and isinstance(parent_p, Tag):
                snippet_tag = parent_p
        snippet = _extract_text(snippet_tag)

        result = _build_result(title, url, snippet, source, len(results) + 1)
        if result:
            results.append(result)
    return results


def _class_based_parse(
    soup: BeautifulSoup,
    num_results: int,
    container_selector: Dict[str, Any],
    title_selector: Dict[str, Any],
    snippet_selector: Dict[str, Any],
    source: str,
    extract_url_from_title: bool = True,
) -> List[Dict[str, Any]]:
    """Generic class-based extractor parameterized per-engine."""
    results: List[Dict[str, Any]] = []
    for container in soup.find_all(**container_selector)[:num_results]:
        if not isinstance(container, Tag):
            continue

        title_elem = container.find(**title_selector)
        if extract_url_from_title:
            title = _extract_text(cast(Optional[Tag], title_elem))
            url = _extract_href(cast(Optional[Tag], title_elem))
        else:
            # Bing nests <a> inside <h2>
            title, url = None, None
            if title_elem and isinstance(title_elem, Tag):
                inner = title_elem.find("a")
                title = _extract_text(cast(Optional[Tag], inner))
                url = _extract_href(cast(Optional[Tag], inner))

        snippet_elem = container.find(**snippet_selector)
        snippet = _extract_text(cast(Optional[Tag], snippet_elem))

        result = _build_result(title, url, snippet, source, len(results) + 1)
        if result:
            results.append(result)
    return results


def _parse_with_fallback(
    soup: BeautifulSoup,
    num_results: int,
    primary: Callable[[], List[Dict[str, Any]]],
    primary_selector: str,
    source: str,
) -> List[Dict[str, Any]]:
    results = primary()
    if results:
        return results

    _log_parser_failure(source, primary_selector, fallback_used=True)
    return _generic_tag_fallback(soup, num_results, source)


def parse_startpage_results(
    soup: BeautifulSoup, num_results: int
) -> List[Dict[str, Any]]:
    """Parse Startpage search results (class-based with tag fallback)."""
    return _parse_with_fallback(
        soup,
        num_results,
        primary=lambda: _class_based_parse(
            soup,
            num_results,
            container_selector={"name": "div", "class_": "result"},
            title_selector={"name": "a", "class_": "result-link"},
            snippet_selector={"name": "p", "class_": "description"},
            source="startpage",
        ),
        primary_selector="div.result > a.result-link",
        source="startpage",
    )


def parse_duckduckgo_results(
    soup: BeautifulSoup, num_results: int
) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo search results (class-based with tag fallback)."""
    return _parse_with_fallback(
        soup,
        num_results,
        primary=lambda: _class_based_parse(
            soup,
            num_results,
            container_selector={"name": "div", "class_": "result"},
            title_selector={"name": "a", "class_": "result__a"},
            snippet_selector={"name": "a", "class_": "result__snippet"},
            source="duckduckgo",
        ),
        primary_selector="div.result > a.result__a",
        source="duckduckgo",
    )


def parse_bing_results(soup: BeautifulSoup, num_results: int) -> List[Dict[str, Any]]:
    """Parse Bing search results (class-based with tag fallback)."""
    return _parse_with_fallback(
        soup,
        num_results,
        primary=lambda: _class_based_parse(
            soup,
            num_results,
            container_selector={"name": "li", "class_": "b_algo"},
            title_selector={"name": "h2"},
            snippet_selector={"name": "p"},
            source="bing",
            extract_url_from_title=False,
        ),
        primary_selector="li.b_algo > h2 > a",
        source="bing",
    )
