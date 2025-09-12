"""Content processing utilities."""

from datetime import datetime, timezone
from typing import Any, Dict

from bs4 import BeautifulSoup


def extract_text_content(html: str) -> str:
    """Extract and clean text content from HTML"""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text content and clean whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)


def create_error_result(url: str, error_msg: str, error_type: str = "general") -> Dict[str, Any]:
    """Create standardized error result with error type classification"""
    return {
        "url": url,
        "success": False,
        "content": None,
        "content_length": 0,
        "truncated": False,
        "error": error_msg,
        "error_type": error_type,
        "troubleshooting": get_troubleshooting_tips(error_type),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cached": False,
    }


def get_troubleshooting_tips(error_type: str) -> str:
    """Return troubleshooting suggestions based on error type"""
    tips = {
        "timeout": "The website took too long to respond. Try again later or check if the URL is correct.",
        "connection": "Could not connect to the website. Check your internet connection or if the website is down.",
        "http_4xx": "Server returned a client error (4xx). The URL might be incorrect or you don't have permission to access it.",
        "http_5xx": "Server returned a server error (5xx). The website might be experiencing issues, try again later.",
        "parse": "Could not parse the website content. The site might use unsupported formatting or scripts.",
        "general": "An unexpected error occurred. Check the URL and try again later."
    }
    
    return tips.get(error_type, tips["general"])
