---
name: sync-paradigm
source: scripts/generate_all.py
summary: The Sync Paradigm is a six-step pattern (Discover → Parse → Transform → Validate
  → Output → Verify) that all generators in the documentation stack follow to consistently
  produce, validate, and verify generated documentation from source code.
tags:
- architecture
- documentation
type: concept
---

# The Sync Paradigm

## Overview

The sync paradigm is a six-step pattern that every generator in the documentation stack follows to produce documentation from source code. The steps are: **Discover → Parse → Transform → Validate → Output → Verify**.

## Why It Exists

Applying a consistent pattern across all generators provides three key guarantees:

- **Consistency** — every generator behaves predictably, regardless of its source format.
- **Idempotency** — running a generator multiple times produces the same output.
- **Verifiability** — the `--check` mode can confirm that generated content matches its source without triggering a full regeneration.

## How It Works

Each generator executes the following steps in order:

1. **Discover** — Locate the relevant source files (for example, `SKILL.md` or `tool_schemas.py`).
2. **Parse** — Extract structured data from those source files.
3. **Transform** — Convert the extracted data into a typed template dataclass.
4. **Validate** — Check the dataclass against its expected schema.
5. **Output** — Render the validated data through a Jinja2 template and write the result to the `generated/` directory.
6. **Verify** — In `--check` mode, compare the rendered output against the files already on disk and report any drift.

## Example

To verify that all generated files are in sync with their sources, run:

```bash
python scripts/generate_all.py --check
```

This command runs the Verify step across all generators and confirms that all 498 templates match their current sources. No files are written; the command exits with a non-zero status if any drift is detected.

## Related Topics

*No related topics yet.*
