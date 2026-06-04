# rag-code-gen cleanup — punch list

**Status:** draft
**Created:** 2026-05-16
**Origin:** 23-finding code-review pass on
`src/attune/workflows/rag_code_gen.py`
(4 security, 10 quality, 5 performance, 8 architecture).

## What shipped (PR referencing this doc)

Four security findings + three highest-severity quality findings,
all with regression tests in
`tests/unit/workflows/test_rag_code_gen_security.py`:

- **Sec-1** sentinel-defense clause echoed in `_SYSTEM_PROMPT`
  (defense in depth over attune-rag 0.1.5's user-prompt-level
  sentinel wrapping).
- **Sec-2** `_validate_file_path(cwd)` blocks system-dir targets;
  `allowed_dir` deliberately omitted so legitimate cross-tree use
  (e.g. `path="/tmp/scope"` from CI) keeps working. System-dir
  blocklist covers the primary exfil vector.
- **Sec-3** `model` kwarg allowlisted against `MODEL_REGISTRY`
  (cost-DoS + opaque SDK failure mitigation).
- **Qual-1** `int(kwargs.get('k', 3))` wrapped in try/except;
  returns structured `WorkflowResult` on bad input.
- **Qual-2** `from attune_rag.provenance import
  format_citations_markdown` hoisted to module scope with
  `ImportError` guard — failure surfaces at module load, not
  after the agent has billed API cost.
- **Qual-3** `pipeline.run()` exception catch broadened from
  `RuntimeError` only to
  `(RuntimeError, ConnectionError, TimeoutError, ValueError)`
  so retrieval-layer failures no longer mis-attribute as Agent
  SDK errors.

Drive-by fixes to integration tests that were already broken on
`origin/main` (stale post-#401 cwd Path type, stale post-#357
"Agent SDK error" → "Agent SDK failure" wording).

## Deferred to this spec

### Security finding #4 — citation URL encoding

**File:** `attune-rag/src/attune_rag/provenance.py:75-105`
**Issue:** `format_citations_markdown` interpolates
`source.template_path` directly into both link text and href:
`f"[{path}]({trimmed}/{path})"`. No URL-encoding of path
segments. If `template_path` ever contains markdown specials
(`)`, `[`, etc.) or scheme-relative content, the rendered
markdown link breaks or becomes a phishing vector.

**Current exposure:** Low. `template_path` comes from
`entry.path` in the corpus index, which is built from
attune-help's template tree. Trusted source today; not user-
controlled.

**Action required:**

- Patch `format_citations_markdown` in attune-rag to
  `urllib.parse.quote(path, safe="/")` the href segment.
- Bump attune-rag minimum version cap in attune-ai's
  `[rag]` extra to the patched release.
- Add a regression test in attune-rag exercising the encoding.

Cross-repo work — needs a separate spec under attune-rag.

### Quality findings 4–10 (lower stakes)

All seven from the code-review pass that didn't make this
PR. None are crashes; they're hygiene.

| Line | Finding | Severity |
|------|---------|----------|
| 313 | `_record_feedback` catches `Exception` without narrowing | LOW |
| 125 | `tier_map` retrieve-stage labeled `CHEAP` but is zero-LLM (cosmetic) | LOW |
| 140 | `legacy_cwd = kwargs.get("cwd")` shadows builtin `cwd` shadow concern in static analyzers | LOW |
| 111 | `_pipeline: Any` could be properly typed once `attune_rag.RagPipeline` is a stable public class | LOW |
| 163 | `max_turns = _DEPTH_MAX_TURNS.get(depth, 12)` silently falls back on bad `depth` | LOW |
| 164 | `started_at = datetime.now()` should be timezone-aware per the project's UTC convention | LOW |
| 126 | `import warnings as _warnings` aliased inside function with stale rationale comment | LOW |

Bundle these into a single `chore(rag-code-gen): low-priority
hygiene fixes` PR when convenient.

## Out of scope (separate specs)

### Architecture findings (5 total)

Patterns shared across multiple SDK-native workflows. Fixing
piecemeal in one file just creates drift.

- Mixin over-inheritance: `BaseWorkflow` mixin surface is
  larger than any single workflow uses.
- Cross-package feedback writes: `_record_feedback` writes
  into `attune.help.feedback` from a workflow — coupling
  violation.
- Hardcoded `_DEPTH_MAX_TURNS` per workflow file instead of
  centralised depth policy.
- Inconsistent budget / turns / model selection across the
  ~15 SDK-native workflows.
- Citation rendering coupled to a specific corpus base URL
  (`_CITATION_BASE_URL`) — should be per-corpus config.

→ Capture as `docs/specs/sdk-workflow-isp-cleanup/` (separate
spec, separate session, multi-PR).

### Performance findings (5 total)

Micro-optimisations on a workflow that spends 99% of its
wall-clock in LLM calls. Deferred indefinitely.

## Verification

Run after each cluster:

```bash
PYTHONPATH=$(pwd)/src .venv/bin/python -m pytest \
  tests/unit/workflows/test_rag_code_gen* \
  tests/unit/workflows/test_agent_sdk_adapter.py \
  tests/unit/rag/ \
  tests/integration/rag/ \
  -m "" -o addopts=
```

Current baseline: 130 passed, 0 failed.
