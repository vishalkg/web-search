#!/usr/bin/env python3
"""
Enhanced schema validation for web-search MCP tool
Based on 2025 MCP best practices research
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Union, Optional
from enum import Enum

class SearchEngine(str, Enum):
    """Supported search engines"""
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"
    STARTPAGE = "startpage"
    ALL = "all"

class SearchWebInput(BaseModel):
    """Schema for search_web tool input"""
    search_query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string (1-500 characters)",
        example="quantum computing applications"
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of results to return (1-20)",
        example=10
    )
    
    @validator('search_query')
    def validate_search_query(cls, v):
        if not v.strip():
            raise ValueError('Search query cannot be empty or whitespace only')
        return v.strip()

class FetchPageContentInput(BaseModel):
    """Schema for fetch_page_content tool input"""
    urls: Union[HttpUrl, List[HttpUrl]] = Field(
        ...,
        description="Single URL or list of URLs to fetch content from",
        example=["https://example.com", "https://docs.python.org"]
    )
    timeout: Optional[int] = Field(
        default=20,
        ge=5,
        le=60,
        description="Request timeout in seconds (5-60)",
        example=20
    )
