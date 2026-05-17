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
