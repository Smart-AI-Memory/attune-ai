---
type: warning
name: clusterfuzz-dockerfile-copies-to-src-repo-but-also-copies
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Clusterfuzz Dockerfile copies `.` to
  `$SRC/<repo>` but also copies individual files
  to `$SRC/` — new sibling files need one path or
  the other, not `$(dirname "$0")`

## Condition

`.clusterfuzzlite/Dockerfile` does `COPY . $SRC/attune-ai` and then `COPY .clusterfuzzlite/build.sh $SRC/build.sh` plus `COPY .clusterfuzzlite/fuzz_*.py $SRC/`

## Risk

Adding a new file like `requirements.txt` and referencing it via `$(dirname "$0")/requirements.txt` fails with "No such file or directory: /src/requirements.txt"

## Mitigation

1. Adding a new file like `requirements.txt` and referencing it via `$(dirname "$0")/requirements.txt` fails with "No such file or directory: /src/requirements.txt"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Clusterfuzz Dockerfile copies `.` to
  `$SRC/<repo>` but also copies individual files
  to `$SRC/` — new sibling files need one path or
  the other, not `$(dirname "$0")`
