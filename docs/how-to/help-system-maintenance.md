---
description: How the .help/ knowledge base stays fresh — weekly PR automation, session-start drift nudges, completeness and coverage gates, local telemetry, and a golden-query benchmark.
---

# Help System Maintenance

*Drift-bounded maintenance for the `.help/` knowledge
base — Claude Code and CLI users both pull from it, so
freshness is a first-class concern.*

---

## Overview

The `.help/` directory is authored once as templates and
rendered at runtime via `attune-help`. Source code
changes faster than docs, so attune-ai ships five
mechanisms that keep the knowledge base bounded against
drift — none of them require manual babysitting:

| Mechanism | What it does | When it runs |
|---|---|---|
| Weekly freshness PR | Regenerates stale features and opens a PR if the diff is non-empty | Sunday 12:00 UTC cron + manual dispatch |
| SessionStart hook | One-line drift summary on Claude Code session open | Every session start |
| Completeness check | Flags features with fewer than 11 template kinds or orphan directories | Locally, in CI |
| Coverage check | Every registered workflow must have a manifest entry or allowlist | Locally, in CI |
| Golden-query benchmark | 52 queries pin `resolve_topic()` P@1 against difficulty buckets | `pytest` run or on-demand |

Local telemetry (`help_tracker`) writes a JSONL of every
`help_lookup` MCP call, giving you usage data to drive
corpus investment.

---

## Weekly freshness workflow

```bash
# Manually trigger the cron workflow:
gh workflow run help-freshness.yml --ref main
```

`.github/workflows/help-freshness.yml` runs every Sunday
at 12:00 UTC (and on manual dispatch). It:

1. Lists stale features via
   `scripts/list_stale_help_features.py` (the
   hash-based staleness check).
2. Regenerates them with `attune-author generate
   <feature> --help-dir .help --all-kinds` (all 11
   template kinds, not just the 3-depth core).
3. Opens a PR if the diff is non-empty.

Requires `ANTHROPIC_API_KEY` as a repo secret for the
LLM-polish pass; without it, the workflow falls back to
raw Jinja2 drafts.

---

## SessionStart nudge

`src/attune/hooks/scripts/help_freshness_nudge.py` runs
at Claude Code session start. It's silent when the
`.help/` tree is clean and emits a one-line summary on
drift:

```text
attune: 5 help template(s) may be stale
  types: con, ref, tas, tip
  run: /coach maintain (or ATTUNE_DOCS_AUTOREGEN=1)
```

The hook always exits 0 — the session starts normally
either way. Installed via `.claude/settings.json` under
`hooks.SessionStart`.

---

## Completeness + coverage checks

Two scripts that complement the hash-based
staleness check with structural checks:

```bash
# Enforce: every manifest feature has all 11 template kinds,
# no orphan directories outside the manifest.
python scripts/check_help_completeness.py

# Enforce: every workflow registered by list_workflows() has a
# manifest entry, alias, or KNOWN_GAPS allowlist.
python scripts/check_help_coverage.py
```

Both exit 0 on clean, 1 on violations. Run them
locally before committing manifest or workflow-registry
changes; both are gated by CI pre-commit. Output is
human-readable by default; `--format=json` is available
for CI parsing.

---

## Local telemetry

`src/attune/telemetry/help_tracker.py` records every
`help_lookup` MCP call to
`~/.attune/telemetry/help.jsonl`. Writes are gated by
an autouse conftest fixture
(`ATTUNE_HELP_TELEMETRY=0` during tests) so test runs
never pollute the real log.

```bash
# Summarize recent lookups:
python scripts/summarize_help_telemetry.py

# Example output:
# Top topics:     security-audit (42), code-review (31), ...
# Miss rate:      6.3%
# Top missed:     "static analysis" (5), "lint rules" (3), ...
```

Top-missed topics are the corpus-investment signal —
they're the queries users typed that didn't resolve. Use
them to seed new golden queries or manifest tag
additions.

---

## Golden-query benchmark

```bash
pytest tests/unit/help/test_golden_queries.py -v
```

The fixture at
`tests/unit/help/fixtures/golden_queries.yaml` contains
52 hand-crafted queries across three difficulty buckets:

| Bucket | Count | Description |
|---|---|---|
| easy | 22 | Feature-name synonyms — always expected to pass |
| medium | 26 | Paraphrases + industry terminology — may need tag or description edits |
| hard | 4 | Shared-tag collisions (e.g. `"review"` matches both `code-quality` and `deep-review`) — documented ceilings, run as `pytest.xfail` |

`resolve_topic()` in `attune-help` slug-normalizes
spaces and underscores to hyphens at the tag-matching
step, so `"race condition"` matches the
`race-condition` tag without requiring a separate
fixture entry.

When expanding the fixture, dry-run candidates through
`resolve_topic()` first — mislabeled difficulty causes
"unexpectedly hard" medium queries that hide real gaps.

---

## Related reference

- [`rag/index.md`](../rag/index.md) — RAG-grounded
  retrieval that runs on top of the `.help/` corpus.
- [`attune-author` repository](https://github.com/Smart-AI-Memory/attune-author)
  — authoring CLI + staleness detection + LLM polish.
- [`attune-help` repository](https://github.com/Smart-AI-Memory/attune-help)
  — template runtime, `resolve_topic()`, progressive
  depth.
