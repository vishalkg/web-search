# Web Search MCP Server (Standalone)

A Model Context Protocol (MCP) server that provides web search capabilities using multiple search engines (DuckDuckGo, Bing, and Startpage) with parallel execution and result deduplication.

## Features

- **Multi-engine search**: Searches DuckDuckGo, Bing, and Startpage simultaneously
- **Parallel execution**: All searches run concurrently for faster results
- **Result deduplication**: Removes duplicate URLs from combined results
- **Source attribution**: Shows which search engine provided each result
- **Comprehensive logging**: Logs all operations to `web-search.log`
- **Standalone**: Pre-configured virtual environment included - no setup required
- **Two tools available**:
  - `SearchWeb`: Multi-engine web search
  - `FetchPageContent`: Extract text content from web pages

## Installation

### Option 1: Standalone (Pre-configured venv included)

1. **Extract the files**:
   ```bash
   unzip web-search-mcp.zip -d ~/.mcp/
   ```

2. **Make start script executable**:
   ```bash
   chmod +x ~/.mcp/web-search/start.sh
   ```

3. **Add to Q CLI MCP configuration**:
   ```bash
   q mcp add web-search ~/.mcp/web-search/start.sh
   ```

4. **Verify installation and test**:
   ```bash
   q mcp status --name web-search
   q chat
   # In chat: "search web for python libraries"
   ```

### Option 2: Manual Setup (If venv is missing)

1. **Navigate to the directory**:
   ```bash
   cd ~/.mcp/web-search
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment and install dependencies**:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   deactivate
   ```

4. **Make start script executable**:
   ```bash
   chmod +x start.sh
   ```

5. **Add to Q CLI MCP configuration**:
   ```bash
   q mcp add web-search ~/.mcp/web-search/start.sh
   ```

6. **Test the installation**:
   ```bash
   q mcp status --name web-search
   ```

## Files Included

- `server.py` - Main MCP server code
- `start.sh` - Startup script  
- `requirements.txt` - Python dependencies
- `venv/` - Pre-configured virtual environment with all dependencies
- `README.md` - This documentation

## Usage

Start a new Q CLI chat session. The server provides two tools:

### SearchWeb
```
Search query: "python web scraping libraries"
```

### FetchPageContent  
```
Fetch content from: "https://example.com"
```

## Logs

All operations are logged to `web-search.log` in the server directory with timestamps and detailed information about search requests and results.

## Troubleshooting

- **Permission denied**: Ensure `start.sh` is executable (`chmod +x start.sh`)
- **No search results**: Check the log file for error messages
- **Debugging**: Check `web-search.log` for detailed debugging information

## Requirements

- Q CLI with MCP support
- Internet connection for web searches
- macOS/Linux (Python 3.11+ included in venv)
