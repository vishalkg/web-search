# Web Search MCP Server v2.1.0

A Model Context Protocol (MCP) server that provides advanced web search and content extraction capabilities using multiple search engines with intelligent caching, parallel processing, and enhanced metadata following 2025 MCP best practices.

## ✨ Features

### 🔍 Multi-Engine Search
- **Simultaneous search** across DuckDuckGo, Bing, and Startpage
- **Parallel execution** for optimal performance
- **Result deduplication** with source attribution
- **Intelligent caching** (5-minute TTL) for improved response times

### 📄 Content Extraction
- **Batch processing** of multiple URLs in parallel
- **Intelligent HTML parsing** with ad/navigation removal
- **Content caching** (30-minute TTL) for efficiency
- **Automatic retry** with exponential backoff

### 🚀 Enhanced Metadata (2025 MCP Standards)
- **Dynamic versioning** from package.json
- **Comprehensive tool annotations** with behavior hints
- **Tool categorization** and feature documentation
- **Introspection capabilities** for debugging

## 🛠️ Available Tools

### 1. `search_web` - Multi-Engine Web Search
**Category:** `information_retrieval`
**Features:** multi_engine, caching, parallel_processing, rate_limiting

Search across multiple engines with intelligent result aggregation.

```python
# Examples
search_web("quantum computing applications", 5)
search_web("latest AI research papers", 10)
```

### 2. `fetch_page_content` - Web Content Extractor  
**Category:** `content_extraction`
**Features:** batch_processing, caching, intelligent_parsing, retry_logic

Extract clean text content from web pages with batch support.

```python
# Examples
fetch_page_content("https://en.wikipedia.org/wiki/Machine_learning")
fetch_page_content(["https://docs.python.org/3/tutorial", "https://docs.python.org/3/library"])
```

### 3. `get_tool_info` - Tool Information Inspector
**Category:** `introspection`
**Features:** metadata_inspection

Get comprehensive metadata about the server and available tools.

## 📦 Installation

### Option 1: Standalone (Recommended)
```bash
# Extract files
unzip web-search-mcp.zip -d ~/.mcp/

# Make executable
chmod +x ~/.mcp/web-search/start.sh

# Add to Q CLI
q mcp add web-search ~/.mcp/web-search/start.sh

# Test installation
q mcp status --name web-search
```

### Option 2: Manual Setup
```bash
cd ~/.mcp/web-search
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
chmod +x start.sh
q mcp add web-search ~/.mcp/web-search/start.sh
```

## 📋 Requirements

- **Q CLI** with MCP support
- **Python 3.8+** (included in venv)
- **Internet connection** for web searches
- **macOS/Linux** (Windows support via WSL)

## 🔧 Configuration

### Environment Variables
- `WEB_SEARCH_VERSION` - Override version (default: from package.json)
- Custom logging and timeout settings available in server.py

### Performance Settings
- **Search cache TTL:** 300 seconds (5 minutes)
- **Content cache TTL:** 1800 seconds (30 minutes)  
- **Request timeout:** 12 seconds
- **Content timeout:** 20 seconds
- **Max results:** 20 per search
- **Max content length:** 8000 characters

## 📊 Usage Examples

### Basic Search
```bash
q chat
# "Search for Python web scraping libraries"
```

### Content Extraction
```bash
q chat  
# "Extract content from https://docs.python.org/3/tutorial/"
```

### Tool Inspection
```bash
q chat
# "Get information about available web search tools"
```

## 📁 File Structure

```
~/.mcp/web-search/
├── server.py              # Main MCP server (enhanced v2.1.0)
├── schemas.py             # Pydantic validation schemas  
├── package.json           # Version and project metadata
├── start.sh               # Startup script
├── requirements.txt       # Python dependencies
├── test_integration.py    # E2E tests (14 tests)
├── web-search.log         # Operation logs
├── venv/                  # Virtual environment
└── README.md              # Documentation
```

## 🧪 Testing

Run comprehensive E2E tests:
```bash
cd ~/.mcp/web-search
python test_integration.py
```

**Test Coverage:**
- ✅ Multi-engine search functionality
- ✅ Content extraction and batch processing  
- ✅ Caching mechanisms and expiration
- ✅ Error handling and recovery
- ✅ Performance and deduplication

## 📝 Logging

All operations logged to `web-search.log` with:
- **Timestamps** and operation details
- **Cache hit/miss** information
- **Performance metrics** and error tracking
- **Search engine** response statistics

## 🔍 Troubleshooting

### Common Issues
- **Permission denied:** `chmod +x start.sh`
- **No results:** Check `web-search.log` for errors
- **Slow performance:** Verify internet connection
- **Cache issues:** Restart server to clear caches

### Debug Information
```bash
# Check server status
q mcp status --name web-search

# View recent logs  
tail -f ~/.mcp/web-search/web-search.log

# Test tools directly
q chat
# "Get tool information to see server details"
```

## 🆕 What's New in v2.1.0

### Enhanced Metadata
- ✅ **Dynamic versioning** from package.json
- ✅ **Extended annotations** with behavior hints
- ✅ **Tool categorization** and feature documentation
- ✅ **Comprehensive descriptions** with use cases

### Improved Developer Experience  
- ✅ **Tool introspection** capabilities
- ✅ **Better error messages** and validation
- ✅ **Enhanced logging** with version tracking
- ✅ **2025 MCP best practices** compliance

### Performance Optimizations
- ✅ **Maintained compatibility** with existing functionality
- ✅ **Same performance** characteristics
- ✅ **Enhanced caching** metadata
- ✅ **Better resource management**

## 📄 License

MIT License - See LICENSE file for details

## 👤 Author

**Vishal Gupta** - [GitHub](https://github.com/guvishl)

---

*Built with ❤️ following 2025 MCP best practices for enhanced AI tool integration*
