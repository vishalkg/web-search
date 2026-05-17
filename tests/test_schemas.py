"""Tests for Pydantic schemas and the legacy-dict adapter."""

import pytest
from pydantic import ValidationError

from websearch.schemas import (BatchPageContent, PageContentError,
                               PageContentSuccess, QuotaStatus, SearchResponse,
                               ToolValidationError, page_content_from_dict)


def test_page_content_success_round_trip():
    d = {
        "url": "https://example.com",
        "success": True,
        "content": "hello",
        "content_length": 5,
        "truncated": False,
        "cached": False,
        "error": None,
    }
    out = page_content_from_dict(d)
    assert isinstance(out, PageContentSuccess)
    assert out.content == "hello"


def test_page_content_error_preserves_troubleshooting():
    """Regression guard: troubleshooting must NOT be silently dropped."""
    d = {
        "url": "https://example.com",
        "success": False,
        "error": "timed out",
        "error_type": "timeout",
        "troubleshooting": "Try again later or check the URL.",
        "cached": False,
    }
    out = page_content_from_dict(d)
    assert isinstance(out, PageContentError)
    assert out.troubleshooting == "Try again later or check the URL."
    # Round-trips through model_dump
    dumped = out.model_dump()
    assert dumped["troubleshooting"] == "Try again later or check the URL."


def test_page_content_error_missing_troubleshooting_is_none():
    d = {
        "url": "https://example.com",
        "success": False,
        "error": "boom",
        "error_type": "general",
        "cached": False,
    }
    out = page_content_from_dict(d)
    assert isinstance(out, PageContentError)
    assert out.troubleshooting is None


def test_page_content_error_unknown_type_maps_to_general():
    d = {
        "url": "https://example.com",
        "success": False,
        "error": "weird",
        "error_type": "oauth_failed",  # not in the literal union
    }
    out = page_content_from_dict(d)
    assert isinstance(out, PageContentError)
    assert out.error_type == "general"


def test_page_content_malformed_success_coerces_to_error():
    """A success=True dict missing required fields must NOT raise — should
    convert to a typed PageContentError instead."""
    d = {"url": "https://example.com", "success": True}  # missing content/length
    out = page_content_from_dict(d)
    assert isinstance(out, PageContentError)
    assert out.error_type == "parse"
    assert "Malformed success payload" in out.error


def test_page_content_error_extra_allow_via_direct_validate():
    """When validated directly, extra='allow' preserves unknown fields.
    page_content_from_dict goes through explicit kwargs so it does not preserve
    extras — that's intentional, the adapter only knows the documented shape."""
    extra = PageContentError.model_validate(
        {
            "url": "https://example.com",
            "success": False,
            "error": "x",
            "error_type": "general",
            "future_field": "whatever",
        }
    )
    assert extra.model_dump().get("future_field") == "whatever"


def test_search_response_validation():
    SearchResponse.model_validate(
        {
            "query": "q",
            "total_results": 0,
            "sources": {},
            "engine_distribution": {},
            "results": [],
            "cached": False,
        }
    )
    with pytest.raises(ValidationError):
        SearchResponse.model_validate({"query": "q"})  # missing required


def test_batch_page_content_validation():
    BatchPageContent.model_validate(
        {
            "batch_request": True,
            "total_urls": 1,
            "successful_fetches": 1,
            "failed_fetches": 0,
            "results": [
                {
                    "url": "https://example.com",
                    "success": True,
                    "content": "x",
                    "content_length": 1,
                    "truncated": False,
                    "cached": False,
                }
            ],
        }
    )


def test_tool_validation_error_shape():
    err = ToolValidationError(error="bad input")
    assert err.success is False
    assert err.error_type == "validation"
