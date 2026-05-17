#!/usr/bin/env python3
"""Benchmark content-extraction quality and latency.

Strategy:
  1. Fetch a fixed corpus of representative URLs once (Wikipedia, news,
     docs, blogs). Save HTML to ``benchmarks/fixtures/`` so re-runs are
     reproducible without network.
  2. For each extractor, measure on each fixture:
       - wall_time_ms (median of 5 runs)
       - chars_out
       - words_out
       - boilerplate_ratio (presence of cookie/nav/footer words in output)
  3. Emit a side-by-side Markdown table to stdout and a JSON record so the
     PR description can include reproducible numbers.

Run:
    .venv/bin/python benchmarks/extractor_bench.py            # use cached fixtures
    .venv/bin/python benchmarks/extractor_bench.py --refetch  # re-download
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Dict, List

# Make src importable without installing
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)

# Curated corpus: news, encyclopedia, docs, blog, ecommerce-style.
# Keep small — we want representative, not comprehensive.
CORPUS: Dict[str, str] = {
    "wikipedia_python": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "wikipedia_quantum": "https://en.wikipedia.org/wiki/Quantum_computing",
    "python_docs_tutorial": "https://docs.python.org/3/tutorial/index.html",
    "mdn_javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "reddit_thread": "https://www.reddit.com/r/Python/comments/1bz5emi/python_312_release_notes/",
    "github_readme": "https://github.com/vishalkg/web-search",
    "blog_post": "https://lilianweng.github.io/posts/2023-06-23-agent/",
    "news_article": "https://www.bbc.com/news/technology",
}

# Words/phrases that almost always come from boilerplate (nav, cookie banners,
# footer, share widgets). Used as a heuristic boilerplate-leakage measure —
# the cleaner the extractor, the lower this ratio.
BOILERPLATE_MARKERS = [
    "cookie",
    "subscribe",
    "newsletter",
    "sign in",
    "log in",
    "privacy policy",
    "terms of service",
    "all rights reserved",
    "skip to content",
    "follow us",
    "share this",
    "table of contents",
    "navigation menu",
    "search this site",
]


@dataclass
class ExtractorResult:
    extractor: str
    fixture: str
    wall_time_ms: float
    chars_out: int
    words_out: int
    boilerplate_hits: int


def fetch_fixtures(urls: Dict[str, str], force: bool) -> Dict[str, str]:
    """Download or load HTML fixtures. Returns name -> raw_html."""
    out: Dict[str, str] = {}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    for name, url in urls.items():
        path = FIXTURES / f"{name}.html"
        if path.exists() and not force:
            out[name] = path.read_text(encoding="utf-8", errors="replace")
            continue
        print(f"  fetching {name}: {url}", file=sys.stderr)
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            html = resp.text
            path.write_text(html, encoding="utf-8")
            out[name] = html
        except Exception as exc:  # noqa: BLE001
            print(f"    SKIP {name}: {exc}", file=sys.stderr)
    return out


def measure(extractor_fn: Callable[[str], str], html: str, runs: int = 5) -> float:
    """Median wall time across N runs (ms)."""
    timings: List[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        extractor_fn(html)
        timings.append((time.perf_counter() - t0) * 1000)
    return statistics.median(timings)


def boilerplate_score(text: str) -> int:
    lower = text.lower()
    return sum(lower.count(m) for m in BOILERPLATE_MARKERS)


def run_extractor(
    name: str, fn: Callable[[str], str], fixtures: Dict[str, str]
) -> List[ExtractorResult]:
    results: List[ExtractorResult] = []
    for fixture_name, html in fixtures.items():
        try:
            wall_ms = measure(fn, html)
            output = fn(html) or ""
        except Exception as exc:  # noqa: BLE001
            print(f"  {name} crashed on {fixture_name}: {exc}", file=sys.stderr)
            continue
        results.append(
            ExtractorResult(
                extractor=name,
                fixture=fixture_name,
                wall_time_ms=round(wall_ms, 2),
                chars_out=len(output),
                words_out=len(output.split()),
                boilerplate_hits=boilerplate_score(output),
            )
        )
    return results


def make_extractors() -> Dict[str, Callable[[str], str]]:
    """Return name -> extractor callable.

    Three candidates:
      - ``bs4_old``: the pre-PR pure-BeautifulSoup extractor (kept inline).
      - ``trafilatura_only``: Trafilatura without any fallback.
      - ``current``: whatever ``websearch.utils.content.extract_text_content``
        is on this branch — the actual production code path.
    """
    extractors: Dict[str, Callable[[str], str]] = {}

    # Pre-PR baseline: pure BeautifulSoup get_text — kept inline so the
    # benchmark stays comparable even after the production code is replaced.
    def _bs4_old(html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for s in soup(["script", "style"]):
            s.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return " ".join(chunk for chunk in chunks if chunk)

    extractors["bs4_old"] = _bs4_old

    try:
        import trafilatura  # noqa: WPS433

        def _trafilatura(html: str) -> str:
            return trafilatura.extract(html, include_comments=False) or ""

        extractors["trafilatura_only"] = _trafilatura
    except ImportError:
        print("  (trafilatura not installed; skipping)", file=sys.stderr)

    from websearch.utils.content import extract_text_content as _current

    extractors["current"] = _current

    return extractors


def render_table(results: List[ExtractorResult]) -> str:
    """Markdown table with one row per (extractor, fixture)."""
    by_fixture: Dict[str, Dict[str, ExtractorResult]] = {}
    for r in results:
        by_fixture.setdefault(r.fixture, {})[r.extractor] = r

    lines = []
    lines.append("| fixture | extractor | wall_ms | chars | words | boilerplate_hits |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for fixture, by_ext in sorted(by_fixture.items()):
        for ext_name, r in sorted(by_ext.items()):
            lines.append(
                f"| {fixture} | {ext_name} | {r.wall_time_ms} | {r.chars_out} | "
                f"{r.words_out} | {r.boilerplate_hits} |"
            )
    return "\n".join(lines)


def render_summary(results: List[ExtractorResult]) -> str:
    """Aggregate per-extractor totals."""
    by_ext: Dict[str, List[ExtractorResult]] = {}
    for r in results:
        by_ext.setdefault(r.extractor, []).append(r)

    lines = ["", "**Aggregate (sum across all fixtures):**", ""]
    lines.append("| extractor | total_chars | total_words | total_ms | total_boilerplate |")
    lines.append("|---|---:|---:|---:|---:|")
    for ext, rs in sorted(by_ext.items()):
        lines.append(
            f"| {ext} | {sum(r.chars_out for r in rs)} | {sum(r.words_out for r in rs)} | "
            f"{round(sum(r.wall_time_ms for r in rs), 2)} | "
            f"{sum(r.boilerplate_hits for r in rs)} |"
        )
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--refetch", action="store_true", help="Re-download HTML fixtures")
    p.add_argument("--json", help="Write raw results as JSON to this path")
    args = p.parse_args()

    print("Loading fixtures...", file=sys.stderr)
    fixtures = fetch_fixtures(CORPUS, force=args.refetch)
    if not fixtures:
        print("No fixtures available — run with --refetch first.", file=sys.stderr)
        return 1
    print(f"  {len(fixtures)} fixtures loaded", file=sys.stderr)

    extractors = make_extractors()
    print(f"  extractors: {sorted(extractors)}", file=sys.stderr)

    all_results: List[ExtractorResult] = []
    for name, fn in extractors.items():
        print(f"Running {name}...", file=sys.stderr)
        all_results.extend(run_extractor(name, fn, fixtures))

    print(render_table(all_results))
    print(render_summary(all_results))

    if args.json:
        Path(args.json).write_text(
            json.dumps([asdict(r) for r in all_results], indent=2)
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
