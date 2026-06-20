# Completeness Audit — Phase 1 Triage Worklist

**Generated:** 2026-06-09 | **Package version at audit:** 8.0.1
**Scope:** the in-scope set defined by [requirements.md](./requirements.md#scope)
and [decisions.md](./decisions.md) (Q1–Q3).

> **What this is:** the Stage-A triage artefact required by the
> acceptance criteria. It classifies in-scope docs into the four
> buckets (MECHANICAL / REWRITE / RETIRE / CLEAN) and is the
> durable inventory that drives the Stage-B bucket PRs.
>
> **Honesty note (faithfulness):** rows are marked **CONFIRMED**
> (verified against current `src/` or by dated-artefact convention)
> or **PENDING** (structural classification by cluster, not yet
> read line-by-line against source). The spec's own risk note
> warns that heuristics miss drift — so PENDING rows carry a
> *recommended* bucket, not an asserted one, and must pass a
> content read before any Stage-B fix lands. This is a first-pass
> worklist within the session effort cap; the PENDING queue is the
> explicit follow-up, per requirements §5 ("anything not landed
> defers … with the triage artefact preserved").

---

## Inventory baseline (re-run 2026-06-09)

| Bucket | Count |
|--------|-------|
| `find docs -name '*.md'` (excl `archive/`, `specs/`) | 226 |
| Tracked in `features.yaml` `doc_paths` (owned by doc-fiction-cleanup / help system) | 45 |
| Untracked, in-scope (before blog rule) | 181 |
| — of which blog (`docs/blog/`, `docs/BLOG_*`) | 55 |
| **Non-blog in-scope (this worklist)** | **126** |

Blog cohort (55) needs a git-date classification pass per Q1
(6-month cutoff) before content audit — deferred to a dedicated
blog pass (no date frontmatter exists; git first-commit date is
the signal). Not classified here.

---

## Summary by bucket (non-blog, 126 docs)

| Bucket | Confirmed | Pending | Total |
|--------|-----------|---------|-------|
| MECHANICAL | 6 | 4 | 10 |
| REWRITE | 1 (done) + 2 | 0 | 3 |
| RETIRE / archive-candidate | 0 | 4 | 4 |
| CLEAN (incl. dated-historical) | 16 | 0 | 16 |
| **PENDING content-verify (Stage A queue)** | — | 93 | 93 |

---

## CONFIRMED — version-fiction (deterministic: stale `**Version:**` header vs 8.0.1)

| doc | bucket | stale claim | evidence | action |
|-----|--------|-------------|----------|--------|
| docs/PROJECT_OVERVIEW.md | REWRITE | hdr 5.1.1; "15 workflows"/"30 tools"/"7 skills"/"14 templates"/"15,555 tests" | real: 8.0.1, 17 workflows (`attune.workflows.list_workflows`), 17 skill dirs | **DONE this PR** — evergreen rewrite, counts stripped, 3 missing workflows added, PyPI pointer |
| docs/reference/API_REFERENCE.md | MECHANICAL | hdr+footer 7.4.0 | `pyproject.toml` 8.0.1 | **DONE this PR** — bumped to 8.0.1 |
| docs/ARCHITECTURE.md | MECHANICAL | hdr 6.3.0 ("Living Document") | living doc; version on an evergreen doc → strip or bump | Stage B: strip version (evergreen) |
| docs/index.md | MECHANICAL | 3.9.0 | landing doc | Stage B: strip/bump |
| docs/rag/index.md | MECHANICAL | 6.1.0 | rag surface current | Stage B: strip/bump |
| docs/getting-started/mcp-integration.md | MECHANICAL | 6.3.0 | MCP integration real | Stage B: strip/bump |
| docs/ORCHESTRATION_API.md | REWRITE | hdr 4.0.0, 1596 lines | `src/attune/orchestration/meta_orchestrator.py` EXISTS → real module, but 4 majors of API drift likely | Stage B: verify API surface, rewrite drifted sections |
| docs/ORCHESTRATION_USER_GUIDE.md | REWRITE | hdr 3.12.0, 1262 lines | companion to above; same drift risk | Stage B: verify + rewrite |

## CONFIRMED — CLEAN (self-disambiguated version)

| doc | evidence |
|-----|----------|
| docs/CODING_STANDARDS.md | hdr "3.9.1 (doc revision, not framework version)" — explicitly a doc-revision number, not a framework-version claim; not fiction |
| docs/EXCEPTION_HANDLING_GUIDE.md | hdr "3.9.0 (doc revision, not framework version)" — same; got partial PR #508 cleanup |

## CONFIRMED — CLEAN, dated-historical (intentionally point-in-time; like blog history)

| doc | why historical |
|-----|----------------|
| docs/rag/embeddings-decision-2026-04-17.md | dated decision record (Q-style pre-committed matrix) |
| docs/rag/faithfulness-decision-2026-04-19.md | dated decision record |
| docs/security/security-fixes-2026-03-17.md | dated fix log |
| docs/testing-audit-2026-04-23.md | dated audit snapshot |
| docs/conversations/ai-consciousness-dialogue-2025-12-28.md | dated transcript |
| docs/conversations/social-post-ai-consciousness.md | companion social post |
| docs/COVERAGE_BUG_LOG.md | append-only log |
| docs/cost-analysis/COST_SAVINGS_BY_ROLE_AND_PROVIDER.md | dated analysis |
| docs/cost-analysis/TIER_ROUTING_SENSITIVITY_ANALYSIS.md | dated analysis |
| docs/examples/generated-plan-release-prep.md | dated generated artefact |
| docs/MULTI_PACKAGE_RELEASE_PATTERNS.md | release-pattern reference (versions are examples) |
| docs/process/COLLABORATION_DISCIPLINE_outline.md | planning outline (per project memory) |
| docs/plans/MONITORING_SPRINT_PLAN.md | dated sprint plan |
| docs/plans/mcp-server-refactor.md | planning artefact |

## PENDING MECHANICAL (recommended bucket; needs read before fix)

| doc | stale signal | note |
|-----|-------------|------|
| docs/pitch/VC_PITCH_DECK.md | 4.4.0 | marketing; strip version, low priority |
| docs/pitch/EXECUTIVE_SUMMARY.md | 4.4.0 | marketing |
| docs/pitch/TECHNICAL_BRIEF.md | 4.4.0 | marketing |
| docs/governance.md | 1.6.1 / 2.0.0 | verify governance content current |

## PENDING RETIRE / archive-candidate (needs decision)

| doc | why candidate |
|-----|---------------|
| docs/CLAUDE_NATIVE.md | "Migration Guide … Complete … v3.0.4" — a *completed* v3 migration record; archival, not current docs |
| docs/AUTH_INTEGRATION_COMPLETE.md | "…COMPLETE" completion record (point-in-time) |
| docs/AUTH_CLI_IMPLEMENTATION.md | implementation record (point-in-time) |
| docs/ARCHITECTURAL_GAPS_ANALYSIS.md | analysis snapshot — verify still relevant |

---

## PENDING — Stage A content-verify queue (93 docs)

These are structurally classified by cluster but **not yet read
line-by-line against `src/`**. Most are expected CLEAN/MECHANICAL
(the feature-doc quad is attune-author-generated from source and
typically tracks current), but per the spec's anti-rubber-stamp
rule they require a content read before a bucket is asserted.
Recommended execution: the Stage-A subagent fan-out (batches of
~15) when the server rate-limiter is cooperative — it tripped a
transient limit on the first attempt this session.

**Feature-doc quad (per real workflow/feature — likely CLEAN, attune-author-generated):**

- `architecture/`: bug-predict, cli, deep-review, help-system, hooks, memory, ops-dashboard, rag-grounding, refactor-plan, release-prep, resilience, security-audit, smart-test, spec-engine, telemetry (15)
- `how-to/`: bug-predict, deep-review, discovery-sweep-on-the-dashboard, hooks, ops-dashboard, plugin, rag-grounding, refactor-plan, release-prep, spec-engine, triage-code-quality (11)
- `reference/`: bug-predict, deep-review, hooks, ops-dashboard, plugin, rag-grounding, refactor-plan, release-prep, smart-test, spec-engine (10)
- `tutorials/`: bug-predict, deep-review, hooks, ops-dashboard, plugin, rag-grounding, refactor-plan, release-prep, spec-engine (9)

**Onboarding / guides (verify install commands, flags, counts):**

- `getting-started/`: choose-your-path, first-steps, index, installation, redis-setup (5)
- `guides/`: DISTRIBUTION_POLICY, MCP_PUBLISH_INSTRUCTIONS, WORKFLOW_PATTERNS, foreword, pattern-catalog, preface, trust-circuit-breaker, wizard-architecture, wizards-getting-started (9)
- `quickstart.md` + `quickstart/index.md` (2) — **possible redundancy** (27 vs 15 lines); hand off dup-check to docs-wiring-audit

**Pitch / marketing (verify metrics, claims):**

- `pitch/`: CASE_STUDIES, COMPETITIVE_ANALYSIS, HEALTHCARE_ONE_PAGER (3) — (VC_PITCH_DECK/EXECUTIVE_SUMMARY/TECHNICAL_BRIEF already flagged MECHANICAL above)

**Philosophy / implementation / integration / misc root:**

- `philosophy/`: ENHANCED_PATTERN_TRACKING_DEMO, XML_ENHANCED_AGENT_COMMUNICATION (2)
- `implementation/`: AGENT_SDK_EVALUATION, MCP_SDK_MIGRATION (2)
- `integration/`: claude-code-integration (1)
- `migration/`: redis-plugin-migration (1) — version timeline doc, likely CLEAN-historical
- `redis/`: best-practice-alignment (1)
- root: DEVELOPER_GUIDE, FEATURES, FEATURE_OVERVIEW_PROJECT_INDEX, PERFORMANCE_OPTIMIZATION_ROADMAP, REDIS_SETUP, SECURITY_REVIEW, SKILLS_REFERENCE, about-the-author, book-cover, commands, comparison, context-management, continuous-learning, contributing, feature-overview-meta-workflows, hooks, keyboard-shortcuts, markdown-agents, repo-hygiene (19)
- `examples/`: adaptive-learning-system, multi-agent-team-coordination, sbar-clinical-handoff, simple-chatbot (4)
- `plans/`: simplify-sweep (1)

---

## Recommended Stage-B sequencing

1. **DONE (this PR):** PROJECT_OVERVIEW evergreen rewrite +
   API_REFERENCE version bump + this triage artefact.
2. **MECHANICAL version-header sweep PR:** ARCHITECTURE (strip),
   index, rag/index, getting-started/mcp-integration, pitch trio,
   governance — each read-then-fixed (confirm body matches current
   behavior before bumping; strip on evergreen-shaped docs).
3. **REWRITE PRs (one per doc):** ORCHESTRATION_API,
   ORCHESTRATION_USER_GUIDE — verify the meta-orchestration API
   surface against `src/attune/orchestration/` first.
4. **RETIRE decision:** CLAUDE_NATIVE + the two AUTH completion
   records → archive to `docs/archive/` (grep `tests/` and the
   PyPI long-description for inbound links first per requirements §5).
5. **Stage-A content-verify of the 93 PENDING docs** (subagent
   fan-out) — promotes each to a confirmed bucket; feeds further
   Stage-B PRs.
6. **Blog date-classification pass** (Q1 6-month cutoff via git
   dates) — separate from this non-blog worklist.

Closing the spec requires the PENDING queue worked through (or
formally deferred to a follow-up release in decisions.md) and a
final `mkdocs build --strict`.

---

## Stage B5 — content-verify results (2026-06-09)

The PENDING queue was content-verified by a 5-batch subagent
fan-out over the **built (site-discoverable)** docs, after a key
prioritisation finding (below). Method: each subagent read its
batch line-by-line against `src/` with the canonical facts
embedded; reported a bucket + specific drift; fixes applied
centrally (report-only agents, no parallel edits).

### Prioritisation finding — `exclude_docs` splits the corpus

`mkdocs.yml`'s `exclude_docs` block excludes large swaths from the
built site. Classifying all in-scope `.md` (excl `specs/`,
`archive/`) through the mkdocs gitwildmatch patterns:

| Set | Count |
|-----|-------|
| In-scope `.md` | 220 |
| **BUILT (on the rendered site — discoverable)** | **113** |
| EXCLUDED (repo-only; GitHub-readable, not on site) | 107 |

Excluded dirs include `pitch/`, `philosophy/`, `implementation/`,
`cost-analysis/`, `conversations/`, `plans/`, `examples/*.md`,
`blog/0*.md`, `BLOG_*.md`, and most top-level `*_*.md` patterns.
B5 focused verification on the BUILT set (highest discoverability;
the only set `--strict` link-checks). Excluded docs were not
content-verified line-by-line — they carry the same drift risk but
lower reach; recorded as deferred below.

### Canonical ground truth (verified against `src/`, 8.0.1)

17 workflows · 5 wizards (debug, refactor, release-prep, security,
test-gen) · 14 agent templates · 10 composition patterns · 41 MCP
tools · 17 plugin skills · ~21,000 tests · Python >=3.10.
`WorkflowResult` real fields: `success, stages, final_output,
cost_report, started_at, completed_at, total_duration_ms, provider,
error, error_type, transient, metadata, summary, suggestions`
(NO `status`/`findings`/`content`/`sources`). `execute()` is
`async`, takes `**kwargs` (commonly `path=`).

### Result — the "generated quad is CLEAN" hypothesis FAILED

The fan-out found pervasive, *systemic* fiction across the built
docs, far beyond the triage's "mostly low-drift" expectation. It
splits into two root causes that drive two follow-up specs:

**Root cause A — legacy "Empathy framework" hand-written docs.**
These describe a superseded product surface (5-level empathy
maturity model, healthcare/HIPAA, `EmpathyOS` as "main entry
point") with dead/fabricated APIs and legacy naming. → routed to
the **legacy-doc-retirement** follow-up. Docs: `index.md`,
`reference/{core,empathy-os,glossary,llm-toolkit,configuration,config,pattern-library,TROUBLESHOOTING,cli-reference}.md`,
`getting-started/choose-your-path.md`. Representative drift:
`import attune_llm` (real: `attune.llm`), `coach_wizards` (real:
`attune.wizards`), `EmpathyOS.from_config` (absent),
`PatternLibrary.find_patterns`/`remove_pattern` (absent),
fictional `EmpathyOS(...)` kwargs, stale versions (v1.10.0, v3.9.0,
"November 2025"), legacy `empathy`/`Empathy-framework` naming,
fictional `[healthcare]` install, `attune.cli` module (absent),
`test-coverage` workflow (real: `test-gen`).

**Root cause B — attune-author generator bug in the feature
quad.** `how-to/`, `reference/`, `tutorials/` per feature share
identical generated failure modes (the docs' own fact-check
footers even document the unresolved imports). → routed to the
**attune-author generator-fidelity** follow-up (fix the generator
+ regenerate; hand-patching ~30 generated docs would regress on
next regen). Failure modes: wrong import paths (top-level
`pipeline`/`spec`/`workflows`/`release` instead of `attune.*`);
async-shown-as-sync (`execute()`/`run_all()`/`assess_readiness()`
are `async def`); `@property` shown called as `()`; fabricated
standalone CLI binaries (`spec-engine`, `bug-predict`,
`release-prep`) when the real surface is `attune workflow run
<name>` or a skill; fictional `WorkflowResult.content/.sources`;
MCP tool `document_generation` (real: `doc_gen`);
`BaseWorkflow.call_llm` (real: `_call_llm`); stale "Opus 4.6"
(PREMIUM is `claude-opus-4-8`); dead `plugin/commands/attune-security.md`.

### Per-doc disposition (built docs verified)

**FIXED this PR (MECHANICAL + the one onboarding REWRITE):**

| doc | fix |
|-----|-----|
| getting-started/first-steps.md | REWRITE the Python example to the real `WorkflowResult` API (`success`/`summary`/`final_output`/`cost_report.total_cost`; `execute(path=)`; drop fictional `enable_cache`/`status`/`findings`) |
| getting-started/installation.md | VSCode-extension refs → Claude Code plugin; fiction flag `provider --check` → `attune provider show` |
| guides/wizard-architecture.md | 12 → 15 mixins; "3-tier" → "4-tier" search |
| contributing.md | repo slug `…/empathy/…` → `…/attune-ai/…` |
| migration/redis-plugin-migration.md | `redis<8.0.0` → `<9.0.0` |
| how-to/index.md | "Empathy deployment" → "Attune AI deployment" |
| reference/index.md | removed fictional `pip install attune-ai[healthcare]` |
| reference/FAQ.md | stale model names Sonnet 4.5/Opus 4.5 → 4.6/4.8 |
| docs/pitch/* (6) | counts: 5 wizards, 17 workflows, 14 templates, 10 patterns, 21,000+ tests; fictional `ClaudeCodeIntegration` block → real plugin install; removed-VSCode → ops dashboard; Python 3.8 → 3.10 |
| FEATURES.md, PERFORMANCE_OPTIMIZATION_ROADMAP.md, governance.md | stripped stale count/version footers (evergreen) |

**CLEAN (no action):** getting-started/{index,redis-setup},
redis/best-practice-alignment, reference/{wizards,multi-agent,agent-factory-overview,agent-factory-api,ops-dashboard},
guides/wizards-getting-started, DEVELOPER_GUIDE, integration/claude-code-integration
(MECHANICAL framing note only), and the dated-historical set
(rag/*-decision, security/security-fixes-*, testing-audit-*).

**ROUTED to legacy-doc-retirement follow-up (REWRITE/retire):**
the Root-cause-A doc list above.

**ROUTED to attune-author generator-fidelity follow-up
(regenerate):** the feature quad (`how-to/<feature>`,
`reference/<feature>`, `tutorials/<feature>` for the ~15 features).

### Blog (B6 kept all 55 in-scope by git date)

- **Archived** (content-historical version-announcement posts) to
  `docs/archive/blog/2026/`: `attune-ai-v4-agent-sdk.md` (v4.0),
  `discord-v6-release.md` (v6.0). No inbound links from built docs.
- **Deferred:** remaining blog tutorial/essay/social posts carry
  point-in-time counts (557 templates, 18 workflows, 38 MCP tools,
  etc.). Treated as dated content-marketing artifacts (same
  convention as dated-historical CLEAN docs) — a blog-copy refresh
  is out of scope for the completeness audit. See decisions.md
  Q4.
