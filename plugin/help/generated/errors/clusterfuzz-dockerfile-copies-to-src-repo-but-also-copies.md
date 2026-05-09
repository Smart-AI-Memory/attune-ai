---
type: error
name: clusterfuzz-dockerfile-copies-to-src-repo-but-also-copies
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Clusterfuzz Dockerfile copies `.` to
  `$SRC/<repo>` but also copies individual files
  to `$SRC/` — new sibling files need one path or
  the other, not `$(dirname "$0")`

## Signature

)/requirements.txt` fails with

## Root Cause

`.clusterfuzzlite/Dockerfile` does `COPY . $SRC/attune-ai` and then `COPY .clusterfuzzlite/build.sh $SRC/build.sh` plus `COPY .clusterfuzzlite/fuzz_*.py $SRC/`. Result: `build.sh` runs from `/src/` (so `$(dirname "$0")` resolves to `/src/`, not `/src/attune-ai/.clusterfuzzlite/`). Adding a new file like `requirements.txt` and referencing it via `$(dirname "$0")/requirements.txt` fails with "No such file or directory: /src/requirements.txt". Two fixes: (a) add another `COPY` to the Dockerfile, or (b) use the in-repo path via `$SRC/attune-ai/.clusterfuzzlite/requirements.txt` — the whole repo is already staged via the first `COPY .`. Option (b) is less maintenance when adding more companion files over time.

## Resolution

1. Adding a new file like `requirements.txt` and referencing it via `$(dirname "$0")/requirements.txt` fails with "No such file or directory: /src/requirements.txt"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Clusterfuzz Dockerfile copies `.` to
  `$SRC/<repo>` but also copies individual files
  to `$SRC/` — new sibling files need one path or
  the other, not `$(dirname "$0")`
