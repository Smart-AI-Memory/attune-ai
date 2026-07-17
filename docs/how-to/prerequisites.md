---
description: Prerequisites: *What you need before building with the Attune AI* --- ## Quick Checklist Before you begin, ensure you have: - [ ] **Python 3.9+** instal
---

# Prerequisites

*What you need before building with the Attune AI*

---

## Quick Checklist

Before you begin, ensure you have:

- [ ] **Python 3.10+** installed
- [ ] **Redis** running locally OR a cloud Redis URL
- [ ] **30 minutes** for initial setup
- [ ] **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com/))

---

## Detailed Requirements

### 1. Python Environment

**Minimum version**: Python 3.10

**Recommended**: Python 3.11+ for best async performance

```bash
# Check your version
python --version

# Create a virtual environment (recommended)
python -m venv attune-env
source attune-env/bin/activate  # macOS/Linux
# or
attune-env\Scripts\activate      # Windows
```

**Required knowledge**:
- Basic Python syntax
- Package installation with pip
- (Optional) async/await for advanced patterns

---

### 2. Redis for Short-Term Memory

The framework uses Redis for agent coordination. You have three options:

#### Option A: Local Redis (Development)

```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows (WSL recommended)
# Use WSL and follow Ubuntu instructions

# Docker (any platform)
docker run -d -p 6379:6379 redis:alpine
```

**Verify it's running**:
```bash
redis-cli ping
# Should return: PONG
```

#### Option B: Cloud Redis (Production)

For production or team environments, use a managed Redis service:

| Provider | Free Tier | Setup Time |
|----------|-----------|------------|
| [Railway](https://railway.app) | 500MB | 2 minutes |
| [Upstash](https://upstash.com) | 10K commands/day | 2 minutes |
| [Redis Cloud](https://redis.com/try-free/) | 30MB | 5 minutes |
| AWS ElastiCache | No free tier | 15 minutes |

**Set the connection URL**:
```bash
export REDIS_URL="redis://default:password@your-host:port"
```

#### Option C: Mock Mode (No Redis)

For quick experiments without Redis:

```python
import os

os.environ["ATTUNE_REDIS_MOCK"] = "true"

import attune  # In-memory mock backend is used automatically
```

**Limitations**: Mock mode doesn't persist across restarts.

---

### 3. Anthropic API Key

Attune AI runs on Anthropic's Claude models exclusively.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get your key: [console.anthropic.com](https://console.anthropic.com/)

---

### 4. Install the Framework

```bash
# Core framework
pip install attune-ai

# With Redis support
pip install attune-ai

# With the ops dashboard
pip install 'attune-ai[ops]'
```

**Verify installation**:
```python
import attune

print("Attune AI installed successfully!")
```

---

## Knowledge Prerequisites

### Required

| Skill | Why It's Needed | Quick Resource |
|-------|-----------------|----------------|
| Python basics | All examples are in Python | [Python Tutorial](https://docs.python.org/3/tutorial/) |
| Environment variables | Configuration and API keys | [12-Factor App](https://12factor.net/config) |

### Helpful But Optional

| Skill | When You'll Need It | Quick Resource |
|-------|---------------------|----------------|
| async/await | Multi-agent patterns | [Real Python Async](https://realpython.com/async-io-python/) |
| Redis basics | Custom memory patterns | [Redis Quickstart](https://redis.io/docs/getting-started/) |
| Docker | Production deployment | [Docker Getting Started](https://docs.docker.com/get-started/) |

---

## Environment Setup Script

Run this script to verify your environment:

```python
#!/usr/bin/env python3
"""Verify Attune AI prerequisites."""

import sys
import os

def check_python():
    version = sys.version_info
    if version >= (3, 10):
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"[FAIL] Python {version.major}.{version.minor} (need 3.10+)")
        return False

def check_redis():
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.ping()
        print("[OK] Redis connected")
        return True
    except Exception as e:
        if os.getenv("ATTUNE_REDIS_MOCK") == "true":
            print("[OK] Redis mock mode enabled")
            return True
        print(f"[WARN] Redis not available: {e}")
        print("       Set ATTUNE_REDIS_MOCK=true to use mock mode")
        return False

def check_api_keys():
    if os.getenv("ANTHROPIC_API_KEY"):
        print("[OK] Anthropic API key configured")
        return True
    print("[WARN] ANTHROPIC_API_KEY not set")
    print("       Get your key at console.anthropic.com")
    return False

def check_attune():
    try:
        import attune  # noqa: F401

        print("[OK] Attune AI installed")
        return True
    except ImportError:
        print("[FAIL] Attune AI not installed")
        print("       Run: pip install attune-ai")
        return False

if __name__ == "__main__":
    print("=== Attune AI Prerequisites Check ===\n")

    results = [
        check_python(),
        check_attune(),
        check_redis(),
        check_api_keys(),
    ]

    print("\n" + "=" * 45)
    if all(results):
        print("All prerequisites met! You're ready to start.")
    else:
        print("Some prerequisites need attention. See above.")
```

Save as `check_prereqs.py` and run:
```bash
python check_prereqs.py
```

---

## Troubleshooting

### "Redis connection refused"

Redis isn't running. Start it with:
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### "No module named 'attune'"

Install the framework:
```bash
pip install attune-ai
```

### "API key not found"

Set your environment variable:
```bash
# Add to ~/.bashrc or ~/.zshrc for persistence
export ANTHROPIC_API_KEY="your-key-here"
```

### "Python version too old"

Use pyenv to manage Python versions:
```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11.0
pyenv local 3.11.0
```

---

## Next Steps

Once prerequisites are met:

1. **Quick start**: [Unified Memory System](./unified-memory-system.md)
2. **Understand the philosophy**: Multi-Agent Philosophy
3. **See patterns**: [Practical Patterns](./practical-patterns.md)

---

*Estimated setup time: 15-30 minutes depending on your starting point*
