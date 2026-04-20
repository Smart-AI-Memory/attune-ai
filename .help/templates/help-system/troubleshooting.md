---
type: troubleshooting
feature: help-system
depth: troubleshooting
generated_at: 2026-04-20T01:18:17.465018+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Troubleshoot help system

## Before you start

The help system provides progressive-depth template lookup, audience adaptation, and template generation from source code. When it breaks, users get no help or malformed output.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Templates fail to load | Run `_parse_template_file()` on individual `.md` files to find YAML frontmatter errors |
| Progressive depth stuck at 0 | Check `lookup_raw()` metadata — depth should increment with repeated calls |
| Cross-links return 404 | Verify template IDs in `cross_links.json` exist using `_find_template_file()` |
| Precursor warnings empty | Test `precursor_warnings()` with known file extensions like `.py` or `.js` |
| Renderer crashes | Call each renderer function directly with a populated template |
| Feature generation fails | Check that `features.yaml` exists and contains valid feature definitions |

## Step-by-step diagnosis

1. **Reproduce with minimal code.**
   Create a standalone test that isolates the failure:
   ```python
   from attune_help.engine import HelpEngine
   from attune_help.storage import MemoryStorage

   engine = HelpEngine(storage=MemoryStorage(), renderer="plain")
   result = engine.lookup("your-failing-topic")
   ```

2. **Check template directory structure.**
   Verify the templates directory exists and contains valid markdown files:
   ```bash
   find packages/attune-help/src/attune_help/templates -name "*.md" | head -5
   python -c "from attune_help.templates import _parse_template_file; _parse_template_file('path/to/template.md')"
   ```

3. **Test progressive depth manually.**
   Progressive depth relies on session state. Call the same topic multiple times:
   ```python
   r1 = engine.lookup_raw("security-audit")
   r2 = engine.lookup_raw("security-audit")
   r3 = engine.lookup_raw("security-audit")
   print([r.metadata["depth_level"] for r in [r1, r2, r3]])  # Should be [0, 1, 2]
   ```

4. **Validate cross-links integrity.**
   Load the cross-links index and check for broken references:
   ```python
   import json
   from pathlib import Path
   from attune_help.templates import _find_template_file

   gen_dir = Path("packages/attune-help/src/attune_help/templates")
   links = json.loads((gen_dir / "cross_links.json").read_text())
   broken = [tid for tid in links.get("links", {}) if _find_template_file(tid, gen_dir) is None]
   ```

5. **Test each renderer separately.**
   Isolate renderer failures by testing each one individually:
   ```python
   from attune_help.transformers import render_claude_code, render_cli
   template = populate("con-progressive-depth", audience=AudienceProfile(), generated_dir=gen_dir)
   plain_output = template.body
   claude_output = render_claude_code(template)
   cli_output = render_cli(template)
   ```

## Common fixes

- **Fix malformed frontmatter.** Add missing required fields like `type`, `name`, or `tags` to template YAML headers.
- **Regenerate cross-links.** Run template generation to rebuild `cross_links.json` after adding or removing templates.
- **Clear progressive depth state.** Call `engine.storage.clear()` or use a fresh `MemoryStorage()` instance to reset session state.
- **Update feature manifest.** Run `scan_project()` and `proposals_to_manifest()` to refresh `features.yaml` when source files change.
- **Install missing dependencies.** The help system requires specific versions of YAML parsers and template engines — check `requirements.txt`.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
