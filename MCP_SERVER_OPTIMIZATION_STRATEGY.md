# WebSearch MCP Server Optimization Strategy

## Executive Summary

**Problem**: Each Q chat session spawns a new WebSearch MCP server process, leading to resource waste and slower startup times.

**Solution**: Convert from stdio-based communication to TCP daemon mode with process management.

**Impact**: Single server instance serving multiple clients, faster connections, better resource utilization.

---

## Current State Analysis

### Issues Identified
- Multiple Python processes: `python -m websearch.server` (PIDs 8771, 4058)
- Resource duplication across Q chat sessions
- Startup overhead for each new session
- No process lifecycle management

### Current Architecture
```
Q Chat Session 1 → stdio → WebSearch Server Process 1
Q Chat Session 2 → stdio → WebSearch Server Process 2
Q Chat Session N → stdio → WebSearch Server Process N
```

### Target Architecture
```
Q Chat Session 1 ↘
Q Chat Session 2 → TCP → Single WebSearch Daemon → Shared Resources
Q Chat Session N ↗
```

---

## Implementation Plan

### Phase 1: TCP Daemon Conversion
**Objective**: Convert stdio transport to TCP with daemon management

#### Tasks
- [ ] **1.1** Modify FastMCP server to use TCP transport
- [ ] **1.2** Add daemon startup/shutdown logic
- [ ] **1.3** Implement graceful connection handling
- [ ] **1.4** Create daemon management scripts (start/stop/status)
- [ ] **1.5** Update Q CLI configuration to use TCP endpoint
- [ ] **1.6** Add health check endpoint
- [ ] **1.7** Test multi-client connections

#### Deliverables
- TCP-enabled WebSearch server with daemon mode
- Management scripts in `/scripts/` directory
- Updated `mcp.json` configuration
- Health monitoring endpoint

### Phase 2: Process Management & Monitoring
**Objective**: Add robust process lifecycle and monitoring

#### Tasks
- [ ] **2.1** Implement PID file management
- [ ] **2.2** Add automatic restart on failure
- [ ] **2.3** Create process monitoring dashboard
- [ ] **2.4** Add connection pooling logic
- [ ] **2.5** Implement resource usage tracking
- [ ] **2.6** Add log rotation and cleanup
- [ ] **2.7** Create launchd service file for macOS

#### Deliverables
- Robust daemon with auto-restart
- Monitoring and metrics collection
- macOS service integration
- Connection pool management

### Phase 3: Performance & Scaling
**Objective**: Optimize performance and add scaling capabilities

#### Tasks
- [ ] **3.1** Add connection caching and reuse
- [ ] **3.2** Implement request queuing and throttling
- [ ] **3.3** Add memory usage optimization
- [ ] **3.4** Add configuration hot-reloading
- [ ] **3.5** Implement graceful shutdown with connection draining
- [ ] **3.6** Add performance benchmarking suite

#### Deliverables
- High-performance daemon with optimization
- Performance monitoring and tuning
- Benchmarking and testing suite

---

## Technical Specifications

### TCP Configuration
```python
# Target configuration
TCP_HOST = "127.0.0.1"
TCP_PORT = 8080  # web-search
```

### File Structure Changes
```
.mcp/web-search/
├── src/websearch/
│   ├── server.py           # Modified for TCP
│   ├── daemon.py           # New daemon logic
│   └── health.py           # Health checks
├── scripts/
│   ├── start-daemon.sh     # Daemon startup
│   ├── stop-daemon.sh      # Daemon shutdown
│   └── status.sh           # Status check
├── config/
│   └── daemon.conf         # Daemon configuration
└── logs/                   # Daemon logs
```

### Configuration Updates
```json
// ~/.aws/amazonq/mcp.json
{
  "mcpServers": {
    "web-search": {
      "transport": "tcp",
      "host": "127.0.0.1",
      "port": 8080,
      "timeout": 5000
    }
  }
}
```

---

## Success Metrics

### Performance Targets
- **Startup Time**: < 100ms connection time (vs current ~2s)
- **Memory Usage**: Single process vs N processes (60-80% reduction)
- **CPU Usage**: Shared processing overhead
- **Connection Time**: Sub-second for subsequent sessions

### Operational Targets
- **Uptime**: 99.9% daemon availability
- **Auto-Recovery**: Automatic restart within 5s of failure
- **Resource Cleanup**: Proper connection cleanup and memory management
- **Monitoring**: Real-time health and performance metrics

---

## Risk Assessment & Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| TCP connection failures | High | Fallback to stdio mode |
| Daemon crashes | Medium | Auto-restart with health checks |
| Port conflicts | Low | Dynamic port allocation |
| Memory leaks | Medium | Connection pooling and cleanup |

### Operational Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing sessions | High | Gradual rollout with feature flags |
| Configuration complexity | Medium | Automated setup scripts |
| Debugging difficulty | Medium | Enhanced logging and monitoring |

---

## Testing Strategy

### Unit Tests
- [ ] TCP transport functionality
- [ ] Daemon lifecycle management
- [ ] Connection pooling logic
- [ ] Health check endpoints

### Integration Tests
- [ ] Multi-client connection handling
- [ ] Q CLI integration with TCP mode
- [ ] Daemon restart scenarios
- [ ] Resource cleanup verification

### Performance Tests
- [ ] Connection latency benchmarks
- [ ] Memory usage under load
- [ ] Concurrent client handling
- [ ] Long-running stability tests

---

## Rollout Plan

### Development Environment
1. **Local Testing**: Implement and test on development machine
2. **Feature Toggle**: Add configuration flag for stdio/TCP mode selection
3. **Parallel Testing**: Run both modes simultaneously for comparison

### Production Rollout
1. **Soft Launch**: Enable TCP mode with stdio fallback
2. **Monitoring Phase**: Monitor performance and stability metrics
3. **Full Migration**: Switch default to TCP mode
4. **Cleanup Phase**: Remove stdio mode support

---

## Task Tracking

### Phase 1 Progress
```
□ 1.1 FastMCP TCP conversion
□ 1.2 Daemon startup/shutdown
□ 1.3 Connection handling
□ 1.4 Management scripts
□ 1.5 Q CLI configuration
□ 1.6 Health check endpoint
□ 1.7 Multi-client testing
```

### Phase 2 Progress
```
□ 2.1 PID file management
□ 2.2 Auto-restart logic
□ 2.3 Monitoring dashboard
□ 2.4 Connection pooling
□ 2.5 Resource tracking
□ 2.6 Log management
□ 2.7 Service integration
```

### Phase 3 Progress
```
□ 3.1 Connection caching
□ 3.2 Request queuing
□ 3.3 Memory optimization
□ 3.4 Hot-reloading
□ 3.5 Graceful shutdown
□ 3.6 Benchmarking suite
```

---

## Critical Context & Implementation Details

### Current Server Implementation
- **Location**: `/Users/guvishl/.mcp/web-search/src/websearch/server.py`
- **Framework**: FastMCP with `mcp = FastMCP("WebSearch")` and `mcp.run()`
- **Entry Point**: `if __name__ == "__main__": main()` calls `mcp.run()`
- **Startup Script**: `/Users/guvishl/.mcp/web-search/start.sh` activates venv and runs `python -m websearch.server`

### Current Q CLI Configuration
- **Config File**: `~/.aws/amazonq/mcp.json`
- **Current Entry**:
```json
"web-search": {
  "command": "/Users/guvishl/.mcp/web-search/start.sh",
  "args": [],
  "env": {},
  "timeout": 120000,
  "disabled": false
}
```

### Active Process Evidence
```bash
# Multiple running instances found:
python -m websearch.server  # PID 8771 (session s157)
python -m websearch.server  # PID 4058 (session s089)
```

### Key FastMCP Research Points
- Default `mcp.run()` uses stdio transport
- Need to investigate TCP transport options in FastMCP
- May require `mcp.run(transport="tcp", host="127.0.0.1", port=8080)`
- Check FastMCP documentation for daemon mode capabilities

### Repository Status
- **Git Remote**: `git@github.com-personal:vishalkg/web-search.git`
- **Branch**: main
- **Last Push**: Successful (commit 89b8321..8596e9a)
- **Working Directory**: Clean, ready for development

### Environment Setup
- **Python Environment**: `/Users/guvishl/.mcp/venv/` (shared venv)
- **PYTHONPATH**: Set to `$DIR/src:$PYTHONPATH` in start.sh
- **Package Structure**: `src/websearch/` with server.py as main module

### Implementation Priority Order
1. **FastMCP TCP Research** - Critical first step
2. **Backup Current Working Version** - Before any changes
3. **Create Feature Branch** - For daemon development
4. **Implement TCP Transport** - Core conversion
5. **Test Multi-Client** - Validation step

---

## Next Actions

1. **Immediate**: Research FastMCP TCP transport documentation and capabilities
2. **Backup**: Create git branch `feature/tcp-daemon` from current working state
3. **Implement**: Start Phase 1.1 - FastMCP TCP conversion in server.py
4. **Test**: Verify TCP mode works before proceeding to daemon logic

---

*Document Version: 1.1*  
*Last Updated: 2025-09-12 23:29*  
*Status: Ready for Implementation*  
*Next Session: Start with FastMCP TCP research*
