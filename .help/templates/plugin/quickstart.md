---
type: quickstart
feature: plugin
depth: quickstart
generated_at: 2026-04-19T18:53:34.996941+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Quickstart: Add Claude Code hooks

Run Python formatting and help checks automatically in Claude Code.

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai && claude plugin install attune-ai@attune-ai
```

**Result:** Four hooks activate in Claude Code — Python auto-formatting, help freshness checks, error suggestions, and help maintenance.

## Test the hooks

**1. Create a Python file to trigger formatting:**

```python
# test.py
def hello(  ):
    print( "badly formatted" )
```

**2. Use Claude Code's Write tool to edit the file**

The `format_on_save` hook automatically reformats your Python code after any Write or Edit operation.

**3. Verify the formatting worked:**

```python
# test.py
def hello():
    print("badly formatted")
```

## What you activated

- **Auto-formatting**: Python files get formatted after Claude writes or edits them
- **Help freshness**: Session startup checks if help templates need updates
- **Error assistance**: Failed bash commands trigger help suggestions
- **Help maintenance**: Git commits update the `.help/` directory automatically

**Next:** Say **"/attune"** in Claude Code to see all available skills.
