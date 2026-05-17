"""Query-relevance and freshness signals for result ranking.

Both functions are deliberately cheap: they run once per candidate result
during ranking, so a 10-result query traverses these on the order of 50
times. No regex compilation per call, no NLP libraries.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

# Words that show up in every search result and shouldn't count toward overlap.
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "have", "he", "her", "his", "how", "i", "in", "is", "it",
        "its", "of", "on", "or", "she", "that", "the", "their", "they",
        "this", "to", "was", "were", "what", "when", "where", "which",
        "who", "why", "will", "with", "you", "your",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> Set[str]:
    """Lowercase alphanumeric tokens with stopwords removed."""
    if not text:
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def query_overlap(query: str, *fields: str) -> float:
    """Fraction of query tokens that appear across the candidate fields.

    Returns 0.0–1.0. Stopwords are removed before counting. Empty queries
    return 0.0 (no signal).
    """
    q_tokens = _tokens(query)
    if not q_tokens:
        return 0.0

    candidate_tokens: Set[str] = set()
    for field in fields:
        candidate_tokens |= _tokens(field)

    if not candidate_tokens:
        return 0.0

    matches = q_tokens & candidate_tokens
    return len(matches) / len(q_tokens)


# Date patterns ordered most-specific first so we never partial-match a
# longer pattern.
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_DATE_PATTERNS = [
    # "Jan 22, 2026" / "January 22, 2026"
    re.compile(
        r"\b(?P<month>" + "|".join(_MONTHS) + r")\s+"
        r"(?P<day>\d{1,2}),?\s+(?P<year>(?:19|20|21)\d{2})\b",
        re.IGNORECASE,
    ),
    # "22 Jan 2026"
    re.compile(
        r"\b(?P<day>\d{1,2})\s+(?P<month>" + "|".join(_MONTHS) + r")\s+"
        r"(?P<year>(?:19|20|21)\d{2})\b",
        re.IGNORECASE,
    ),
    # "2026-05-17" / "2026/05/17"
    re.compile(
        r"\b(?P<year>(?:19|20|21)\d{2})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})\b"
    ),
]

# Explicit "N units ago" — unambiguous, e.g. "3 days ago", "2 weeks ago"
_RELATIVE_RE = re.compile(
    r"\b(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago\b",
    re.IGNORECASE,
)

# "a/an UNIT ago" — unambiguous indefinite-article form.
_INDEFINITE_RE = re.compile(
    r"\b(?:an?)\s+(hour|day|week|month|year)\s+ago\b",
    re.IGNORECASE,
)

_INDEFINITE_DELTAS = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}

# We deliberately do NOT match bare "today", "yesterday", "last week" etc:
# substring false positives ("Today Show", "Last Week Tonight", "last year,
# the company...") would systematically inflate freshness for unrelated text.
# Search-engine snippets that want to convey recency reliably use either an
# explicit date or "N units ago" — both of which we handle.


def parse_snippet_date(
    text: str, *, now: Optional[datetime] = None
) -> Optional[datetime]:
    """Extract the most recent plausible date from snippet/title text.

    Returns a UTC-aware datetime or None when nothing parseable is found.
    When the text contains multiple candidate dates (e.g. a reference to an
    older event plus a publication date), returns the most recent one — the
    publication date is almost always the latest, and freshness signals
    should reflect it.
    """
    if not text:
        return None
    now = now or datetime.now(timezone.utc)

    candidates: list = []

    # "Month DD, YYYY" and "DD Month YYYY"
    for pattern in _DATE_PATTERNS[:2]:
        for m in pattern.finditer(text):
            try:
                year = int(m.group("year"))
                day = int(m.group("day"))
                month = _MONTHS[m.group("month").lower()]
                if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= now.year + 1:
                    candidates.append(datetime(year, month, day, tzinfo=timezone.utc))
            except (KeyError, ValueError):
                continue

    # ISO-ish "YYYY-MM-DD"
    for m in _DATE_PATTERNS[2].finditer(text):
        try:
            year = int(m.group("year"))
            month = int(m.group("m"))
            day = int(m.group("d"))
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= now.year + 1:
                candidates.append(datetime(year, month, day, tzinfo=timezone.utc))
        except ValueError:
            continue

    if candidates:
        return max(candidates)

    # "a/an UNIT ago" before generic "N UNIT ago" because both can match in
    # principle (different patterns)
    m = _INDEFINITE_RE.search(text)
    if m:
        return now - _INDEFINITE_DELTAS[m.group(1).lower()]

    # "N units ago"
    m = _RELATIVE_RE.search(text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        deltas = {
            "second": timedelta(seconds=amount),
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
            "week": timedelta(weeks=amount),
            "month": timedelta(days=30 * amount),
            "year": timedelta(days=365 * amount),
        }
        return now - deltas[unit]

    return None


def freshness_score(
    text: str, *, now: Optional[datetime] = None, half_life_days: float = 365.0
) -> float:
    """Return 0.0–1.0 freshness score derived from any date in ``text``.

    Decay is exponential with the supplied half-life. Returns 0.0 when no
    date can be parsed (no signal — neither boost nor penalty). Returns 1.0
    for "today" content.
    """
    parsed = parse_snippet_date(text, now=now)
    if parsed is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    age_days = max(0.0, (now - parsed).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life_days)
