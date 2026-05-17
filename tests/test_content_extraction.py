"""Tests for utils.content.extract_text_content (Trafilatura + BS4 fallback)."""

import logging

import pytest

from websearch.utils import content as content_mod
from websearch.utils.content import extract_text_content

ARTICLE_HTML = """
<html><head><title>T</title></head>
<body>
  <nav>Site Nav | About | Contact</nav>
  <header>Cookie banner: please accept our cookies</header>
  <main>
    <article>
      <h1>The Article Title</h1>
      <p>This is the first paragraph of real article content. It is long enough
         that Trafilatura will treat it as the main body.</p>
      <p>Second paragraph continues the discussion with more substantive prose
         that any reasonable extractor should preserve in the output.</p>
    </article>
  </main>
  <aside>Sidebar: subscribe to newsletter, follow us on social media</aside>
  <footer>All rights reserved. Privacy Policy. Terms of Service.</footer>
</body></html>
"""

EMPTY_HTML = "<html><body></body></html>"
SHORT_HTML = "<html><body><p>too short</p></body></html>"


def test_extract_real_article_strips_chrome():
    out = extract_text_content(ARTICLE_HTML, url="https://example.com/article")
    assert "first paragraph of real article content" in out
    assert "Second paragraph continues" in out
    # Boilerplate must be gone
    assert "Cookie banner" not in out
    assert "newsletter" not in out
    assert "All rights reserved" not in out


def test_extract_falls_back_when_trafilatura_returns_empty(monkeypatch):
    """When Trafilatura yields '', the BS4 fallback runs."""
    if not content_mod._TRAFILATURA_AVAILABLE:
        pytest.skip("trafilatura not installed in this env")

    monkeypatch.setattr(
        content_mod.trafilatura, "extract", lambda *a, **kw: None
    )
    out = extract_text_content("<html><body><p>fallback content</p></body></html>")
    assert "fallback content" in out


def test_extract_falls_back_when_trafilatura_raises(monkeypatch):
    """Defensive: an exception in Trafilatura must not propagate."""
    if not content_mod._TRAFILATURA_AVAILABLE:
        pytest.skip("trafilatura not installed in this env")

    def _boom(*_a, **_kw):
        raise RuntimeError("trafilatura is sad")

    monkeypatch.setattr(content_mod.trafilatura, "extract", _boom)
    out = extract_text_content("<html><body><p>still works</p></body></html>")
    assert "still works" in out


def test_extract_handles_completely_empty_html():
    """Both extractors should return '' or near-empty without raising."""
    out = extract_text_content(EMPTY_HTML)
    assert out == "" or len(out.strip()) == 0


def test_extract_short_page_uses_fallback_or_returns_text():
    """Trafilatura might reject very short pages; fallback ensures we return
    *something* useful so the LLM sees it instead of empty content."""
    out = extract_text_content(SHORT_HTML)
    assert "too short" in out


def test_extract_passes_url_hint_to_trafilatura(monkeypatch):
    """The URL hint must be forwarded — Trafilatura uses it for heuristics."""
    if not content_mod._TRAFILATURA_AVAILABLE:
        pytest.skip("trafilatura not installed in this env")

    captured = {}

    def _spy(html, **kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(content_mod.trafilatura, "extract", _spy)
    extract_text_content("<html></html>", url="https://example.com/x")
    assert captured.get("url") == "https://example.com/x"


def test_extract_does_not_raise_on_invalid_html():
    """Garbage in must not raise."""
    out = extract_text_content("<<<not <html> at all>>>")
    assert isinstance(out, str)


def test_trafilatura_loggers_silenced(caplog):
    """Routine empty/garbage extractions must NOT emit WARNING/ERROR logs.

    Trafilatura and htmldate are noisy on malformed/empty inputs; we silence
    them at import time so the MCP server's log file stays clean.
    """
    if not content_mod._TRAFILATURA_AVAILABLE:
        pytest.skip("trafilatura not installed in this env")

    with caplog.at_level(logging.WARNING):
        # Each of these would emit warnings/errors on the trafilatura/htmldate
        # loggers if we hadn't silenced them.
        extract_text_content("")
        extract_text_content("<html></html>")
        extract_text_content("<<not html>>")

    noisy = [
        rec for rec in caplog.records
        if rec.name.startswith(("trafilatura", "htmldate"))
    ]
    assert noisy == [], f"Expected no trafilatura/htmldate logs, got: {noisy}"
