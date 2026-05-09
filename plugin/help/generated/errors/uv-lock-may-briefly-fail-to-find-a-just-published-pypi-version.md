---
type: error
name: uv-lock-may-briefly-fail-to-find-a-just-published-pypi-version
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: `uv lock` may briefly fail to find a just-published
  PyPI version because the simple index lags the JSON
  API

## Signature

`uv lock` may briefly fail to find a just-published
  PyPI version because the simple index lags the JSON
  API

## Root Cause

within ~30 seconds of a successful PyPI publish, `curl https://pypi.org/pypi/<pkg>/<ver>/json` returns the new version but `uv lock --upgrade-package <pkg>` fails with "only <previous-version> is available. [...]  requirements are unsatisfiable." Both surfaces eventually converge, but the simple index (used by uv / pip) refreshes a few seconds behind the JSON API.

## Resolution

1. wait ~30s and rerun with `uv lock --upgrade-package <pkg> --refresh` — the `--refresh` flag bypasses uv's local cache of the simple index

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv lock` may briefly fail to find a just-published
  PyPI version because the simple index lags the JSON
  API
