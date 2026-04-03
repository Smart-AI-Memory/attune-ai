# Discord Post: A Knowledge Base That Maintains Itself

**Part 5 (final): The 5-phase pipeline that keeps 557
templates accurate**

This is the article the series has been building toward.
Code conventions as sources (Part 2), 11 template types
(Part 3), and context-aware delivery (Part 4) only work
if the system can detect when code changes and
regenerate automatically.

The 5-phase maintenance pipeline:

**1. Detect** — SHA-256 hash comparison. Each template
tracks its source file hash in a manifest. Changed hash
= stale template. No LLM calls, runs in seconds.

**2. Map** — One source file can produce many templates.
Pipeline identifies every affected template type.

**3. Regenerate** — Two modes:
- Immediate: standard API, fast, synchronous
- Batch: Anthropic Batch API, **50% cost savings**, async

Priority queue: low-confidence first, then high-usage,
then by age. The security audit reference (used daily)
regenerates before a comparison template nobody reads.

**4. Rebuild cross-links** — Seven deterministic rules
reconnect templates after regeneration. Error ↔ warning,
skill → tool, task → reference. Progressive depth chains
rebuild automatically.

**5. Validate** — Generators run in check mode to verify
sync. Also runs as a pre-commit hook.

The economics make it practical:
- Incremental (only stale templates, not all 557)
- Hash-based detection (no LLM calls to check)
- Batch-eligible (50% off for non-urgent updates)

Exposed as one MCP tool: `help_maintain(dry_run, batch)`

**What's next:** We're exploring `attune-help` — a lean
runtime package so any AI app can ship progressive depth
and "tell me more" without the full authoring toolkit.
Author with `attune-ai`, ship with `attune-help`.

Try it:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Say "check for stale docs" to see the pipeline in
dry-run mode.

Runs on your Claude subscription — no API key required.

Thanks for following the series. Star the repo if useful:
https://github.com/Smart-AI-Memory/attune-ai
