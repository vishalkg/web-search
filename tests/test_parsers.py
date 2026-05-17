"""Tests for HTML parsers — feed canned HTML and verify shape of output."""

import pytest
from bs4 import BeautifulSoup

from websearch.engines.parsers import (parse_bing_results,
                                       parse_duckduckgo_results,
                                       parse_startpage_results)

DDG_HTML = """
<html><body>
  <div class="result">
    <a class="result__a" href="https://a.example/">A title</a>
    <a class="result__snippet">A snippet text</a>
  </div>
  <div class="result">
    <a class="result__a" href="https://b.example/">B title</a>
    <a class="result__snippet">B snippet text</a>
  </div>
</body></html>
"""

BING_HTML = """
<html><body>
  <li class="b_algo">
    <h2><a href="https://x.example/">X title</a></h2>
    <p>X snippet</p>
  </li>
  <li class="b_algo">
    <h2><a href="https://y.example/">Y title</a></h2>
    <p>Y snippet</p>
  </li>
</body></html>
"""

STARTPAGE_HTML = """
<html><body>
  <div class="result">
    <a class="result-link" href="https://m.example/">M title</a>
    <p class="description">M snippet</p>
  </div>
</body></html>
"""


def test_parse_duckduckgo_results():
    soup = BeautifulSoup(DDG_HTML, "lxml")
    results = parse_duckduckgo_results(soup, num_results=10)
    assert len(results) == 2
    assert results[0]["title"] == "A title"
    assert results[0]["url"] == "https://a.example/"
    assert results[0]["snippet"] == "A snippet text"
    assert results[0]["source"] == "duckduckgo"
    assert results[0]["rank"] == 1


def test_parse_duckduckgo_respects_limit():
    soup = BeautifulSoup(DDG_HTML, "lxml")
    assert len(parse_duckduckgo_results(soup, num_results=1)) == 1


def test_parse_bing_results():
    soup = BeautifulSoup(BING_HTML, "lxml")
    results = parse_bing_results(soup, num_results=10)
    assert len(results) == 2
    assert results[0]["title"] == "X title"
    assert results[0]["source"] == "bing"


def test_parse_startpage_results():
    soup = BeautifulSoup(STARTPAGE_HTML, "lxml")
    results = parse_startpage_results(soup, num_results=10)
    assert len(results) == 1
    assert results[0]["url"] == "https://m.example/"
    assert results[0]["source"] == "startpage"


def test_parsers_return_empty_on_unrelated_html():
    soup = BeautifulSoup("<html><body><p>nothing</p></body></html>", "lxml")
    assert parse_duckduckgo_results(soup, 5) == []
    assert parse_bing_results(soup, 5) == []
    assert parse_startpage_results(soup, 5) == []


@pytest.mark.parametrize(
    "html",
    [
        # Missing href on the title link — should skip
        '<div class="result"><a class="result__a">No href</a></div>',
    ],
)
def test_parse_skips_malformed_entries(html):
    soup = BeautifulSoup(f"<html><body>{html}</body></html>", "lxml")
    assert parse_duckduckgo_results(soup, 5) == []


# Tag-based fallback: engine-style classes are gone, only h2 > a structure
DDG_NO_CLASSES_HTML = """
<html><body>
  <article>
    <h2><a href="https://fallback-a.example/">Fallback A</a></h2>
    <p>Fallback A snippet</p>
  </article>
  <article>
    <h2><a href="https://fallback-b.example/">Fallback B</a></h2>
    <p>Fallback B snippet</p>
  </article>
</body></html>
"""


def test_fallback_used_when_class_selector_misses(caplog):
    """If the primary class selector fails, tag-based fallback runs."""
    soup = BeautifulSoup(DDG_NO_CLASSES_HTML, "lxml")
    with caplog.at_level("WARNING"):
        results = parse_duckduckgo_results(soup, num_results=5)

    assert len(results) == 2
    assert results[0]["url"] == "https://fallback-a.example/"
    assert results[0]["title"] == "Fallback A"
    assert results[0]["source"] == "duckduckgo"
    assert results[0]["rank"] == 1
    # Structured failure log was emitted
    assert any(
        "parser_failure" in rec.getMessage() and "duckduckgo" in rec.getMessage()
        for rec in caplog.records
    )


def test_fallback_does_not_run_when_class_selector_succeeds(caplog):
    """Successful primary parse must NOT log parser_failure."""
    soup = BeautifulSoup(DDG_HTML, "lxml")
    with caplog.at_level("WARNING"):
        results = parse_duckduckgo_results(soup, num_results=5)
    assert len(results) == 2
    assert not any("parser_failure" in r.getMessage() for r in caplog.records)


def test_fallback_skips_relative_urls():
    """Tag fallback must reject non-http(s) and javascript: links."""
    html = """
    <html><body>
      <h2><a href="javascript:alert(1)">Bad</a></h2>
      <h2><a href="/relative">Relative</a></h2>
      <h2><a href="https://good.example/">Good</a></h2>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    results = parse_duckduckgo_results(soup, num_results=5)
    assert len(results) == 1
    assert results[0]["url"] == "https://good.example/"


def test_fallback_returns_empty_when_no_h2_present():
    soup = BeautifulSoup("<html><body><p>no h2 anywhere</p></body></html>", "lxml")
    assert parse_bing_results(soup, num_results=5) == []
    assert parse_duckduckgo_results(soup, num_results=5) == []
    assert parse_startpage_results(soup, num_results=5) == []


def test_fallback_rejects_nav_and_footer_h2s():
    """Site chrome (nav/header/footer/aside) must not pollute fallback results."""
    html = """
    <html><body>
      <header>
        <h2><a href="https://nav.example/">Navigation</a></h2>
      </header>
      <nav>
        <h2><a href="https://nav2.example/">Try our newest features</a></h2>
      </nav>
      <article>
        <h2><a href="https://real.example/">Real Result</a></h2>
        <p>real snippet</p>
      </article>
      <footer>
        <h2><a href="https://footer.example/">Footer link</a></h2>
      </footer>
      <aside>
        <h2><a href="https://aside.example/">Sidebar</a></h2>
      </aside>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    results = parse_duckduckgo_results(soup, num_results=10)
    assert len(results) == 1
    assert results[0]["url"] == "https://real.example/"


def test_fallback_rejects_links_to_engine_own_domain():
    """Self-links (related searches, category nav) shouldn't appear as results."""
    html = """
    <html><body>
      <article>
        <h2><a href="https://duckduckgo.com/?q=more+python">More results</a></h2>
        <p>related search</p>
      </article>
      <article>
        <h2><a href="https://wikipedia.org/Python">Python on Wikipedia</a></h2>
        <p>real result</p>
      </article>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    results = parse_duckduckgo_results(soup, num_results=10)
    urls = [r["url"] for r in results]
    assert "https://wikipedia.org/Python" in urls
    assert not any("duckduckgo.com" in u for u in urls)


def test_fallback_handles_h2_without_paragraph():
    """When no <p> sibling or parent <p> exists, snippet falls back gracefully."""
    html = """
    <html><body>
      <article>
        <h2><a href="https://only-heading.example/">Only heading</a></h2>
      </article>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    results = parse_duckduckgo_results(soup, num_results=5)
    assert len(results) == 1
    assert results[0]["snippet"] == "No description"
