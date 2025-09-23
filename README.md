# WebSearch MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pylint Score](https://img.shields.io/badge/pylint-10.00/10-brightgreen)](https://pylint.org/)

High-performance Model Context Protocol (MCP) server for web search and content extraction with intelligent fallback system.

## ✨ Features

- **🚀 Fast**: Async implementation with parallel execution
- **🔍 Multi-Engine**: Google, Bing, DuckDuckGo, Startpage, Brave Search
- **🛡️ Intelligent Fallbacks**: Google→Startpage, Bing→DuckDuckGo, Brave (standalone)
- **📄 Content Extraction**: Clean text extraction from web pages
- **💾 Smart Caching**: LRU cache with compression and deduplication
- **🔑 API Integration**: Google Custom Search, Brave Search APIs with quota management
- **⚡ Resilient**: Automatic failover and comprehensive error handling

## 🚀 Quick Start

### Q CLI
```bash
# Install from GitHub
git clone https://github.com/vishalkg/web-search.git ~/.mcp/web-search
cd ~/.mcp
python3 -m venv venv
source venv/bin/activate
cd web-search
pip install -e .
chmod +x start.sh

# Add to Q CLI
q mcp add websearch ~/.mcp/web-search/start.sh

# Test
q chat "search for python tutorials"
```

## 📦 Installation Options

### Option 1: Direct install from GitHub (Recommended)
```bash
# Basic installation (DuckDuckGo, Bing, Startpage)
pip install git+https://github.com/vishalkg/web-search.git

# With Google API support  
pip install "git+https://github.com/vishalkg/web-search.git[google]"

# With all features
pip install "git+https://github.com/vishalkg/web-search.git[all]"

# Then run
websearch-server
```

### Option 2: Development installation
```bash
git clone https://github.com/vishalkg/web-search.git
cd web-search
pip install -e .
```

### Option 3: Manual dependencies
```bash
git clone https://github.com/vishalkg/web-search.git
cd web-search
pip install -r requirements.txt
```

## 🗂️ File Structure (Installation Independent)

The server automatically creates and manages files in a unified user directory:

```
~/.websearch/                 # Single websearch directory
├── venv/                    # Virtual environment (recommended)
├── config/
│   └── .env                 # Configuration file
├── data/
│   ├── search-metrics.jsonl # Search analytics
│   └── quota/              # API quota tracking
│       ├── google_quota.json
│       └── brave_quota.json
├── logs/
│   └── web-search.log      # Application logs
└── cache/                  # Optional caching
```

### Environment Variable Overrides
- `WEBSEARCH_HOME`: Base directory (default: `~/.websearch`)
- `WEBSEARCH_CONFIG_DIR`: Config directory override  
- `WEBSEARCH_LOG_DIR`: Log directory override

## ⚙️ MCP Configuration

### Recommended Setup (unified directory):
```bash
# Create everything in ~/.websearch/
python -m venv ~/.websearch/venv
source ~/.websearch/venv/bin/activate
pip install git+https://github.com/vishalkg/web-search.git
```

### MCP Settings:
```json
{
  "mcpServers": {
    "websearch": {
      "command": "~/.websearch/venv/bin/websearch-server"
    }
  }
}
```

### Alternative (system/user install):
```json
{
  "mcpServers": {
    "websearch": {
      "command": "websearch-server"
    }
  }
}
```
q chat
# Try: "search web for python tutorials"
```

### Claude Desktop
```bash
# Install and configure (see detailed instructions below)
git clone https://github.com/vishalkg/web-search.git ~/.mcp/web-search
# Configure claude_desktop_config.json
# Restart Claude Desktop
# Look for 🔨 MCP indicator
```

## 🔧 Configuration

### API Keys (Optional)
For enhanced performance, configure API keys:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
GOOGLE_CSE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_google_cse_id_here
BRAVE_SEARCH_API_KEY=your_brave_api_key_here
```

**Fallback Behavior:**
- **Google API** → Falls back to **Startpage** scraping if quota exhausted
- **Bing scraping** → Falls back to **DuckDuckGo** scraping if blocked
- **Brave API** → Standalone with quota management

## 📦 Installation
cd ~/.mcp
python3 -m venv venv
source venv/bin/activate
cd web-search
pip install -e .
chmod +x start.sh
q mcp add websearch ~/.mcp/web-search/start.sh
```

### For Claude Desktop
```bash
# 1. Install the server
git clone https://github.com/vishalkg/web-search.git ~/.mcp/web-search
cd ~/.mcp/web-search
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 2. Configure Claude Desktop
# Open Claude Desktop → Settings → Developer → Edit Config
# Add this to your claude_desktop_config.json:
```

**macOS Configuration:**
```json
{
  "mcpServers": {
    "websearch": {
      "command": "/Users/YOUR_USERNAME/.mcp/web-search/venv/bin/python",
      "args": ["-m", "websearch.server"],
      "cwd": "/Users/YOUR_USERNAME/.mcp/web-search"
    }
  }
}
```

**Windows Configuration:**
```json
{
  "mcpServers": {
    "websearch": {
      "command": "C:\\Users\\YOUR_USERNAME\\.mcp\\web-search\\venv\\Scripts\\python.exe",
      "args": ["-m", "websearch.server"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\.mcp\\web-search"
    }
  }
}
```

**After configuration:**
1. Replace `YOUR_USERNAME` with your actual username
2. Restart Claude Desktop completely
3. Look for the 🔨 MCP indicator in the chat input
4. Try: "search web for python tutorials"

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
│   ├── search.py              # Sync search orchestration
│   ├── async_search.py        # Async search orchestration  
│   ├── fallback_search.py     # 3-engine fallback system
│   ├── async_fallback_search.py # Async fallback system
│   ├── ranking.py             # Quality-first result ranking
│   └── common.py              # Shared utilities
├── engines/
│   ├── google_api.py          # Google Custom Search API
│   ├── brave_api.py           # Brave Search API
│   ├── bing.py                # Bing scraping
│   ├── duckduckgo.py          # DuckDuckGo scraping
│   └── startpage.py           # Startpage scraping
├── utils/
│   ├── unified_quota.py       # Unified API quota management
│   ├── deduplication.py       # Result deduplication
│   ├── advanced_cache.py      # Enhanced caching system
│   └── http.py                # HTTP utilities
└── server.py                  # FastMCP server
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
- **Search Speed**: ~2-3 seconds for 5-engine search
- **Fallback Speed**: ~1-2 seconds for 3-engine search  
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

1. **Use fallback mode** for faster searches when you don't need maximum coverage
2. **Set API keys** to reduce reliance on scraping (faster + more reliable)
3. **Enable caching** for repeated queries (enabled by default)
4. **Tune batch sizes** for content extraction based on your needs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
