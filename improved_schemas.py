#!/usr/bin/env python3
"""
Improved schema validation for web-search MCP tool
Based on 2025 MCP best practices research
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Union, Optional, Literal
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
    engines: Optional[List[SearchEngine]] = Field(
        default=None,
        description="Specific search engines to use (default: all)",
        example=["duckduckgo", "bing"]
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
    max_content_length: Optional[int] = Field(
        default=8000,
        ge=1000,
        le=50000,
        description="Maximum content length to extract (1000-50000 chars)",
        example=8000
    )

class ToolMetadata(BaseModel):
    """Enhanced tool metadata following MCP 2025 best practices"""
    name: str
    title: str
    description: str
    version: str
    category: str
    tags: List[str]
    input_schema: dict
    output_schema: Optional[dict] = None
    annotations: dict
    examples: List[dict]
    error_codes: List[dict]
    
class WebSearchToolMetadata(ToolMetadata):
    """Metadata for web search tool"""
    name: str = "search_web"
    title: str = "Multi-Engine Web Search"
    description: str = """
    Search across multiple search engines (DuckDuckGo, Bing, Startpage) with intelligent 
    caching and parallel processing. Returns comprehensive results with titles, URLs, 
    and snippets from multiple sources.
    
    Use cases:
    • Research topics and find information
    • Discover websites and documentation  
    • Get current news and updates
    • Verify facts and cross-reference sources
    • Find tutorials and how-to guides
    """
    version: str = "2.1.0"
    category: str = "information_retrieval"
    tags: List[str] = ["search", "web", "research", "information", "multi-engine"]
    annotations: dict = {
        "title": "Multi-Engine Web Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "rateLimited": True,
        "requiresNetwork": True
    }
    examples: List[dict] = [
        {
            "description": "Basic search with default settings",
            "input": {"search_query": "machine learning tutorials", "num_results": 5},
            "expected_output_type": "search_results"
        },
        {
            "description": "Targeted search with specific engines",
            "input": {
                "search_query": "Python async programming", 
                "num_results": 8,
                "engines": ["duckduckgo", "bing"]
            },
            "expected_output_type": "search_results"
        }
    ]
    error_codes: List[dict] = [
        {"code": "INVALID_QUERY", "description": "Search query is empty or invalid"},
        {"code": "NETWORK_ERROR", "description": "Unable to reach search engines"},
        {"code": "RATE_LIMITED", "description": "Too many requests, please wait"},
        {"code": "TIMEOUT", "description": "Search request timed out"}
    ]

class FetchContentToolMetadata(ToolMetadata):
    """Metadata for content fetching tool"""
    name: str = "fetch_page_content"
    title: str = "Web Content Extractor"
    description: str = """
    Extract clean, readable text content from web pages with intelligent parsing
    and parallel processing. Supports single URLs or batch processing of multiple URLs.
    
    Features:
    • HTML-to-text conversion with formatting preservation
    • Intelligent content extraction (removes ads, navigation)
    • Parallel processing for multiple URLs
    • Caching for improved performance
    • Automatic retry with exponential backoff
    """
    version: str = "2.1.0"
    category: str = "content_extraction"
    tags: List[str] = ["content", "extraction", "web", "text", "parsing", "batch"]
    annotations: dict = {
        "title": "Web Content Extractor", 
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "batchCapable": True,
        "requiresNetwork": True
    }
    examples: List[dict] = [
        {
            "description": "Extract content from single URL",
            "input": {"urls": "https://en.wikipedia.org/wiki/Machine_learning"},
            "expected_output_type": "extracted_text"
        },
        {
            "description": "Batch extract from multiple URLs",
            "input": {
                "urls": [
                    "https://docs.python.org/3/tutorial/",
                    "https://docs.python.org/3/library/"
                ],
                "timeout": 30,
                "max_content_length": 10000
            },
            "expected_output_type": "batch_extraction_results"
        }
    ]
    error_codes: List[dict] = [
        {"code": "INVALID_URL", "description": "URL format is invalid"},
        {"code": "ACCESS_DENIED", "description": "Website blocks access or requires authentication"},
        {"code": "CONTENT_TOO_LARGE", "description": "Content exceeds maximum length limit"},
        {"code": "PARSING_ERROR", "description": "Unable to extract readable content"}
    ]
