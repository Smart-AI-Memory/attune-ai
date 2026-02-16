# Hot-Reload Infrastructure

**Version:** 1.0.0
**Status:** Production Ready
**Phase:** 2 of 4 - Wizard Factory Enhancement

## Overview

The Hot-Reload Infrastructure enables real-time wizard reloading during development without server restarts. When you modify a wizard file, it's automatically reloaded and re-registered with the wizard API.

### Key Features

- ✅ **Zero Downtime** - No server restart required
- ✅ **File Watching** - Automatic detection of wizard file changes
- ✅ **WebSocket Notifications** - Real-time client notifications
- ✅ **Graceful Error Handling** - Reload failures don't crash the server
- ✅ **Development Mode Toggle** - Enable/disable via environment variable

---

## Quick Start

### 1. Install Dependencies

```bash
pip install watchdog
```

### 2. Enable Hot-Reload

Set environment variable:

```bash
export HOT_RELOAD_ENABLED=true
```

### 3. Integrate with Wizard API

Add to `backend/api/wizard_api.py`:

```python
from hot_reload.integration import HotReloadIntegration

app = FastAPI(title="Attune Wizard API")

# Create hot-reload integration
hot_reload = HotReloadIntegration(app, register_wizard)

@app.on_event("startup")
async def startup_event():
    init_wizards()  # Initialize wizards
    hot_reload.start()  # Start hot-reload

@app.on_event("shutdown")
async def shutdown_event():
    hot_reload.stop()

# Add status endpoint
@app.get("/api/hot-reload/status")
async def get_hot_reload_status():
    if not hot_reload:
        return {"enabled": False}
    return hot_reload.get_status()
```

### 4. Connect Frontend (Optional)

```javascript
// Connect to WebSocket for reload notifications
const ws = new WebSocket('ws://localhost:8001/ws/hot-reload');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.event === 'wizard_reloaded') {
        console.log(`✓ Wizard reloaded: ${message.wizard_id}`);
        // Refresh wizard list or show notification
    }

    if (message.event === 'wizard_reload_failed') {
        console.error(`✗ Reload failed: ${message.error}`);
        // Show error notification
    }
};

// Keep connection alive
setInterval(() => ws.send('ping'), 30000);
```

---

## Architecture

### Components

```
hot_reload/
├── __init__.py          # Package exports
├── config.py            # Configuration from environment
├── watcher.py           # File system watcher (watchdog)
├── reloader.py          # Dynamic module reloader
├── websocket.py         # WebSocket notifications
└── integration.py       # FastAPI integration
```

### Flow Diagram

```
File Change → Watcher → Reloader → Register → Notify Clients
              ↓          ↓          ↓          ↓
         watchdog    importlib   wizard_api  WebSocket
```

### Detailed Flow

1. **File Watcher** detects `.py` file change in wizard directory
2. **Extract Wizard ID** from filename (`debug_wizard.py` → `debug`)
3. **Unload Module** from `sys.modules`
4. **Reload Module** with `importlib.import_module()`
5. **Find Wizard Class** (classes ending with "Wizard")
6. **Re-Register** with wizard API
7. **Notify Clients** via WebSocket

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOT_RELOAD_ENABLED` | `false` | Enable hot-reload |
| `HOT_RELOAD_WATCH_DIRS` | Auto-detect | Comma-separated directories to watch |
| `HOT_RELOAD_WS_PATH` | `/ws/hot-reload` | WebSocket endpoint path |
| `HOT_RELOAD_DELAY` | `0.5` | Debounce delay in seconds |

### Watched Directories (Default)

- `wizards/` - Healthcare wizards
- `coach_wizards/` - Coach wizards
- `attune_software_plugin/wizards/` - AI wizards
- `attune_llm/wizards/` - Domain wizards

### Custom Watch Directories

```bash
export HOT_RELOAD_WATCH_DIRS="/path/to/custom/wizards,/another/path"
```

---

## API Reference

### HotReloadIntegration

Main integration class for hot-reload.

```python
class HotReloadIntegration:
    def __init__(self, app: FastAPI, register_callback: callable):
        """Initialize hot-reload integration.

        Args:
            app: FastAPI application
            register_callback: Function to register wizard
                               (wizard_id, wizard_class) -> bool
        """

    def start(self) -> None:
        """Start file watcher"""

    def stop(self) -> None:
        """Stop file watcher"""

    def get_status(self) -> dict:
        """Get hot-reload status"""
```

### WizardReloader

Handles dynamic module reloading.

```python
class WizardReloader:
    def reload_wizard(self, wizard_id: str, file_path: str) -> ReloadResult:
        """Reload a wizard module"""

    def get_reload_count(self) -> int:
        """Get total successful reloads"""
```

### ReloadResult

Result of a reload operation.

```python
@dataclass
class ReloadResult:
    success: bool
    wizard_id: str
    message: str
    error: str | None
```

---

## Usage Examples

### Example 1: Basic Integration

```python
from fastapi import FastAPI
from hot_reload.integration import HotReloadIntegration

app = FastAPI()

def register_wizard(wizard_id: str, wizard_class: type) -> bool:
    """Your wizard registration logic"""
    try:
        WIZARDS[wizard_id] = wizard_class()
        return True
    except Exception:
        return False

# Initialize
hot_reload = HotReloadIntegration(app, register_wizard)

@app.on_event("startup")
async def startup():
    hot_reload.start()
```

### Example 2: Manual Reload

```python
from hot_reload import WizardReloader

reloader = WizardReloader(
    register_callback=register_wizard,
    notification_callback=notify_clients
)

# Manually reload a wizard
result = reloader.reload_wizard("debug", "/path/to/debug_wizard.py")

if result.success:
    print(f"✓ {result.message}")
else:
    print(f"✗ Error: {result.error}")
```

### Example 3: Custom File Watcher

```python
from pathlib import Path
from hot_reload import WizardFileWatcher

def on_change(wizard_id: str, file_path: str):
    print(f"File changed: {wizard_id} at {file_path}")

watcher = WizardFileWatcher(
    wizard_dirs=[Path("custom/wizards")],
    reload_callback=on_change
)

with watcher:  # Context manager auto-starts/stops
    # Watcher is active
    input("Press Enter to stop...")
```

---

## WebSocket Protocol

### Events Sent by Server

#### `connected`
```json
{
    "event": "connected",
    "message": "Hot-reload notifications enabled",
    "active_connections": 1
}
```

#### `wizard_reloaded`
```json
{
    "event": "wizard_reloaded",
    "wizard_id": "debug",
    "success": true,
    "reload_count": 5
}
```

#### `wizard_reload_failed`
```json
{
    "event": "wizard_reload_failed",
    "wizard_id": "debug",
    "success": false,
    "error": "Failed to import module: ModuleNotFoundError"
}
```

### Client Messages

Send `"ping"` to keep connection alive.

---

## Error Handling

### Graceful Degradation

Hot-reload failures **never crash the server**. Common errors are handled gracefully:

1. **Import Errors** - Logged, old wizard continues working
2. **Registration Errors** - Logged, old wizard continues working
3. **File System Errors** - Logged, watcher continues monitoring
4. **WebSocket Errors** - Client disconnected, others unaffected

### Error Scenarios

| Scenario | Behavior | Old Wizard |
|----------|----------|------------|
| Syntax error in wizard | Reload fails, error logged | Still works |
| Missing dependency | Import fails, error logged | Still works |
| Registration fails | Logged, notification sent | Still works |
| WebSocket disconnect | Client removed | Others unaffected |

---

## Performance

### Reload Speed

- **File Detection**: <100ms (watchdog)
- **Module Reload**: ~50-200ms
- **Total Reload Time**: <500ms

### Resource Usage

- **Memory**: ~2-5MB (watchdog observer)
- **CPU**: <1% (idle), ~5-10% (during reload)
- **Network**: Minimal (WebSocket keepalive only)

### Optimization Tips

1. **Use Reload Delay**: Set `HOT_RELOAD_DELAY=1.0` to debounce multiple file saves
2. **Limit Watch Directories**: Only watch directories with wizards
3. **Disable in Production**: `HOT_RELOAD_ENABLED=false` (default)

---

## Troubleshooting

### Hot-Reload Not Working

**Check if enabled:**
```bash
curl http://localhost:8001/api/hot-reload/status
```

**Expected response:**
```json
{
    "enabled": true,
    "running": true,
    "watch_dirs": ["/path/to/wizards"],
    "reload_count": 0,
    "websocket_connections": 0
}
```

**If enabled=false:**
```bash
export HOT_RELOAD_ENABLED=true
# Restart server
```

### Wizard Not Reloading

**Check logs for errors:**
```bash
tail -f app.log | grep "hot.reload"
```

**Common issues:**
1. Wizard file not in watched directory
2. Syntax error in wizard (check reload_failed event)
3. Import error (missing dependency)

### WebSocket Not Connecting

**Check endpoint:**
```bash
# Default path
wscat -c ws://localhost:8001/ws/hot-reload
```

**If connection fails:**
1. Check `HOT_RELOAD_WS_PATH` environment variable
2. Verify FastAPI app is running
3. Check firewall/proxy settings

---

## Testing

### Manual Testing

1. Start API with hot-reload enabled
2. Modify a wizard file
3. Check logs for reload message
4. Verify wizard works with new code

### Integration Tests

See `tests/integration/hot_reload/` for automated tests.

---

## Security Considerations

### Development Only

⚠️ **Hot-reload is for DEVELOPMENT ONLY**

- Do NOT enable in production (`HOT_RELOAD_ENABLED=false`)
- No authentication on WebSocket endpoint
- File system watching has security implications

### Recommended Setup

**Development:**
```bash
export HOT_RELOAD_ENABLED=true
```

**Production:**
```bash
export HOT_RELOAD_ENABLED=false  # Default
```

---

## Roadmap

### Phase 2 (Current)
- ✅ File watching with watchdog
- ✅ Dynamic module reloading
- ✅ WebSocket notifications
- ✅ FastAPI integration
- ✅ Configuration system

### Future Enhancements
- [ ] Selective reload (only changed functions)
- [ ] Rollback on failed reload
- [ ] Reload history/undo
- [ ] Hot-reload for config files
- [ ] Browser extension for notifications

---

## License

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0

---

**For questions or issues, see:** [Wizard Factory Enhancement Plan](../docs/architecture/WIZARD_FACTORY_DISCOVERY.md)
