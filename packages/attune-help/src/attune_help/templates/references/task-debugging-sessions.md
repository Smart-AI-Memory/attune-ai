---
type: reference
subtype: tabular
name: task-debugging-sessions
tags: [debugging, python, tools]
source: developer-guidance
---

# Debugging Sessions Reference

Complete reference for Python debugging tools, techniques,
and common gotchas.

## Built-in debugger (pdb)

Drop `breakpoint()` anywhere in your code to pause
execution. Python 3.7+ uses this instead of
`import pdb; pdb.set_trace()`.

### pdb commands

| Command | Short | What it does |
|---------|-------|-------------|
| `next` | `n` | Execute the next line (step over) |
| `step` | `s` | Step into the function call on this line |
| `continue` | `c` | Resume execution until next breakpoint |
| `return` | `r` | Continue until the current function returns |
| `print expr` | `p expr` | Print the value of an expression |
| `pretty-print` | `pp expr` | Pretty-print complex objects |
| `list` | `l` | Show source code around the current line |
| `longlist` | `ll` | Show the entire current function |
| `where` | `w` | Print the full stack trace |
| `up` | `u` | Move one frame up in the stack |
| `down` | `d` | Move one frame down in the stack |
| `break file:line` | `b` | Set a breakpoint at a specific location |
| `clear N` | `cl N` | Remove breakpoint number N |
| `condition N expr` | | Break at N only when expr is true |
| `commands N` | | Run commands automatically when breakpoint N hits |
| `quit` | `q` | Exit the debugger and abort the program |

### Conditional breakpoints

```python
# Break only when a specific condition is met
breakpoint()  # then in pdb:
# (Pdb) b process.py:45, len(data) > 100
```

## VSCode / debugpy setup

To debug Python in VSCode with full GUI support, add this
to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v", "--no-header"],
      "console": "integratedTerminal"
    },
    {
      "name": "Attach to Running Process",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5678 }
    }
  ]
}
```

To attach to a running script, add this to the code:

```python
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()  # pauses until VSCode connects
```

## Logging levels

| Level | Value | When to use |
|-------|-------|-------------|
| `DEBUG` | 10 | Detailed diagnostic info -- variable values, flow decisions |
| `INFO` | 20 | Confirmation that things are working as expected |
| `WARNING` | 30 | Something unexpected happened but the code still works |
| `ERROR` | 40 | Something failed -- a function couldn't complete |
| `CRITICAL` | 50 | The application itself may not be able to continue |

### Quick logging setup

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

logger.debug("Processing %d items", len(items))
logger.warning("Retrying request (attempt %d/3)", attempt)
logger.error("Failed to connect: %s", err)
```

## Traceback module

For programmatic access to stack traces:

```python
import traceback

try:
    risky_operation()
except Exception:
    # Print the traceback without crashing
    traceback.print_exc()

    # Or capture it as a string
    tb_str = traceback.format_exc()
    logger.error("Operation failed:\n%s", tb_str)
```

## Profiling tools

| Tool | What it measures | Command |
|------|-----------------|---------|
| `cProfile` | Function call time and count | `python -m cProfile -s cumulative script.py` |
| `line_profiler` | Time per line within a function | `kernprof -l -v script.py` |
| `memory_profiler` | Memory usage per line | `python -m memory_profiler script.py` |
| `py-spy` | Sampling profiler (no code changes) | `py-spy record -o profile.svg -- python script.py` |
| `snakeviz` | Interactive visualization of cProfile output | `snakeviz profile.prof` |
| `tracemalloc` | Track memory allocations (stdlib) | See example below |

### tracemalloc example

```python
import tracemalloc

tracemalloc.start()

# ... your code ...

snapshot = tracemalloc.take_snapshot()
top = snapshot.statistics("lineno")
for stat in top[:10]:
    print(stat)
```

## Debugging techniques

### Bisect debugging (git bisect)

Find the exact commit that introduced a bug:

```bash
git bisect start
git bisect bad                # HEAD is broken
git bisect good v1.0.0        # this tag was working
# Git checks out a midpoint -- test and mark:
git bisect good               # or: git bisect bad
# Repeat until Git identifies the first bad commit
git bisect reset              # return to original branch
```

Automate with a test script:

```bash
git bisect run pytest tests/test_auth.py::test_login -x
```

### Time-travel debugging

Record execution and replay it:

```bash
# Install
pip install pytrace

# Record
python -m pytrace record script.py

# Replay -- step forward and backward
python -m pytrace replay
```

Alternative: use `snoop` for automatic trace logging
without breakpoints:

```python
import snoop

@snoop
def process(data):
    result = transform(data)
    return result
```

### Memory profiling

Track down memory leaks:

```python
import objgraph

# Show the 10 most common object types
objgraph.show_most_common_types(limit=10)

# Show what's referencing a leaked object
objgraph.show_backrefs(
    objgraph.by_type("MyClass")[:3],
    filename="refs.png",
)
```

### sys.settrace

Low-level tracing for advanced debugging:

```python
import sys

def trace_calls(frame, event, arg):
    if event == "call":
        name = frame.f_code.co_name
        file = frame.f_code.co_filename
        print(f"CALL {name} in {file}:{frame.f_lineno}")
    return trace_calls

sys.settrace(trace_calls)
# ... your code runs with tracing ...
sys.settrace(None)
```

## Common Python gotchas

Bugs that look mysterious but have well-known causes:

| Gotcha | What happens | Why | Fix |
|--------|-------------|-----|-----|
| **Mutable default args** | Default list/dict is shared across calls | Default values are evaluated once at function definition | Use `None` as default, create inside the function |
| **Late binding closures** | All lambdas in a loop capture the same variable | Closures bind to names, not values | Add `x=x` default parameter to capture current value |
| **Import cycles** | `ImportError` or `AttributeError` at import time | Module A imports B which imports A | Restructure, or use lazy imports inside functions |
| **GIL contention** | Multithreaded CPU code runs slower than single-threaded | Global Interpreter Lock serializes CPU-bound threads | Use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` |
| **`is` vs `==`** | `a is b` is `False` even though `a == b` is `True` | `is` compares identity (memory address), not equality | Use `==` for value comparison; `is` only for `None` |
| **Silent `except: pass`** | Bugs vanish with no trace | Bare `except` catches and discards everything | Catch specific exceptions, always log |
| **Floating point math** | `0.1 + 0.2 != 0.3` | IEEE 754 representation is approximate | Use `math.isclose()` or `decimal.Decimal` |
| **String immutability in loops** | `s += char` in a loop is O(n^2) | Each `+=` creates a new string object | Collect in a list and `"".join()` at the end |
| **`__init__.py` shadows** | `import mypackage` gives wrong module | A directory at the repo root matches the package name | Remove or rename the shadow directory |
| **`datetime.utcnow()` is naive** | Timezone comparisons raise `TypeError` | `utcnow()` returns a naive datetime, not UTC-aware | Use `datetime.now(timezone.utc)` instead |

## Want to learn more?

- Say **"what are the debugging strategies?"** for the
  conceptual overview
- Say **"how do I debug a problem step by step?"** for the
  hands-on walkthrough
- Say **"something is broken and I don't know why"** for
  the quick triage guide
- Try **/fix-test** to auto-diagnose and fix failing tests
- Try **/bug-predict** to predict where bugs are most
  likely in your code
- Try **/code-quality** to find code smells before they
  become bugs
