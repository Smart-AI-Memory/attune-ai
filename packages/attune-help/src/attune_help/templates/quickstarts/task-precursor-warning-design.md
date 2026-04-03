---
type: quickstart
name: task-precursor-warning-design
tags: [precursor, warnings, help-system, patterns]
source: developer-guidance
---

# Quickstart: Add a proactive warning

Five steps to surface a warning before a developer hits
a problem.

## 1. Pick the mistake and its trigger file

Start from a mistake you have seen (or a Lessons Learned
entry). Work backward to the file being edited when it
happens.

| Mistake | Trigger file | Extension/name |
|---------|-------------|----------------|
| Secrets committed to git | `.env` | `.env` (both maps) |
| Stale dist/ artifacts | `pyproject.toml` | `.toml` + filename |
| Pre-commit stash conflict | Any `.py` file | `.py` extension |

## 2. Check if tags already exist

Look at the extension and filename maps in
`engine.py:precursor_warnings()`. If your trigger file
already maps to relevant tags, skip to step 3.

```python
# Already mapped:
".env": ["config", "secrets"]
".py":  ["python", "imports", "testing", "error-handling"]
```

If your file type is not mapped, add it:

```python
ext_map[".tf"] = ["infrastructure", "terraform"]
```

## 3. Write the warning template

Create a file in `templates/warnings/`:

```yaml
---
type: warning
name: your-warning-name
tags: [config, secrets]
source: developer-guidance
---

# Warning: Brief title

One or two sentences explaining the risk.

## What to do

- Actionable step 1
- Actionable step 2

## If it already happened

- Recovery step 1
- Recovery step 2
```

Make sure the `tags` in your frontmatter overlap with
the tags assigned by the extension or filename map.

## 4. Regenerate cross-links

If you added a new template, regenerate
`cross_links.json` so the `tag_index` includes your
warning:

```bash
python -m attune_help.generate
```

## 5. Test it

```python
from attune_help import HelpEngine

engine = HelpEngine()
warnings = engine.precursor_warnings(".env")
for w in warnings:
    print(w)
```

Verify your warning appears. If it does not, check
that your template tags overlap with the file's
mapped tags.

## Done

Your warning now surfaces automatically when a
developer edits a file matching your trigger.

## Want to learn more?

- Say **"what are precursor warnings?"** for the full
  design principles and trigger chain
- Say **"walk me through adding a warning"** for the
  detailed step-by-step with a complete example
- Say **"show me all the mappings"** for every file-
  to-tag mapping and scoring rule

## Related Topics

- **Concept**: Precursor warning design -- why proactive
  warnings beat reactive errors
- **Task**: Precursor warning design -- full step-by-step
  guide with a `.env` secrets example
- **Reference**: Precursor warning design -- all file
  mappings, tag conventions, prefixes, and scoring rules
