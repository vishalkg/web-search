"""Pydantic models for MCP tool responses.

FastMCP 3 supports Pydantic return types directly: the model schema is
advertised to the client (so the LLM gets a typed contract) and the
runtime payload is auto-serialized. Discriminated unions on `error_type`
let agents distinguish recoverable from terminal failures.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


def _utc_now_z() -> str:
    """ISO timestamp normalized to a trailing 'Z' for JSON consumers."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------- search_web response ----------


class SearchResultItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    url: str
    snippet: str
    source: str = Field(
        description="Engine that produced this result (lowercase: duckduckgo,"
        " bing, startpage, google, brave)."
    )
    quality_score: Optional[float] = None
    rank: Optional[int] = None


class SearchResponse(BaseModel):
    """Successful search_web result."""

    query: str
    total_results: int
    sources: dict
    engine_distribution: dict
    results: List[SearchResultItem]
    cached: bool


# ---------- fetch_page_content responses ----------


class PageContentSuccess(BaseModel):
    success: Literal[True] = True
    url: str
    content: str
    content_length: int
    truncated: bool
    cached: bool
    timestamp: str = Field(default_factory=_utc_now_z)
    error: None = None


class PageContentError(BaseModel):
    """Per-URL failure. error_type lets agents pick a retry strategy."""

    model_config = ConfigDict(extra="allow")

    success: Literal[False] = False
    url: str
    error: str
    error_type: Literal[
        "timeout",
        "connection",
        "http_4xx",
        "http_5xx",
        "redirect",
        "too_large",
        "validation",
        "parse",
        "general",
    ]
    troubleshooting: Optional[str] = None
    cached: bool = False
    timestamp: str = Field(default_factory=_utc_now_z)


PageContent = Union[PageContentSuccess, PageContentError]


class BatchPageContent(BaseModel):
    batch_request: Literal[True] = True
    total_urls: int
    successful_fetches: int
    failed_fetches: int
    timestamp: str = Field(default_factory=_utc_now_z)
    results: List[PageContent]


# ---------- get_quota_status response ----------


class ServiceQuota(BaseModel):
    used: int
    limit: int
    period: Literal["daily", "monthly", "unknown"]
    percentage_used: float
    remaining: int
    status: Literal["available", "exhausted"]


class QuotaStatus(BaseModel):
    timestamp: str = Field(default_factory=_utc_now_z)
    services: dict


# ---------- top-level error wrapper ----------


class ToolValidationError(BaseModel):
    """Returned when tool input fails validation before any work runs."""

    success: Literal[False] = False
    error: str
    error_type: Literal["validation"] = "validation"
    received: Optional[int] = None


_VALID_ERROR_TYPES = frozenset(
    {
        "timeout",
        "connection",
        "http_4xx",
        "http_5xx",
        "redirect",
        "too_large",
        "validation",
        "parse",
        "general",
    }
)


def page_content_from_dict(d: dict) -> PageContent:
    """Convert a legacy dict produced by core/content.py into the typed union.

    Robust against malformed legacy dicts: missing fields on a `success: True`
    payload are coerced into a typed `PageContentError(error_type="parse")`
    rather than raising, so the tool always returns a valid PageContent.
    """
    if d.get("success"):
        try:
            return PageContentSuccess.model_validate(d)
        except Exception as e:  # noqa: BLE001 — explicit fallback to typed error
            return PageContentError(
                url=d.get("url", ""),
                error=f"Malformed success payload: {e}",
                error_type="parse",
                cached=d.get("cached", False),
            )

    et = d.get("error_type", "general")
    if et not in _VALID_ERROR_TYPES:
        et = "general"
    return PageContentError(
        url=d.get("url", ""),
        error=d.get("error", "Unknown error"),
        error_type=et,
        troubleshooting=d.get("troubleshooting"),
        cached=d.get("cached", False),
        timestamp=d.get("timestamp", _utc_now_z()),
    )
