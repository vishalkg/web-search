# MCP Server Management: Recommended Approach

## TL;DR
Use `uvx` to run Python MCP servers. Store state in user data directories, not relative to script location.

## Running MCP Servers

### Recommended: uvx (uv tool runner)

**Why:**
- 10-100x faster than pip
- Automatic environment isolation (no manual venv management)
- Zero configuration needed
- Cached environments for speed

**Installation:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS (Homebrew)
brew install uv

# Windows (PowerShell as admin)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Usage:**
```bash
# Run any MCP server directly
uvx mcp-server-package-name

# Update to latest
uvx mcp-server-package-name@latest

# List installed tools
uv tool list
```

### Alternative: Docker (for production)

**When to use:**
- Multiple servers with conflicting dependencies
- Production/shared environments
- Need strict security boundaries
- Distributing to others

**Basic setup:**
```bash
docker run -v ~/.mcp-state:/app/state my-mcp-server
```

## Making Your Server uvx-Compatible

Most pip-installable packages already work. Just need proper packaging:

**Minimal pyproject.toml:**
```toml
[project]
name = "my-mcp-server"
version = "0.1.0"
dependencies = ["mcp", "platformdirs"]

[project.scripts]
my-mcp-server = "my_package.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Test compatibility:**
```bash
pip install your-mcp-server
your-mcp-server  # If this works, uvx works too
```

## State Management (Critical!)

**Problem:** uvx uses temporary cached environments. Don't store state relative to script location.

**Solution:** Use OS-appropriate user data directories

### Recommended Pattern (with platformdirs)

```python
from platformdirs import user_data_dir
from pathlib import Path
import json

class StateManager:
    def __init__(self, app_name='my-mcp-server'):
        state_dir = Path(user_data_dir(app_name))
        state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = state_dir / 'state.json'
    
    def load(self):
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}
    
    def save(self, data):
        self.state_file.write_text(json.dumps(data, indent=2))
```

**Add dependency:**
```toml
dependencies = ["mcp", "platformdirs"]
```

### Manual Approach (no dependencies)

```python
from pathlib import Path
import os

def get_state_dir(app_name):
    if os.name == 'nt':  # Windows
        base = Path(os.getenv('APPDATA'))
    else:  # macOS/Linux
        base = Path.home() / '.local' / 'share'
    
    state_dir = base / app_name
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir

# Usage
quota_file = get_state_dir('my-mcp-server') / 'quotas.json'
```

### With Environment Variables (for flexibility)

```python
from pathlib import Path
import os

state_dir = Path(os.getenv('MCP_STATE_DIR', Path.home() / '.mcp-state'))
state_dir.mkdir(parents=True, exist_ok=True)
state_file = state_dir / 'quotas.json'
```

Users can customize:
```bash
export MCP_STATE_DIR=/custom/path
uvx my-mcp-server
```

## State Storage Locations

| OS | Default Location |
|----|------------------|
| Linux | `~/.local/share/app-name/` |
| macOS | `~/Library/Application Support/app-name/` |
| Windows | `%APPDATA%\app-name\` |

## Migration from venv + pip

**Before:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install mcp-server
mcp-server
```

**After:**
```bash
uvx mcp-server
```

## Key Principles

1. **Never create venvs manually** for MCP servers - let uvx handle it
2. **Never store state relative to `__file__`** - use user data directories
3. **Use Docker** if you need production-grade isolation or have complex dependencies
4. **Package properly** with pyproject.toml for distribution

## References

- Docker MCP Best Practices: https://www.docker.com/blog/mcp-server-best-practices/
- UV Documentation: https://docs.astral.sh/uv/
- DataCamp UV Guide: https://www.datacamp.com/tutorial/python-uv
- platformdirs: https://pypi.org/project/platformdirs/
