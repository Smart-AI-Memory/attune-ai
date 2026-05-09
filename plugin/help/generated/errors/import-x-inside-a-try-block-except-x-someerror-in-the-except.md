---
type: error
name: import-x-inside-a-try-block-except-x-someerror-in-the-except
confidence: Verified
tags: [ci, imports, git, packaging]
source: .claude/CLAUDE.md
---

# Error: `import X` inside a `try` block + `except
  X.SomeError` in the except clause crashes with
  `UnboundLocalError` when the import fails

## Signature

ImportError

## Root Cause

hit in `.clusterfuzzlite/fuzz_config_parsing.py` where the fuzz target did ```python try:     import yaml     yaml.safe_load(raw) except (yaml.YAMLError, ValueError, TypeError):     pass ``` Python evaluates the except expression only when an exception is raised — so if `import yaml` raises `ImportError`, the except clause is evaluated with `yaml` never bound, producing `UnboundLocalError: cannot access local variable 'yaml'` and crashing libFuzzer with "fuzz target exited". This matters any time an optional dep could be missing at runtime (fuzz containers built with `pip install --no-deps`, minimal CI environments, etc.). Fix pattern: move the import to module scope behind an availability guard and bind the exception class to a name that is always defined: ```python try:     import yaml     _YAML_AVAILABLE = True     _YAML_ERROR: type[Exception] = yaml.YAMLError except ImportError:     _YAML_AVAILABLE = False     _YAML_ERROR = ValueError  # placeholder ``` Then the hot path checks `_YAML_AVAILABLE` before calling `yaml.safe_load`, and the except references `_YAML_ERROR` which is bound in both branches. Scope: fuzz targets, optional-dep SDK adapters, any code where the exception type comes from a potentially-missing package.

## Resolution

1. hit in `.clusterfuzzlite/fuzz_config_parsing.py` where the fuzz target did ```python try:     import yaml     yaml.safe_load(raw) except (yaml.YAMLError, ValueError, TypeError):     pass ``` Python evaluates the except expression only when an exception is raised — so if `import yaml` raises `ImportError`, the except clause is evaluated with `yaml` never bound, producing `UnboundLocalError: cannot access local variable 'yaml'` and crashing libFuzzer with "fuzz target exited". This matters any time an optional dep could be missing at runtime (fuzz containers built with `pip install --no-deps`, minimal CI environments, etc.). Fix pattern: move the import to module scope behind an availability guard and bind the exception class to a name that is always defined: ```python try:     import yaml     _YAML_AVAILABLE = True     _YAML_ERROR: type[Exception] = yaml.YAMLError except ImportError:     _YAML_AVAILABLE = False     _YAML_ERROR = ValueError  # placeholder ``` Then the hot path checks `_YAML_AVAILABLE` before calling `yaml.safe_load`, and the except references `_YAML_ERROR` which is bound in both branches

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `import X` inside a `try` block + `except
  X.SomeError` in the except clause crashes with
  `UnboundLocalError` when the import fails
- Tip: Best practice: `import X` inside a `try` block + `except
  X.SomeError` in the except clause crashes with
  `UnboundLocalError` when the import fails
