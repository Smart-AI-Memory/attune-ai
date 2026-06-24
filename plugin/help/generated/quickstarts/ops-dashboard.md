---
name: ops-dashboard
source: content/features/ops-dashboard.md
tags:
- ops
- dashboard
- runner
- workflows
- scope-picker
- persistence
- sse
type: quickstart
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

## Quickstart

Start the dashboard from the CLI (runs enabled unless `--read-only`):

```bash
attune ops                 # http://127.0.0.1:8765
python -m attune.ops --read-only --port 9000
```

Build the app from Python (e.g. to embed or test it):

```python
from pathlib import Path

from attune.ops import build_config, create_app

config = build_config(Path("."), host="127.0.0.1", port=8765)
app = create_app(config)
print(type(app).__name__, "| runs allowed:", config.allow_run)
```
