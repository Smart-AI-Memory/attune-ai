---
description: How to Start the Dashboard: **Multiple ways to start the Agent Coordination Dashboard** --- ## 🚀 Method 1: CLI Command (Easiest) # Default (localhost:8000) empa
---

# How to Start the Dashboard

**Multiple ways to start the Agent Coordination Dashboard**

---

## 🚀 Method 1: CLI Command (Easiest)

```bash
# Default (localhost:8000)
attune dashboard start

# Custom host/port
attune dashboard start --host 0.0.0.0 --port 8080

# Get help
attune dashboard start --help
```

**When to use:** Quick start, production deployments, CI/CD

---

## 📜 Method 2: Bash Script

```bash
cd /path/to/attune-ai
./scripts/start_dashboard.sh
```

**When to use:** Development, testing, quick demos

---

## 🐍 Method 3: Python Import

```python
from attune.dashboard import run_standalone_dashboard

# Default settings
run_standalone_dashboard()

# Custom settings
run_standalone_dashboard(host="0.0.0.0", port=8080)
```

**When to use:** Embedding in your application, custom integration

---

## 📦 Method 4: Python Module

```bash
# Standalone version (direct Redis)
python -m attune.dashboard.standalone_server

# Simple version (uses telemetry API)
python -m attune.dashboard.simple_server
```

**When to use:** Testing different implementations, development

---

## 🔧 Method 5: Direct Execution

```bash
# From project root
python -c "from attune.dashboard import run_standalone_dashboard; run_standalone_dashboard()"

# With custom port
python -c "from attune.dashboard import run_standalone_dashboard; run_standalone_dashboard(port=8080)"
```

**When to use:** One-liners, automation scripts

---

## 📊 Before Starting: Populate Test Data

The dashboard needs data in Redis to display. Populate it with:

```bash
python scripts/populate_redis_direct.py
```

This creates:
- 5 active agents with heartbeats
- 10 coordination signals
- 15 event stream entries
- 2 pending approval requests
- 333 quality feedback samples

---

## 🌐 Accessing the Dashboard

Once started, open your browser to:

**http://localhost:8000**

Or if you changed the host/port:

**http://{your-host}:{your-port}**

---

## 📋 Complete Usage Examples

### Example 1: Quick Start for Testing

```bash
# Terminal 1: Populate data
cd /path/to/attune-ai
python scripts/populate_redis_direct.py

# Terminal 2: Start dashboard
attune dashboard start

# Open browser to http://localhost:8000
```

### Example 2: Production Deployment

```bash
# Bind to all interfaces on port 8080
attune dashboard start --host 0.0.0.0 --port 8080

# Or with nohup for background
nohup attune dashboard start --host 0.0.0.0 --port 8080 > dashboard.log 2>&1 &
```

### Example 3: Development with Auto-Reload

```bash
# Use script for quick restarts
./scripts/start_dashboard.sh

# Ctrl+C to stop, then restart to see changes
```

### Example 4: Custom Integration

```python
# In your Python application
from attune.dashboard import run_standalone_dashboard
import threading

# Run dashboard in background thread
dashboard_thread = threading.Thread(
    target=run_standalone_dashboard,
    kwargs={"host": "127.0.0.1", "port": 8000"},
    daemon=True
)
dashboard_thread.start()

# Your application continues
print("Dashboard running in background")
# ... rest of your code
```

### Example 5: Docker Container

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -e .
RUN pip install redis

EXPOSE 8000

CMD ["empathy", "dashboard", "start", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t empathy-dashboard .
docker run -p 8000:8000 empathy-dashboard
```

---

## ⚙️ Configuration Options

### Host Options

```bash
# Localhost only (secure, default)
attune dashboard start --host 127.0.0.1

# All interfaces (accessible from network)
attune dashboard start --host 0.0.0.0

# Specific IP
attune dashboard start --host 192.168.1.100
```

### Port Options

```bash
# Default port
attune dashboard start --port 8000

# Alternative ports
attune dashboard start --port 8080
attune dashboard start --port 3000
attune dashboard start --port 80  # Requires sudo
```

---

## 🔄 Auto-Refresh Behavior

The dashboard automatically refreshes every **5 seconds**:
- Fetches latest data from Redis
- Updates all 7 panels
- Shows "Last update: [timestamp]" at bottom

**No manual refresh needed!** Just watch the data update in real-time.

---

## 🛑 Stopping the Dashboard

**Keyboard interrupt:**
```
Press Ctrl+C
```

**Kill process:**
```bash
# Find process
lsof -i :8000

# Kill it
kill <PID>
```

**Docker:**
```bash
docker stop <container-id>
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or use different port
attune dashboard start --port 8080
```

### Dashboard Shows No Data

**Cause:** Redis is empty or data expired

**Solution:**
```bash
python scripts/populate_redis_direct.py
```

### Cannot Connect to Redis

**Error:** `Connection refused`

**Solution:**
```bash
# Start Redis
redis-server

# Or via empathy CLI
attune memory start
```

### Permission Denied (Port 80)

**Error:** `Permission denied`

**Solution:**
```bash
# Use port > 1024 (doesn't require sudo)
attune dashboard start --port 8080

# Or use sudo (not recommended)
sudo attune dashboard start --port 80
```

---

## 📚 Related Documentation

- [DASHBOARD_COMPLETE.md](DASHBOARD_COMPLETE.md) - Complete reference guide
- [DASHBOARD_QUICKSTART.md](../DASHBOARD_QUICKSTART.md) - 3-command quick start
- [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) - Usage guide with examples
- [DASHBOARD_TESTING.md](DASHBOARD_TESTING.md) - Testing instructions

---

## ✅ Quick Reference

| Method | Command | When to Use |
|--------|---------|-------------|
| **CLI** | `attune dashboard start` | Production, recommended |
| **Script** | `./scripts/start_dashboard.sh` | Development, testing |
| **Python** | `run_standalone_dashboard()` | Integration, custom apps |
| **Module** | `python -m attune.dashboard.standalone_server` | Direct execution |

**Default URL:** http://localhost:8000

**Auto-refresh:** Every 5 seconds

**Stop:** Press Ctrl+C

---

**Version:** 1.0.0
**Last Updated:** January 27, 2026
**Status:** Production Ready ✅
