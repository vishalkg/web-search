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

## 📦 Installation

### For Q CLI (Recommended)
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
