# Tasks: Bulletin Curator

> XML-enhanced execution prompts per
> [`.claude/rules/attune/xml-enhanced-prompts.md`](../../../.claude/rules/attune/xml-enhanced-prompts.md).
> Companion to [`requirements.md`](requirements.md) and
> [`design.md`](design.md).
**Status:** approved
**Last updated:** 2026-05-26
**Total estimate:** ~10h across 4 phases. Each phase ships
independently; CLI/dashboard surfaces (Phase 3) can ship after
the headless API (Phase 2) and use the cached fixtures from
Phase 1.

---

## Phase 1 — Source readers + cache scaffolding

### Task 1.1 — Source dataclasses + base contract

```xml
<task id="1.1" name="source-dataclasses">
  <objective>
    Define SourceSummary and SourceItem dataclasses and the
    SourceReader Protocol. These are the shared types every
    source reader returns and the curator orchestrator
    consumes.
  </objective>

  <context>
    <related-spec path="docs/specs/bulletin-curator/design.md">
      "Source reader contract" section defines field shapes.
    </related-spec>
    <existing-pattern path="src/attune/bulletin/protocol.py">
      Mirror this file's dataclass + Protocol layout. Frozen
      dataclass + Protocol class + module-level type aliases.
    </existing-pattern>
  </context>

  <files-to-create>
    <file path="src/attune/curator/__init__.py">
      Re-exports: SourceSummary, SourceItem, CuratorResult,
      CuratorItem, run_curator.
    </file>
    <file path="src/attune/curator/result.py">
      SourceSummary, SourceItem, CuratorResult, CuratorItem
      dataclasses. All frozen. CuratorResult has summary:str,
      items:list[CuratorItem], sources_consulted:list[str],
      cost_usd:float, cached_at:datetime, model:str.
      CuratorItem mirrors the JSON schema in design.md.
    </file>
    <file path="src/attune/curator/sources/__init__.py">
      Exports SourceReader Protocol.
    </file>
  </files-to-create>

  <validation>
    <check>`from attune.curator import SourceSummary, CuratorResult` succeeds</check>
    <check>All dataclasses are frozen (mutation raises FrozenInstanceError)</check>
    <check>`mypy src/attune/curator/result.py` clean</check>
  </validation>
</task>
```

### Task 1.2 — Bulletin source reader

```xml
<task id="1.2" name="source-bulletin">
  <objective>
    Read active + archived bulletin entries and produce
    SourceItems. Active entries from FileBulletinBackend;
    archived entries from <attune_home>/bulletin/archive/*.jsonl
    filtered by `since`.
  </objective>

  <context>
    <existing-code path="src/attune/bulletin/file_backend.py">
      FileBulletinBackend.read_active() exists.
      read_archive(since=...) does NOT yet exist — add it.
    </existing-code>
    <design-ref>design.md "Per-source details" table, bulletin row.</design-ref>
  </context>

  <files-to-modify>
    <file path="src/attune/bulletin/file_backend.py">
      <change location="end of FileBulletinBackend class">
        Add `read_archive(self, since: datetime) -> list[BulletinEntry]`
        that walks `archive/*.jsonl` files whose filename date is
        >= since.date() and returns concatenated entries. Reuse
        the existing `_iter_entries` helper.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="src/attune/curator/sources/bulletin.py">
      def read(*, project_root, since=None) -> SourceSummary.
      Maps active entries to SourceItem with metadata={
        "kind": "active", "actor_kind": entry.actor_kind,
        "heartbeat_age_s": str(int(now - entry.last_heartbeat))
      }. Archived entries get kind=archived + terminal_status.
      state_hash is sha256 of all entry run_ids + heartbeats.
    </file>
    <file path="tests/unit/curator/test_source_bulletin.py">
      Fixture: tmp_path with seeded bulletin entries (3 active,
      2 archived from yesterday). Assert SourceItem count, that
      stale heartbeats appear in metadata, that links resolve
      to /runs/<id>/view URLs.
    </file>
  </files-to-create>

  <validation>
    <check>Empty bulletin returns SourceSummary with items=[]</check>
    <check>state_hash is stable across calls when bulletin unchanged</check>
    <check>state_hash changes when a heartbeat is appended</check>
    <check>Archive reader respects since= cutoff (older entries dropped)</check>
  </validation>

  <risks>
    <risk severity="low">Archive files don't exist until rotation fires. Reader must tolerate missing archive/ dir.</risk>
  </risks>
</task>
```

### Task 1.3 — Specs source reader

```xml
<task id="1.3" name="source-specs">
  <objective>
    Read spec status across docs/specs/ + completion-candidate
    signals. Each spec produces one SourceItem.
  </objective>

  <context>
    <existing-code path="src/attune/ops/data.py">
      list_specs() exists — returns spec metadata. Reuse it.
    </existing-code>
    <existing-code path="src/attune/ops/completion_candidates.py">
      compute_candidates() identifies specs that look ready
      to close. Reuse its output.
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/curator/sources/specs.py">
      def read(*, project_root, since=None) -> SourceSummary.
      For each spec: item_id="spec:<slug>", title=spec name,
      detail=first paragraph of requirements.md (≤500 chars),
      link=/specs/<slug>, metadata={"status": ..., "age_days": ...,
      "is_completion_candidate": "true|false"}.
    </file>
    <file path="tests/unit/curator/test_source_specs.py">
      Build a synthetic docs/specs/ tree in tmp_path with 3
      specs. Assert items count, status field, link shape.
    </file>
  </files-to-create>

  <validation>
    <check>Status field reflects each spec's actual status</check>
    <check>Completion-candidate flag fires for at least one fixture spec</check>
    <check>Links resolve to /specs/<slug> shape</check>
  </validation>
</task>
```

### Task 1.4 — Discovery-sweep + telemetry + recommendations readers

```xml
<task id="1.4" name="source-sweep-telemetry-rec">
  <objective>
    Three more readers, each a thin wrapper over existing data
    sources. Keep them simple — they all follow the same
    SourceReader contract.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/discovery_sweep/">
      Sweep results stored at <attune_home>/ops/sweep-results/.
      Buckets: queue, questions, rejected.
    </existing-code>
    <existing-code path="src/attune/telemetry/">
      usage.jsonl + anomaly helpers.
    </existing-code>
    <existing-code path="src/attune/ops/data.py">
      Recent runs + recommendations are listable.
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/curator/sources/sweep.py">
      Read queue + questions buckets only (rejected excluded).
      One item per finding. metadata.bucket distinguishes.
    </file>
    <file path="src/attune/curator/sources/telemetry.py">
      Detect cost spikes (>2σ over 7d mean per-workflow) and
      4xx/5xx errors in the last hour. Pure heuristics.
    </file>
    <file path="src/attune/curator/sources/recommendations.py">
      Pending ATTUNE_REC cards on runs from the last 24h.
      Read the same JSON the /api/runs endpoint exposes.
    </file>
    <file path="tests/unit/curator/test_source_sweep.py" />
    <file path="tests/unit/curator/test_source_telemetry.py" />
    <file path="tests/unit/curator/test_source_recommendations.py" />
  </files-to-create>

  <validation>
    <check>Each reader returns empty SourceSummary on missing data</check>
    <check>state_hash is deterministic across calls with identical input</check>
    <check>Telemetry reader caps items at 10 (don't flood the prompt)</check>
  </validation>
</task>
```

### Task 1.5 — git_state reader + cache scaffolding

```xml
<task id="1.5" name="source-git-and-cache">
  <objective>
    Last source reader (git state) + the CuratorCache
    implementation.
  </objective>

  <context>
    <design-ref>design.md "Cache layer" section.</design-ref>
    <safety-note>
      git_state.py uses subprocess. Use shlex / argv-list form
      to avoid shell injection. Cap stdout reads at 1MB.
    </safety-note>
  </context>

  <files-to-create>
    <file path="src/attune/curator/sources/git_state.py">
      Three signals: diverged-from-main (>3 days behind),
      uncommitted files (>10), untracked secrets-shaped files
      (filename pattern match per existing CLAUDE.md lesson).
      Each signal becomes its own SourceItem.
    </file>
    <file path="src/attune/curator/cache.py">
      CuratorCache class per design.md. ttl_seconds default 300.
      Lazy eviction on read. Serialization: JSON, one file
      per cache key under <attune_home>/curator-cache/.
    </file>
    <file path="tests/unit/curator/test_source_git_state.py" />
    <file path="tests/unit/curator/test_cache.py">
      Fixtures: tmp_path cache root. Assert TTL respected,
      key collision detection, eviction sweep.
    </file>
  </files-to-create>

  <validation>
    <check>git_state reader tolerates not-a-git-repo (returns empty)</check>
    <check>Cache hit returns identical CuratorResult bytes</check>
    <check>Cache miss after TTL elapses</check>
    <check>force_refresh=True bypasses cache</check>
  </validation>

  <risks>
    <risk severity="medium">subprocess.run can hang on a locked git repo. Use timeout=5s, treat timeout as "no signal" not error.</risk>
  </risks>
</task>
```

---

## Phase 2 — Agent invocation + structured output

**Status: done (2026-06-05).** Implemented `prompt.py`, `schema.py`,
and `core.py` (`run_curator`) with raw-`anthropic` forced tool-use.
129 curator tests pass; new Phase 2 modules at 96% branch coverage.
Design deviations (agent-SDK → raw `anthropic`, model `4-6`, advisory
budget) recorded in [`decisions.md`](decisions.md) D1–D4.

### Task 2.1 — Curator system prompt + output schema

```xml
<task id="2.1" name="prompt-and-schema">
  <objective>
    Static system prompt template + JSON schema for forced
    tool-use output.
  </objective>

  <context>
    <design-ref>design.md "System prompt" + "Output schema" sections — copy verbatim into the module-level constants.</design-ref>
    <lesson>
      CLAUDE.md "Forced Anthropic tool-use is the cleanest path
      to guaranteed-schema JSON" — use tool_choice={"type": "tool", "name": "emit_curation"}.
    </lesson>
    <lesson>
      CLAUDE.md "Citation-forced prompting" + "prompt-injection
      resistance" — both clauses must appear in the prompt.
    </lesson>
  </context>

  <files-to-create>
    <file path="src/attune/curator/prompt.py">
      _CURATOR_SYSTEM_PROMPT: str (the full template).
      build_curator_prompt(summaries, max_items) -> str
      that injects per-source <source>...</source> blocks.
      Each block renders SourceItem.item_id/title/detail/link/
      metadata as a compact bullet list, max 50 rows per
      source, with a "...N more" marker on truncation.
    </file>
    <file path="src/attune/curator/schema.py">
      _CURATION_SCHEMA: dict (the JSON schema verbatim from design.md).
      output_schema(max_items) -> dict that returns the schema
      with the items.maxItems set dynamically.
    </file>
  </files-to-create>

  <validation>
    <check>build_curator_prompt() with empty summaries produces a valid prompt (no template errors)</check>
    <check>build_curator_prompt() truncates per-source blocks at 50 items</check>
    <check>output_schema(5) returns a schema whose items.maxItems == 5</check>
  </validation>
</task>
```

### Task 2.2 — run_curator orchestrator

```xml
<task id="2.2" name="run-curator">
  <objective>
    The public API. Orchestrates source reads, cache lookup,
    SDK invocation, and result validation.
  </objective>

  <context>
    <design-ref>design.md "Agent invocation" section — the async pseudocode is the spec for this function.</design-ref>
    <existing-pattern path="src/attune/workflows/code_review.py">
      Mirror this file's claude_agent_sdk.query() invocation
      pattern. Single-agent (no subagents). Use
      resolve_cwd_for_path(project_root) per the existing lesson.
    </existing-pattern>
  </context>

  <files-to-create>
    <file path="src/attune/curator/core.py">
      run_curator(...) async function.
      _read_all_sources(project_root) -> list[SourceSummary]
        — gather() across all readers, swallow per-source
        exceptions (log + return empty SourceSummary).
      _query_opus(prompt, output_schema, max_budget_usd)
        — claude_agent_sdk.query() with forced tool-use.
        Returns CuratorResult.
      _validate_sources(result, summaries) -> CuratorResult
        — drops items citing unknown item_ids; logs the drop.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/curator/__init__.py">
      <change location="exports">
        Re-export run_curator.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>run_curator with bulletin=None and an injected fake _query_opus returns a CuratorResult</check>
    <check>Per-source exceptions don't crash the run (one reader raises, others succeed)</check>
    <check>Items citing unknown item_ids are dropped + logged</check>
    <check>Cache hit returns without invoking _query_opus</check>
  </validation>

  <risks>
    <risk severity="medium">claude_agent_sdk dependency on Opus model availability. Test with mocked SDK; live test in Phase 4.</risk>
  </risks>
</task>
```

### Task 2.3 — Unit tests against fixtures

```xml
<task id="2.3" name="orchestrator-tests">
  <objective>
    Deterministic tests against fixtured SourceSummaries +
    mocked SDK. Covers the happy path, the per-source-failure
    path, the cache path, the validation-drop path.
  </objective>

  <context>
    <existing-pattern path="tests/unit/workflows/test_agent_sdk_adapter.py">
      Mock claude_agent_sdk.query() via monkeypatch — build
      a real ResultMessage + AssistantMessage(s) so isinstance
      checks pass.
    </existing-pattern>
  </context>

  <files-to-create>
    <file path="tests/unit/curator/test_run_curator.py">
      Fixtures:
      - _fake_summaries(): pre-built SourceSummary list with
        3 known item_ids per source
      - _fake_sdk_result(items=...): builds AssistantMessage
        + ResultMessage that emits the curator tool call
      Tests:
      - happy path: 5 items returned, all source citations valid
      - source failure: bulletin reader raises, others
        succeed, run returns 4-source result with empty
        bulletin block
      - validation drop: LLM returns an item citing
        "spec:nonexistent" — orchestrator drops it
      - cache hit: second call with same summaries skips SDK
      - cache miss after TTL
      - force_refresh bypasses cache
      - budget cap propagation: max_budget_usd=0.10 reaches SDK options
    </file>
  </files-to-create>

  <validation>
    <check>All tests pass under `pytest -p no:xdist`</check>
    <check>No real network or LLM calls (verified via the existing httpx-block fixture)</check>
  </validation>
</task>
```

---

## Phase 3 — Dashboard `/curator` + CLI

**Phase 3 done (2026-06-05).**

- **Task 3.1** — `GET /curator` route + `curator.html` template + CSS +
  `POST /curator/{answer,dismiss}` + 6 route tests, wired into
  `server.py` (router + "Briefing" nav). Two v1 deferrals in
  [`decisions.md`](decisions.md) D5–D6.
- **Task 3.2** — `attune curator` CLI (`--refresh` / `--json` /
  `--max-items`) in `cli_commands/curator.py`, dispatched from
  `cli_minimal.py`; 6 CLI tests.
- **Task 3.3** — bulletin-strip "View briefing" cross-link on the
  Workflows page (`workflows.html` + `.bulletin-strip-link` CSS).

Task 4.1 (live verification + prompt iteration) is the remaining
phase — a manual review cycle, run when desired.

### Task 3.1 — Dashboard route + template

```xml
<task id="3.1" name="curator-route-and-template">
  <objective>
    GET /curator endpoint that renders the executive summary,
    item cards, and AskUserQuestion forms.
  </objective>

  <context>
    <design-ref>design.md "Dashboard surface" section.</design-ref>
    <existing-pattern path="src/attune/ops/routes/bulletin.py">
      Use the same route registration shape. Inject Config via
      request.app.state.config.
    </existing-pattern>
    <existing-pattern path="src/attune/ops/templates/workflows.html">
      Match the dashboard's existing card + chip CSS conventions.
    </existing-pattern>
  </context>

  <files-to-create>
    <file path="src/attune/ops/routes/curator.py">
      GET /curator → render curator.html
      POST /curator/answer → route the user's choice (writes
        spec status via existing setter when item.suggested_action
        invokes that path)
      POST /curator/dismiss → write to
        <attune_home>/curator/dismissals.json
    </file>
    <file path="src/attune/ops/templates/curator.html">
      Hero block (summary with inline source chips) +
      cards grid + footer (refresh, sources, cost).
    </file>
    <file path="tests/unit/ops/test_curator_route.py">
      TestClient against create_app with a fixture that
      injects a pre-built CuratorResult. Assert HTML content,
      POST /answer side effect, POST /dismiss writes the file.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/ops/server.py">
      <change location="include_router calls">
        Add curator_routes.router include.
      </change>
    </file>
    <file path="src/attune/ops/static/css/main.css">
      <change location="end of file">
        Curator-specific styles: .curator-summary,
        .curator-card, severity color stripes,
        .curator-question-form layout.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>GET /curator returns 200 + HTML containing the summary text</check>
    <check>POST /curator/answer with a "Mark complete?" item updates the spec status via the existing setter</check>
    <check>POST /curator/dismiss persists to dismissals.json</check>
    <check>Subsequent GET /curator filters out dismissed item_ids</check>
  </validation>
</task>
```

### Task 3.2 — CLI subcommand

```xml
<task id="3.2" name="cli-curator">
  <objective>
    `attune curator` subcommand. Same CuratorResult, terminal-
    rendered.
  </objective>

  <context>
    <existing-pattern path="src/attune/cli_minimal.py">
      Subcommand dispatch via _SUBCOMMAND_DISPATCH. Add a new
      entry. Use rich's Console for colored output where present.
    </existing-pattern>
  </context>

  <files-to-modify>
    <file path="src/attune/cli_minimal.py">
      <change location="_SUBCOMMAND_DISPATCH">
        Add curator → cmd_curator dispatch entry.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="src/attune/cli_commands/curator.py">
      cmd_curator(argv) → calls run_curator + renders.
      Flags: --refresh (force), --json (machine-readable),
      --max-items N.
    </file>
    <file path="tests/unit/cli_commands/test_curator.py">
      Use capsys to capture output. Inject a fake run_curator
      via monkeypatch.
    </file>
  </files-to-create>

  <validation>
    <check>`attune curator --json | jq .summary` works</check>
    <check>`attune curator` renders summary + items with severity colors</check>
    <check>`attune curator --refresh` bypasses cache (test via spy on cache.get)</check>
  </validation>
</task>
```

### Task 3.3 — Bulletin strip "View briefing" cross-link

```xml
<task id="3.3" name="bulletin-curator-crosslink">
  <objective>
    Add a "View briefing" link to the existing
    "Now running across actors" strip on the Workflows page.
  </objective>

  <context>
    <existing-code path="src/attune/ops/templates/workflows.html">
      The bulletin-strip section's title row already has the
      count chip. Add the link next to it.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/ops/templates/workflows.html">
      <change location="bulletin-strip-title h2">
        Append &lt;a href="/curator" class="bulletin-strip-link"&gt;View briefing →&lt;/a&gt;.
      </change>
    </file>
    <file path="src/attune/ops/static/css/main.css">
      <change location="bulletin-strip CSS section">
        .bulletin-strip-link styles (right-aligned, link color,
        font-size matches title).
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Preview the workflows page; the link is visible in the strip title row when bulletin has entries</check>
    <check>Clicking it navigates to /curator</check>
  </validation>
</task>
```

---

## Phase 4 — Live verification

### Task 4.1 — Run against real attune-ai state, iterate prompt

```xml
<task id="4.1" name="live-verification">
  <objective>
    Invoke run_curator against the actual attune-ai
    repository (NOT a fixture). Capture the output, eyeball
    it with Patrick, iterate the system prompt where
    rankings or fact-citations look wrong.
  </objective>

  <context>
    <note>
      This task IS NOT a unit test. It's a manual review +
      prompt-engineering cycle. Budget: 1 hour. Stop and
      reconvene with Patrick if the prompt needs more than
      3 substantive revisions.
    </note>
    <safety>
      Real LLM calls cost real money. Use --max-budget-usd
      0.50 per call. Expected total Phase 4 spend: $2-5.
    </safety>
  </context>

  <validation>
    <check>The curator surfaces at least one item Patrick agrees is high-leverage</check>
    <check>No fabricated sources (every cited item_id resolves)</check>
    <check>Empty state ("nothing pressing") fires honestly when run against a quiet repo state</check>
    <check>Cost stays under $0.50 per call</check>
  </validation>

  <deliverables>
    <deliverable>Frozen system prompt in src/attune/curator/prompt.py</deliverable>
    <deliverable>One-page review notes in docs/specs/bulletin-curator/decisions.md capturing what Patrick liked / didn't, with the prompt evolution.</deliverable>
  </deliverables>
</task>
```

---

## Dependencies

```text
multi-actor-bulletin Phase 1 ──┐
                                ├── Phase 1 (source readers) ──┐
ops-specs-completion-candidates ┘                              │
                                                                ├── Phase 2 (agent)
discovery-sweep-ops-integration ──── (sweep reader)            │
                                                                │
telemetry usage.jsonl writer ────── (telemetry reader)        │
                                                                │
                                              Phase 2 ─────────┴── Phase 3 (UI)
                                                                          │
                                                                          └── Phase 4 (live)
```

All Phase 1 dependencies are already shipped (per
[`_sequencing.md`](../_sequencing.md) Done section). Phase 1
is unblocked the moment `multi-actor-bulletin` Phase 1
lands — which is in flight as PR #478 at the time of this
draft.

---

## Out of scope (deferred)

- **Down-vote learning** — v1 ships per-item dismissal; learning
  the *kinds* of items Patrick suppresses is a separate spec.
- **Multi-project curator** — v1 is single-project (working-
  directory bounded).
- **Continuous polling / proactive surfacing** — v1 fires
  on-demand; a "wake me when X happens" mode would be a
  follow-up spec built on top of this one.
- **Source weighting via config** — v1 trusts the LLM with
  ranking heuristics encoded in the system prompt; numeric
  weights in a config file land later if iteration reveals
  the LLM consistently mis-ranks.
