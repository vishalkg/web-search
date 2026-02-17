# WebSearch MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pylint Score](https://img.shields.io/badge/pylint-10.00/10-brightgreen)](https://pylint.org/)

High-performance Model Context Protocol (MCP) server for web search and content extraction with intelligent fallback system.

## ✨ Features

- **🚀 Fast**: Pure async with connection pooling and zero event loop overhead
- **🔗 Connection Reuse**: Global HTTP connection pool (30-50% faster requests)
- **⚡ Parallel Execution**: asyncio.gather for 2-3x faster batch operations
- **🔍 Multi-Engine**: Google, Bing, DuckDuckGo, Startpage, Brave Search
- **🛡️ Intelligent Fallbacks**: Google→Startpage, Bing→DuckDuckGo, Brave (standalone)
- **📄 Content Extraction**: Clean text extraction from web pages
- **💾 Smart Caching**: LRU cache with compression and deduplication
- **🔑 API Integration**: Google Custom Search, Brave Search APIs with quota management
- **🔄 Auto-Rotation**: Timestamped logs (weekly) and metrics (monthly) with auto-cleanup
- **⚡ Resilient**: Automatic failover and comprehensive error handling

## 📦 Installation

### Quick Start (Recommended)
```bash
# Install uv
brew install uv

# Run directly - no setup needed
uvx --from git+https://github.com/vishalkg/web-search websearch-server
```

### Development
```bash
git clone https://github.com/vishalkg/web-search.git
cd web-search
uv pip install -e .
```

## ⚙️ Configuration

### API Keys (Optional but Recommended)

For best results, configure API keys for Google Custom Search and Brave Search. Without API keys, the server falls back to web scraping which is less reliable.

**Get API Keys:**
- Google: [Custom Search API](https://developers.google.com/custom-search/v1/overview)
- Brave: [Brave Search API](https://brave.com/search/api/)

### Kiro CLI (formerly Amazon Q CLI)
```bash
# Add to Kiro CLI with API keys
kiro-cli mcp add --name websearch \
  --command uvx \
  --args "--from" --args "git+https://github.com/vishalkg/web-search" --args "websearch-server" \
  --env "GOOGLE_CSE_API_KEY=your-google-api-key" \
  --env "GOOGLE_CSE_ID=your-search-engine-id" \
  --env "BRAVE_SEARCH_API_KEY=your-brave-api-key"

# Verify installation
kiro-cli mcp list
```

**Configuration scopes:**
- `--scope global`: Available to all agents
- `--scope workspace`: Project-specific configuration
- `--scope default`: Default agent configuration (default)

### Claude Code
Add to your Claude Code MCP settings (`~/.claude/mcp_settings.json`):

```json
{
  "mcpServers": {
    "websearch": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vishalkg/web-search", "websearch-server"],
      "env": {
        "GOOGLE_CSE_API_KEY": "your-google-api-key",
        "GOOGLE_CSE_ID": "your-search-engine-id",
        "BRAVE_SEARCH_API_KEY": "your-brave-api-key"
      }
    }
  }
}
```

**Test the integration:**
```bash
# Restart Claude Code after configuration
# Use search_web or fetch_page_content tools in your conversations
```

### Claude Desktop
Add to your MCP settings file with API keys:

```json
{
  "mcpServers": {
    "websearch": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vishalkg/web-search", "websearch-server"],
      "env": {
        "GOOGLE_CSE_API_KEY": "your-google-api-key",
        "GOOGLE_CSE_ID": "your-search-engine-id",
        "BRAVE_SEARCH_API_KEY": "your-brave-api-key"
      }
    }
  }
}
```

## 🗂️ File Structure

The server automatically manages files in OS-appropriate locations:

**macOS:**
```
~/Library/Application Support/websearch/  # Data
~/Library/Logs/websearch/                 # Logs
~/Library/Application Support/websearch/  # Config
```

**Linux:**
```
~/.local/share/websearch/    # Data
~/.local/state/websearch/    # Logs
~/.config/websearch/         # Config
```

**Files:**
```
data/
├── search-metrics.jsonl     # Search analytics (auto-rotated)
└── quota/
    └── quotas.json          # API quota tracking
logs/
└── web-search.log           # Application logs (auto-rotated)
config/
└── .env                     # Configuration file
└── cache/                  # Optional caching
```

### Environment Variable Overrides
- `WEBSEARCH_HOME`: Base directory (default: `~/.websearch`)
- `WEBSEARCH_CONFIG_DIR`: Config directory override
- `WEBSEARCH_LOG_DIR`: Log directory override

## 🔧 Usage

The server provides two main tools with multiple search modes:

### Search Web
```python
# Standard 5-engine search (backward compatible)
search_web("quantum computing applications", num_results=10)

# New 3-engine fallback search (optimized)
search_web_fallback("machine learning tutorials", num_results=5)
```

**Search Engines:**
- **Google Custom Search API** (with Startpage fallback)
- **Bing** (with DuckDuckGo fallback)
- **Brave Search API** (standalone)
- **DuckDuckGo** (scraping)
- **Startpage** (scraping)

### Fetch Page Content
```python
# Extract clean text from URLs
fetch_page_content("https://example.com")
fetch_page_content(["https://site1.com", "https://site2.com"])  # Batch processing
```

## 🏗️ Architecture

```
websearch/
├── core/
│   ├── async_search.py        # Async search orchestration
│   ├── async_fallback_search.py # 3-engine fallback system
│   ├── ranking.py             # Quality-first result ranking
│   ├── content.py             # Content fetching with async
│   └── common.py              # Shared utilities
├── engines/
│   ├── google_api.py          # Google Custom Search API
│   ├── brave_api.py           # Brave Search API (native async)
│   ├── async_search.py        # Async engine implementations
│   └── parsers.py             # HTML parsing utilities
├── utils/
│   ├── connection_pool.py     # Global HTTP connection pooling
│   ├── unified_quota.py       # Unified API quota management
│   ├── advanced_cache.py      # LRU cache with compression
│   ├── deduplication.py       # Result deduplication
│   └── http.py                # HTTP utilities
└── server.py                  # FastMCP server (pure async)
```

## 🔧 Advanced Configuration

### Environment Variables
```bash
# API Configuration
export GOOGLE_CSE_API_KEY=your_google_api_key
export GOOGLE_CSE_ID=your_google_cse_id
export BRAVE_SEARCH_API_KEY=your_brave_api_key

# Quota Management (Optional)
export GOOGLE_DAILY_QUOTA=100        # Default: 100 requests/day
export BRAVE_MONTHLY_QUOTA=2000      # Default: 2000 requests/month

# Performance Tuning
export WEBSEARCH_CACHE_SIZE=1000
export WEBSEARCH_TIMEOUT=10
export WEBSEARCH_LOG_LEVEL=INFO
```

### How to Get API Keys

#### Google Custom Search API
1. **API Key**: Go to https://developers.google.com/custom-search/v1/introduction and click "Get a Key"
2. **CSE ID**: Go to https://cse.google.com/cse/ and follow prompts to create a search engine

#### Brave Search API
1. Go to [Brave Search API](https://api.search.brave.com/)
2. Sign up for a free account
3. Go to your dashboard
4. Copy the API key as `BRAVE_API_KEY`
5. Free tier: 2000 requests/month

### Quota Management
- **Unified System**: Single quota manager for all APIs
- **Google**: Daily quota (default 100 requests/day)
- **Brave**: Monthly quota (default 2000 requests/month)
- **Storage**: Quota files stored in `~/.websearch/` directory
- **Auto-reset**: Quotas automatically reset at period boundaries
- **Fallback**: Automatic fallback to scraping when quotas exhausted

### Search Modes
- **Standard Mode**: Uses all 5 engines for maximum coverage
- **Fallback Mode**: Uses 3 engines with intelligent fallbacks for efficiency
- **API-First Mode**: Prioritizes API calls over scraping when keys available

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No results | Check internet connection and logs |
| API quota exhausted | System automatically falls back to scraping |
| Google API errors | Verify `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID` |
| Brave API errors | Check `BRAVE_SEARCH_API_KEY` and quota status |
| Permission denied | `chmod +x start.sh` |
| Import errors | Ensure Python 3.12+ and dependencies installed |
| Circular import warnings | Fixed in v2.0+ (10.00/10 pylint score) |

### Debug Mode
```bash
# Enable detailed logging
export WEBSEARCH_LOG_LEVEL=DEBUG
python -m websearch.server
```

### API Status Check
```bash
# Test API connectivity
cd debug/
python test_brave_api.py      # Test Brave API
python test_fallback.py       # Test fallback system
```

## 📈 Performance & Monitoring

### Metrics
- **Pylint Score**: 10.00/10 (perfect code quality)
- **Search Speed**: ~1-1.5 seconds for 3-engine search (50-70% faster with optimizations)
- **Batch Operations**: 2-3x faster with asyncio.gather vs threading
- **Connection Reuse**: 90%+ reuse rate (200-500ms saved per request)
- **Memory Efficiency**: ~4000x less memory for batch operations (async vs threads)
- **Cache Hit Rate**: ~85% for repeated queries
- **API Quota Efficiency**: Automatic fallback prevents service interruption

### Monitoring
Logs are written to `web-search.log` with structured format:
```bash
tail -f web-search.log | grep "search completed"
```

## 🔒 Security

- **No hardcoded secrets**: All API keys via environment variables
- **Clean git history**: Secrets scrubbed from all commits
- **Input validation**: Comprehensive sanitization of search queries
- **Rate limiting**: Built-in quota management for API calls
- **Secure defaults**: HTTPS-only requests, timeout protection

## 🚀 Performance Tips

1. **Connection pooling** is automatic - connections are reused for 30-50% faster requests
2. **Batch operations** use asyncio.gather for optimal parallelism (no manual tuning needed)
3. **Set API keys** to reduce reliance on scraping (faster + more reliable)
4. **Caching** is enabled by default with LRU and compression
5. **Pure async** implementation eliminates event loop overhead automatically

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
