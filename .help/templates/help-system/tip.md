---
type: tip
feature: help-system
depth: tip
generated_at: 2026-04-20T01:19:03.486766+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Use precursor warnings to catch help system issues early

Pass your filenames through `get_precursor_warnings()` before users encounter broken templates or dangling cross-links. This function analyzes file extensions and patterns to surface relevant help templates — and will fail gracefully when those templates have problems.

Testing with real filenames exposes template loading errors, missing cross-link targets, and renderer failures that silent validation might miss. You catch the breakage in development instead of when users ask for help and get garbage.

The tradeoff: precursor testing adds a few seconds to your test suite, but it's still faster than debugging user reports of "the help system returned nothing."
