---
type: faq
name: clusterfuzz-dockerfile-copies-to-src-repo-but-also-copies
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about clusterfuzz Dockerfile copies . to $SRC/<repo> but also copies individual files to $SRC/ — new sibling files need one path or the other, not $(dirname "$0")?

## Answer

`.clusterfuzzlite/Dockerfile` does `COPY . $SRC/attune-ai` and then `COPY .clusterfuzzlite/build.sh $SRC/build.sh` plus `COPY .clusterfuzzlite/fuzz_*.py $SRC/`. Result: `build.sh` runs from `/src/` (so `$(dirname "$0")` resolves to `/src/`, not `/src/attune-ai/.clusterfuzzlite/`).

```
.clusterfuzzlite/Dockerfile
```

## Related Topics
- **Error**: Detailed error: Clusterfuzz Dockerfile copies `.` to
  `$SRC/<repo>` but also copies individual files
  to `$SRC/` — new sibling files need one path or
  the other, not `$(dirname "$0")`
