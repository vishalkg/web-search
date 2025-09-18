# WebSearch MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

High-performance Model Context Protocol (MCP) server for web search and content extraction with async architecture.

## ✨ Features

- **🚀 Fast**: Async implementation for optimal performance
- **🔍 Multi-Engine**: DuckDuckGo, Bing, Startpage with parallel execution  
- **📄 Content Extraction**: Clean text extraction from web pages
- **💾 Smart Caching**: LRU cache with compression
- **🛡️ Resilient**: Automatic fallbacks and comprehensive error handling

## 🚀 Quick Start

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
q chat
# Try: "search web for python tutorials"
```

## 📦 Installation

### From GitHub (Recommended)
```bash
git clone https://github.com/vishalkg/web-search.git ~/.mcp/web-search
cd ~/.mcp
python3 -m venv venv
source venv/bin/activate
cd web-search
pip install -e .
chmod +x start.sh
q mcp add websearch ~/.mcp/web-search/start.sh
```

### Manual Setup
```bash
# If you already have the files
cd ~/.mcp/web-search
python3 -m venv venv
source venv/bin/activate
pip install -e .
chmod +x start.sh
q mcp add websearch ~/.mcp/web-search/start.sh
```

## 🔧 Usage

The server provides two main tools:

### Search Web
```python
# Multi-engine web search
search_web("quantum computing applications", num_results=10)
```

### Fetch Page Content  
```python
# Extract clean text from URLs
fetch_page_content("https://example.com")
fetch_page_content(["https://site1.com", "https://site2.com"])  # Batch processing
```

## 🏗️ Architecture

```
websearch/
├── core/           # Search logic (sync + async)
├── engines/        # Search engine implementations  
├── utils/          # Caching, HTTP, utilities
└── server.py       # FastMCP server
```

## 🔧 Configuration

Set environment variables for customization:
```bash
export WEBSEARCH_CACHE_SIZE=1000
export WEBSEARCH_TIMEOUT=10
export WEBSEARCH_LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No results | Check internet connection and logs |
| Permission denied | `chmod +x start.sh` |
| Import errors | Ensure Python 3.12+ and dependencies installed |

## 📈 Monitoring

Logs are written to `web-search.log` with structured format for debugging and monitoring.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
