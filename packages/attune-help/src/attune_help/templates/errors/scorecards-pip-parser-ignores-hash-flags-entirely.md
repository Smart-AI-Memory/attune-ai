---
type: error
name: scorecards-pip-parser-ignores-hash-flags-entirely
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: Scorecard's pip parser ignores `--hash` flags entirely

## Signature

Scorecard's pip parser ignores `--hash` flags entirely

## Root Cause

Even single-line `pip3 install 'pkg==1.0' --hash=sha256:abc...` is flagged as "not pinned by hash". Scorecard's `PinnedDependenciesID` check does not recognize pip's `--hash` CLI flag — it only recognizes `--require-hashes` with a requirements file, or possibly other formats. For ClusterFuzzLite `build.sh`, dismiss as false positive since the deps ARE hash-pinned. The alerts recur on each Scorecard re-scan so expect to re-dismiss.

## Resolution

1. Even single-line `pip3 install 'pkg==1.0' --hash=sha256:abc...` is flagged as "not pinned by hash"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
