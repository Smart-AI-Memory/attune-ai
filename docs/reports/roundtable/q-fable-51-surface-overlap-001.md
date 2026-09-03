# Round table transcript — `q-fable-51-surface-overlap-001`

**Convened:** 2026-09-02 (chair-dated 2026-09-03) · **Chair:** Patrick
Roebuck · **Moderator:** Claude (Fable 5, this session) · **Roster:**
Claude, Antigravity, Codex — all three seats answered (no absences).
**Rounds:** 1 of a chair-ruled spend gate of 3 seat invocations / 1
round; halted at the gate (board msg 7). A second round needs a fresh
chair go.
**Board thread:** `attune:roundtable:*` / `q-fable-51-surface-overlap-001`
(TTL 7 days; this file is the durable record).
**Receipts:** codex 43s (msg 2) · antigravity 92s, plan mode (msg 3) ·
claude 129s / 62,710 subagent tokens, context-free general-purpose agent
(msg 5). Question posted verbatim from
`docs/specs/host-surface-parity/roundtable-question.md` (msg 1).
**Promotion status:** NOT promoted — no chair rulings yet (R4 holds).
Promotion candidates by board id: positions 2 (codex), 3 (antigravity),
5 (claude); member questions 4 (antigravity), 6 (claude); synthesis 8.

---

## Message 1 — chair · question · round 1

# Round-table question — `q-fable-51-surface-overlap-001`

**Chair:** Patrick Roebuck · **Moderator:** Claude · **Roster:** Claude,
Antigravity, Codex (fixed) · **Rounds:** 1 expected, 2 if the steelman
provision fires (chair lean is recorded below), ceiling 3 (D3).
**Spend gate (chair-ruled 2026-09-03):** 3 seat invocations, 1 round;
a second round needs a fresh chair go.
**Prepared:** 2026-09-03 by the Claude seat in a Cowork session.
**Transcript:** the moderator writes the machine-local transcript to
`~/.attune/reports/roundtable/q-fable-51-surface-overlap-001.md`; please
also copy it to `docs/reports/roundtable/` so the Cowork seat (which
sees only the repo) can read it and draft the promotion triage.

## The question

The 2026-09-01 host release (Claude Fable 5.1; Cowork and Claude Code)
ships first-party versions of things attune-ai built as portable,
verified, multi-provider systems: a structured question widget
(`AskUserQuestion`), desktop-persistent project memory (`MEMORY.md` +
typed topic files), a skill-proposal card, a multi-agent workflow
runner, typed review findings, hosted artifacts with runtime state,
scheduled tasks, and a file monitor.

**Which of Attune's human↔AI communication and capability features
does this release overlap, and where should the next two minors
spend effort so the release is a tailwind rather than a headwind —
without any host becoming the privileged surface, and without
power users on Codex or Antigravity sacrificing anything?**

## What each seat is asked to return

Independently, text only, no tools (R1):

1. A ruling on each proposed requirement R1–R8 in
   `docs/specs/host-surface-parity/requirements.md`: **adopt / amend
   (say how) / decline (say why)**.
2. At least one requirement the Claude seat did **not** propose. The
   chair has asked the table to be creative and not limited to the
   brief.
3. A position on the three open mechanics: D2 (`LOCAL` as enum member
   vs routing label), D3 (no third capability contract), and whether
   Task 7 (Ollama reranker as the Phase A example extension) should
   wait for Phase B.
4. Its own dissent register: where it disagrees with the Claude
   seat's reading in the companion brief.

## Facts taken as given (verified against the tree 2026-09-03)

- attune-ai 16.2.0; attune-forms ≥ 0.12.2; `Surface.RICH / PORTABLE /
  HEADLESS`; state-bound command workspaces shipped.
- `CANONICAL_SEATS` is a literal three-tuple; `SEAT_RECIPES` fixed
  argv; `PLAN_ONLY_SEATS = {"antigravity"}`; workspace gates require
  exactly the fixed roster.
- `ModelProvider` has one member (`ANTHROPIC`); tiers are
  `CHEAP / CAPABLE / PREMIUM` in four copies plus the attune-rag
  mirror with a drift guard.
- `attune.extensions` (release-16-manifest passenger 4) is **not on
  disk**; D1/D2 ruled; D3 phasing proposed, not ruled.
- Chair rulings already made (this spec's D1, 2026-09-03): local
  models start as a `LOCAL` tier for low-stakes roles, not a seat;
  extensions are the seam for providers/backends/seats; the
  deliverable is this spec.

## Chair's lean (recorded so the steelman provision can fire)

The chair leans toward adopting the parity rule (every host-specific
capability ships with PORTABLE and HEADLESS twins, receipted, in the
same change) and toward roster-as-data. Seats that agree should
steelman the opposite; seats that disagree should say what the
parity rule costs.

## Companion material

- Brief (Claude seat opening position): artifact
  "Fable 5.1 and the Attune Surface", 2026-09-03.
- Spec: `docs/specs/host-surface-parity/` (requirements, design,
  tasks, decisions).
- Discipline: attune-ai.dev/discipline, §2 (contract), §5 (memory),
  §7 (verification), §9 (context budgeting).

---

## Message 2 — codex · position · round 1 · duration 43s

1. Rulings on R1–R8

**R1 — ADOPT.** Native structured questions are an additional projection target. Capability detection must happen before rendering, with unsupported forms falling through intact to PORTABLE. Add contract tests covering validation errors, multi-select ordering, “Other,” cancellation, and host-version capability changes.

**R2 — AMEND.** Adopt same-change parity, but enforce it through a declared surface registry rather than filesystem enumeration. Every host-specific adapter must reference:

- One canonical semantic form
- PORTABLE and HEADLESS projections
- A conformance receipt proving equivalent validated values

Filesystem scanning is too easy to evade accidentally and too brittle around helpers and templates.

Steelman against the chair’s parity lean: mandatory three-surface receipts increase the cost and latency of exploiting a new host feature, can force meaningless twins for capabilities with no portable analogue, and may reduce experimentation to the lowest common denominator. The answer is an explicit, expiring parity exception—not weakening the default gate.

**R3 — AMEND.** Do not create a literal “second master.” The Attune promoted-lesson index remains authoritative; host files contain generated projections with provenance, generation version, bounded summaries, and links back to Attune truth. Each destination needs a delimited owned block so unrelated human edits remain legal. Projection must support removal and stale-entry cleanup, not merely regeneration after promotion.

**R4 — ADOPT.** This is precisely the right use of a receipt: validate the existing path without inventing another integration. Record both advertised-profile and fallback cases, including stale revision, wrong contract hash, and replay rejection.

**R5 — AMEND.** Define one host-neutral automation manifest and compile it into host scheduling/file-monitor configuration or cron plus CLI. Do not make host templates the primary definition. Require idempotency, overlap locking, debounce, spend attribution, and loop prevention. Watching `context_fit.jsonl` must not allow an Attune run’s own telemetry write to retrigger itself. Settling the budget clock should be separately asserted rather than treated as a side effect of the first monitor.

**R6 — AMEND.** Adopt the roles and extension phasing, but make `LOCAL` a routing attribute outside the quality-tier enum. Preserve `CHEAP/CAPABLE/PREMIUM` as quality/cost policy. Locality, privacy, and execution venue are orthogonal dimensions. Keep `ModelProvider` unchanged and impose confidence thresholds plus escalation to a capable hosted model for consequential workflow decisions.

**R7 — AMEND.** Move the roster to validated data, but model more than role names: execution mode, plan-only status, required capabilities, trust boundary, receipt responsibilities, and harness recipe must be explicit. Preserve the current roster through golden behavior tests. Extension-provided additional slots remain structurally representable but disabled until the required later chair authorization; R7 must not accidentally authorize seat four.

**R8 — AMEND.** Record structured asks per terminal outcome, not only completed outcomes. Otherwise abandoned or blocked sessions—the most frustrating ones—vanish from the metric. Report at least:

- Asks per accepted receipt
- Zero-outcome/abandonment rate
- Ask type and fallback frequency

Keep this in the existing ledger and avoid recording answer contents.

The overlap is real but mostly at the presentation and orchestration edges: native questioning overlaps forms, host memory overlaps lesson projection, skill proposals overlap discovery/proposal UX, workflow runners overlap orchestration, typed findings overlap Attune receipts/reviews, hosted artifacts overlap state-bound workspaces, and schedules/monitors overlap automation. Attune’s defensible layer is cross-host semantics, validation, policy, receipts, and reproducibility.

2. Additional requirement

**R9 — Portable capability negotiation and conformance kit**

Every host adapter and extension publishes a machine-readable capability descriptor: supported question shapes, persistent-memory destinations, artifact runtime features, scheduling/monitoring support, action round-trip guarantees, and receipt schema versions.

A shared conformance suite runs canonical transcripts against each adapter and proves:

- Unsupported capabilities degrade deliberately
- Semantic outputs remain equivalent
- Receipts retain provenance and replay protection
- Removing a host adapter leaves PORTABLE and HEADLESS execution usable
- No workflow silently selects a privileged host

This turns portability from a collection of twins into a testable protocol. It should be the foundation minor; native integrations and automation compilation should follow in the second minor.

3. Open mechanics

**D2 — Routing label outside the enum.** `LOCAL` describes execution locality, not model competence or price. Adding it beside `CHEAP/CAPABLE/PREMIUM` creates invalid comparisons and multiplies drift across five mirrored enums. Use a separate routing dimension such as `execution=local|hosted` or a constrained extension label. This honors the chair’s “LOCAL tier” product decision without encoding two unrelated axes in one enum.

**D3 — Confirm “no third capability contract” for the next two minors.** Reranking is an optional memory-backend capability; classification and workflow roles belong to the workflow contract. A provider-level contract would prematurely generalize from Ollama and undermine the binding non-goal. Revisit only after two independently implemented extensions demonstrate needs that cannot fit either contract cleanly.

**Task 7 phasing — Ship the Ollama reranker alone first.** It is the smallest real proof that extension discovery, optional capability advertisement, fallback, receipts, packaging, and failure isolation work. Phase B should depend on that evidence. Holding it for workflow extensions creates a larger debugging surface and delays validation of the seam.

4. Dissent register

**H1 — Mostly agree, with a boundary.** Tier 0 is a projection target only when it preserves the form’s semantics. “Single question” is insufficient by itself; validation, cancellation, defaults, multi-select behavior, and recommendation semantics must also fit. Otherwise use PORTABLE.

**H2 — Agree on enforceability, disagree on the proposed mechanism.** Parity can be mechanical, but tree enumeration does not establish semantic coverage. A registered capability graph plus conformance receipts does.

**H3 — Partly disagree.** “The host remembers; Attune recalls” is sound positioning, but copying lesson lines into several instruction files risks context pollution, stale projections, prompt-authority confusion, and collisions with human-maintained guidance. Project bounded, generated summaries and references—not an unconstrained second index.

**H4 — Agree with qualification.** Local models should earn bounded roles before seats. However, “skeptic,” “countersign,” and “fact-check” must remain advisory probes with escalation thresholds; a weak local model must not manufacture the appearance of independent verification.

**H5 — Amend.** Roster by role is necessary but insufficient. A seat is a role plus capabilities, trust boundary, execution semantics, and receipt obligations. Vendor-neutral configuration without those constraints can produce formally valid but behaviorally incomparable rosters.

On Claude’s own dissent points: withdrawing the Claude-only memory bridge was correct. I agree that projected memory does not replace recall, but only if projection remains intentionally bounded; an overfull host notebook could both appear “good enough” and degrade prompt quality. LOCAL should remain outside the quality enum for the reasons above.

---

## Message 3 — antigravity · position · round 1 · duration 92s (plan mode)

### 1. Rulings on Proposed Requirements R1–R8

#### **R1 — Host Tier 0 Renderer**
**Ruling: AMEND**
*Amendment:* Do not hardcode the Tier 0 target to the specific constraints of Claude Fable 5.1’s `AskUserQuestion` (max 4 options, single question). In environments like Antigravity, native structured question tools (`ask_question`) inherently support multi-question forms (`questions: [...]`) with arbitrary option arrays.
Tier 0 must be defined as a **Host Capability Adapter** governed by a capability descriptor (e.g., `max_options: int`, `supports_multi_question: bool`, `supports_free_text_escape: bool`). If the form fits within the detected host envelope, render natively; if it overflows, fall through cleanly to `PORTABLE`. Forcing every host into Claude's 4-option, single-question box unnecessarily degrades the UX in agent runtimes that possess richer native interactive form primitives.

---

#### **R2 — Surface Parity Gate**
**Ruling: ADOPT (with Chair Lean Steelman)**
*Steelman of the Anti-Parity Position:*
> Mandating strict tripartite synchronization (`RICH`, `PORTABLE`, `HEADLESS`) enforced by a blocking drift-guard imposes an unsustainable velocity tax on frontend experimentation. When a host introduces a breakthrough interaction surface (such as interactive visual canvases, fluid artifact runtimes, or streaming graph visualizers), requiring developers to build, receipt, and maintain a semantically identical terminal ASCII and headless twin before shipping delays user value by weeks and bloats PRs by 300%. The result is often contrived, low-value headless mocks written solely to appease the drift guard, disincentivizing teams from taking full advantage of host-native UI differentiators.

*Why Antigravity Still Adopts:* For an agentic CLI and automation platform, headless and terminal fidelity is not an afterthought—it is the foundation of headless CI/CD, batch processing, and non-interactive subagent execution. Without R2, multi-provider portability will quietly rot into a Claude Desktop-first monoculture.

---

#### **R3 — Memory Index Projection**
**Ruling: AMEND**
*Amendment:* Impose a strict **budget and relevance ceiling** on projected indices, and enforce sentinel marker boundaries.
Projecting an unbounded one-line-per-lesson index into `.claude/CLAUDE.md`, `AGENTS.md`, and `.agents/AGENTS.md` creates severe static context-window bloat. In systems like Antigravity where subagents are spawned frequently with inherited project instructions, injecting dozens or hundreds of memory pointer lines imposes an unavoidable token tax on every turn, diluting prompt attention.
R3 must project only a bounded top-$K$ active digest (e.g., max 25 entries prioritized by recent hit frequency and project scope), strictly bracketed by generated sentinel comments (`<!-- ATTUNE:MEMORY:START -->` ... `<!-- ATTUNE:MEMORY:END -->`) to allow safe co-existence with user-authored agent instructions. Hand edits within the sentinel block must fail closed on drift check, while leaving edits outside the block untouched.

---

#### **R4 — MCP Apps Round-Trip Receipt**
**Ruling: ADOPT**
*Rationale:* R4 establishes empirical verification over interface promises. Testing the Fix preview workspace through standard `ui://` profiles while asserting that nonces, contract hashes, and revisions remain unforgeable—and verifying that non-supporting hosts fall back cleanly to Markdown—ensures state-bound workspaces remain tamper-proof without speculative production churn.

---

#### **R5 — Scheduled and Monitored Delivery, Twinned**
**Ruling: AMEND**
*Amendment:* Prohibit autonomous, heavyweight LLM sweeps (`discovery-sweep`, `release-prep`) from triggering directly on raw file-system events.
File monitor events (such as changes to `~/.attune/telemetry/context_fit.jsonl`) must only trigger **deterministic triage probes** or stage an item in the `docs-outbox` / notification tray. Full multi-turn agent sweeps must require:
1. A configurable debounce window (minimum 60s),
2. A strict circuit-breaker spend gate with an hourly execution cap, and
3. User or explicit agent acknowledgment before spinning up token-intensive audits.
Without this amendment, file-monitor loops risk runaway token spend during rapid edit-save cycles.

---

#### **R6 — Local-Model Roles via Extensions**
**Ruling: AMEND**
*Amendment:* Adopt the role-progression model (Phase A reranker, Phase B classification/triage/fact-check probes), but **reject adding `LOCAL` as an enum member of the model tier contract**.
As detailed under Section 3 (D2), `LOCAL` is an orthogonal runtime deployment/locality attribute, not a model capability tier. R6 must route local models via an `ExecutionLocality` configuration tag on capability contracts rather than polluting the core tier enum.

---

#### **R7 — Roster as Data**
**Ruling: ADOPT (with Chair Lean Steelman)**
*Steelman of the Fixed-Roster Position:*
> Hardcoded constants (`CANONICAL_SEATS = ("claude", "antigravity", "codex")`) provide compile-time type safety, exhaustive pattern matching, and zero-overhead execution guarantees. Moving seats into dynamic data (`roster.yaml`) introduces configuration-injection risks, runtime parse failures, schema drift, and an exponential explosion of test matrices. In a consensus round table where deterministic attestation and peer receipts are the entire value proposition, allowing dynamic rosters risks topology failure modes (e.g., configurations with zero reviewers, multiple unreceipted proposers, or missing moderators) that static types prevent by construction.

*Why Antigravity Still Adopts:* Decoupling seat definitions from hardcoded Python literals is essential for enterprise deployments running isolated air-gapped models, private CI harnesses, or synthetic mock seats for automated testing. As long as the roster schema validates invariant roles (exactly one moderator, one reviewer, one proposer) and gates extensions behind signatures, configuration-as-data is strictly superior.

---

#### **R8 — Asks-per-Outcome**
**Ruling: ADOPT**
*Rationale:* Measuring "demandingness" purely by raw prompt interruptions penalizes structured, high-leverage alignment interactions. Normalizing structured inquiries against validated receipts (`asks / completed_outcome`) rewards agents for asking precise, high-yield clarifying questions up front while penalizing meandering, low-yield dialogue.

---

### 2. Antigravity-Proposed Requirements (Not in Claude Brief)

#### **R9 — Typed Diagnostic & Review Finding Interchange (`DiagnosticSeam`)**
*Motivation:*
Claude Fable 5.1 introduces first-party "typed review findings." Codex interfaces natively with GitHub pull request review threads and diff hunks. Antigravity operates natively with IDE diagnostics, compiler errors, and target lint IDs (`TargetLintErrorIds`). Currently, Attune's audits (`deep_review`, `security_audit`, `bug_predict`) emit structured findings, but they do not project into host-native diagnostic trays.
*Specification:*
Attune defines a portable `ReviewFinding` interchange schema conforming to SARIF Level 2:
$$\{ \text{finding\_id}, \text{rule\_id}, \text{severity}, \text{file\_path}, \text{line\_range}, \text{message}, \text{proposed\_fix\_diff}, \text{receipt\_hash} \}$$
Attune projects these findings into:
1. Fable 5.1 / Claude Code typed review cards,
2. Codex/GitHub inline PR review threads,
3. Antigravity IDE diagnostic collections / problem gutters,
4. A portable SARIF/JSON stream for terminal/headless execution.
Host UI actions (Dismiss, Accept, Defer, or Fix-with-Receipt) round-trip back into the Attune review ledger through a normalized callback receipt.

#### **R10 — Multi-Agent Worktree Lease & Turn Attestation Protocol**
*Motivation:*
Fable 5.1 ships a multi-agent workflow runner; Antigravity orchestrates concurrent subagents across workspaces; R5 introduces background file-monitors and scheduled tasks. When multiple agents or background tasks operate simultaneously within a shared repository, git index lock contention and conflicting file overwrites occur. Furthermore, in multi-model round tables, there is currently no cryptographic proof that a turn attributed to Antigravity or Codex was not hallucinated or simulated by Claude.
*Specification:*
1. **Advisory File/Workspace Lease:** An ephemeral lock protocol (`.attune/locks/<scope>.lease`) with heartbeats and auto-expiry to prevent concurrent destructive writes between host runners and background tasks.
2. **Turn Attestation Receipt:** Each round-table seat signs its output turn with an execution receipt (harness PID, model runtime fingerprint, nonce, and execution timestamp). The moderator gate verifies turn receipts before consensus promotion, eliminating seat simulation.

---

### 3. Position on Open Mechanics

#### **D2: `LOCAL` as Member of Tier Enum vs. Routing Label**
**Position: ROUTING LABEL OUTSIDE THE ENUM.**
*Rationale:*
1. **Dimensional Orthogonality:** `CHEAP`, `CAPABLE`, and `PREMIUM` describe reasoning depth, parameter capacity, and token cost along a vertical scale. `LOCAL` describes an execution topology / locality attribute along an orthogonal horizontal scale. A local model can be cheap (e.g., 1.5B Qwen), capable (e.g., 70B Llama 3.3), or highly specialized.
2. **Blast Radius & Drift Guard Churn:** Adding `LOCAL` to the tier enum breaks four core source files and the `attune-rag` mirror, forcing unnecessary updates to drift guards, pricing calculation tables, and token-spend tracking logic that assume tiers represent Anthropic billing tiers.
3. **Architectural Purity:** Locality should be specified as an execution preference:
   ```python
   # Correct abstraction
   target_tier: ModelTier = ModelTier.CAPABLE
   execution_locality: Locality = Locality.LOCAL_PREFERRED  # or LOCAL_REQUIRED / CLOUD_ONLY
   ```
   This allows an extension to route a `CHEAP` role to local Ollama when available, falling back to hosted cloud tiers as policy permits.

#### **D3: Confirm or Challenge "No Third Capability Contract"**
**Position: CONFIRM for Minor 16.3; CONDITIONAL CHALLENGE for Minor 16.4.**
*Rationale:*
- **Confirm for 16.3:** Deferring a general `ModelProvider` contract is the correct tactical decision. In 16.3, local models are strictly scoped to R6 roles (rerank, pre-sort, low-stakes probes). Because a workflow extension encapsulates its own execution transport (e.g., calling `localhost:11434` via `httpx` internally), it does not require Attune core to manage a generalized LLM provider interface. Keeping the contracts limited to `memory-backend` and `workflow` prevents premature API surface sprawl.
- **Challenge for 16.4:** An embedding and scoring capability is currently wedged uncomfortably inside `memory-backend`. If local models expand into code-embedding, semantic search, or invariant evaluation, forcing them into `memory-backend` will leak retrieval concerns into scoring. In 16.4, Attune should formalize an `Evaluator`/`Embedding` seam rather than bloating `memory-backend`.

#### **Task 7 Phasing: Ollama Reranker Alone vs. Waiting for Phase B**
**Position: SHIP THE OLLAMA RERANKER ALONE IN PHASE A.**
*Rationale:*
1. **Canary for the Extension Seam:** `attune.extensions` is currently not on disk. Shipping the Ollama reranker alone isolates the extension discovery, loading, and lifecycle mechanisms from complex multi-agent orchestration.
2. **Deterministic Verification:** Reranking has a closed, mathematically deterministic contract:
   $$\text{rerank}(\text{query: str}, \text{candidates: list[Doc]}) \to \text{ranked\_ids: list[str]}$$
   It requires zero prompt-engineering gymnastics, produces no generative hallucination, has no schema-parsing edge cases, and can be verified by exact automated test receipts.
3. **Fast Feedback Loop:** Validating the extension seam on reranking in 16.3 de-risks IPC latency, process lifecycles, and Ollama connection failures before introducing generative workflow extensions in 16.4.

---

### 4. Antigravity Dissent Register

| Item | Claude Seat Hypothesis / Register | Antigravity Dissent & Counter-Position |
| :--- | :--- | :--- |
| **Dissent 1 (on H1)** | **H1:** *Tier 0 is a render target, not a rival. Richer constructs keep their own renderers and are not degraded.* | **Dissent:** H1 defines Tier 0 exclusively by Claude Fable's 4-option, single-question limitation. Antigravity natively supports multi-question modals and rich options via its native tools. By conflating "Host Tier 0" with "Claude Fable 5.1 constraints," the Claude seat covertly turns a vendor limitation into a universal standard. Tier 0 must be parameterized by host capability metadata, not clamped to Claude's lowest common denominator. |
| **Dissent 2 (on H2)** | **H2:** *Parity can be mechanical via identical validated output receipts across tiers.* | **Dissent:** Output identity is insufficient for parity. An interactive terminal or GUI permits user aborts, parameter backtracking, and inspectable intermediate diffs; a dumb headless pipe often consumes inputs blindly. The parity gate must assert **interaction lifecycle parity** (timeout semantics, abort handling, validation feedback loops), not merely that a mock input string yields an identical output token. |
| **Dissent 3 (on H3)** | **H3:** *The host remembers; Attune recalls. Projecting memory index into MEMORY.md makes plain sessions benefit without diluting recall.* | **Dissent:** Projecting an unbounded index directly into prompt-injected files (`CLAUDE.md`, `AGENTS.md`) is hostile to context-window budgets. In agent runtimes that regularly spawn focused subagents, every injected index line steals attention and context budget on every single subagent turn. Furthermore, plain host sessions without Attune’s retrieval tooling hallucinate when attempting to follow raw index pointers. Projection must be an explicit, compact, LRU-budgeted cache. |
| **Dissent 4 (on H4)** | **H4:** *Local models earn a role before a seat... not deliberation.* | **Dissent:** Barring local models from deliberation by principle contradicts Attune's creed: *"The receipt beats the promise."* In air-gapped enterprise environments, high-parameter local models (e.g., Llama-3.3-70B running on private vLLM clusters) are fully capable of serving as plan-only invariant reviewers. Eligibility for a seat must be governed by test-harness benchmark receipts, not dogmatic provider favoritism. |
| **Dissent 5 (on Claude Dissent a)** | *Claude seat withdrew Claude-only memory bridge to avoid vendor preference.* | **Dissent:** Withdrawing the Claude-only bridge was necessary, but R3 replaced it with an unthrottled index dump across all files. The real solution is a pull-based memory tool or a tightly budgeted sentinel projection, not spraying pointers across every vendor instruction markdown file. |

---

### Follow-Up Question for the Table
> *"When an interactive Fix workspace (R4) or a typed review finding (R9) is resolved inside a host-native UI by a human developer, what is the precise cryptographic schema for the return receipt that proves to peer seats (running in headless CI or across different host runtimes) that the action was executed by an authorized human chair rather than an unverified host subagent simulation?"*

---

## Message 4 — antigravity · question (R9 member-originated, reply_to 3)

When an interactive Fix workspace (R4) or a typed review finding (R9) is resolved inside a host-native UI by a human developer, what is the precise cryptographic schema for the return receipt that proves to peer seats (running in headless CI or across different host runtimes) that the action was executed by an authorized human chair rather than an unverified host subagent simulation?

---

## Message 5 — claude · position · round 1 · duration 129s · 62,710 tokens

## Section 1 — Rulings R1–R8

**R1 — Host tier 0 renderer: AMEND (adopt the projection; parameterize the contract).**
Adopt the mechanism — single-question projection, hard fall-through above the contract, identical validation on return. Amend one thing: the contract constants (four options, label+description, "(Recommended)" suffix, host "Other" escape) must live in a declared *host profile* record, not be inlined as Claude's AskUserQuestion shape. Tier 0 should be "project onto whatever structured-question contract the current host advertises," with the Claude profile merely the first entry. Otherwise R1 is the one place in attune-forms where a specific vendor's widget shape is hardcoded — exactly the quiet privileging the question forbids. Cost of the amendment is one dataclass and a lookup; benefit is that when Codex or Antigravity ships a native question widget, tier 0 lights up there with zero renderer changes.

**R2 — Surface parity gate: AMEND (adopt the gate; add a drift-guarded, expiring spike allowlist).**
I agree with the chair's lean, so the steelman first. The honest case against the parity rule: (1) it is a 3x tax charged *before* a host feature has proven value — the most expensive possible moment; (2) it produces parity theater — a HEADLESS "twin" of a live file-monitor wake is a cron poll nobody runs, written to satisfy a gate, and the gate cannot distinguish a real twin from a compliance artifact; (3) "in the same change" couples host-launch-speed work to portable design work, and host launches move on someone else's calendar; (4) for a team of one, tripling the render-test surface is the difference between shipping and not. That case is strong enough that pure ADOPT is wrong. Rule: adopt the gate, plus an `experiments:` allowlist entry with a mandatory expiry date (14–30 days), itself drift-guarded — the gate fails on any expired entry. A spike may exist untwinned; a shipped surface may not. This keeps "the receipt beats the promise" as the steady state while pricing exploration honestly. Also: the receipt clause "identical validated output" should read "identical validated *payload*" — see my H2 dissent.

**R3 — Memory index projection: ADOPT.**
The every-host projection is the correct answer to the release, and the seat's withdrawal of the Claude-only bridge was the right call for the right reason. Two implementation notes that don't rise to amendment: each projected block carries a generated-by header naming the regenerate command (the refuse-hand-edits behavior needs a visible explanation at the point of temptation), and per-host line budgets should be independent (CLAUDE.md's budget pressure is not AGENTS.md's).

**R4 — MCP Apps round-trip receipt: ADOPT.**
It is a receipt with a no-production-change clause; there is nothing to spend against. The replay-fails-closed and no-profile-fallback checks are the two things that will actually break under host drift, and this is the cheapest early-warning system on the list. Do it first among the eight.

**R5 — Scheduled and monitored delivery, twinned: AMEND (portable twin is the master; host task is a binding).**
Adopt the scope (discovery-sweep, bug-predict, release-prep; context_fit.jsonl as first monitored path; spend gate applies). Amend the ordering and ontology: the cron + attune CLI path is the *definition* of the scheduled behavior, and the host scheduled-task/file-monitor is a projection of that definition — not two parallel implementations that R2 later reconciles. Concretely: one template document per task, from which both the crontab line and the host task registration are generated. Twins that share a master cannot drift; twins written side by side will, and R2 will then catch drift you could have made impossible.

**R6 — Local-model roles via extensions: ADOPT.**
D1 is chair-ruled and this is its faithful implementation: two ruled contracts, roles not seats, no ModelProvider change, no third contract. Mechanics resolve per my D2 and phasing positions in Section 3.

**R7 — Roster as data: AMEND (adopt, with a golden-roster receipt and a typed-slot check).**
Steelman against, since I agree with the chair's lean: the literal three-tuple is the strongest invariant in the tree — "exactly these three, exactly these argv" is checkable by `==`; roster-as-data replaces it with "exactly whatever the roster says," which is a weaker gate wearing the same name, and data-driven rosters invite untested combinations and config sprawl for a roster that has changed zero times. The answer to that steelman is to keep the old invariant as a receipt: (a) a golden test asserting the default roster reproduces the current literals byte-for-byte in behavior — CANONICAL_SEATS, SEAT_RECIPES argv, PLAN_ONLY_SEATS membership — so the refactor is provably a no-op; (b) role slots are typed (plan-only reviewer / code-native proposer / moderator-with-receipts) and validated, so a roster edit that produces two moderators or zero plan-only reviewers fails loudly; (c) the fourth-slot-requires-enabled-extension rule is enforced in the roster loader, not in prose, since the non-goal binds this spec but the loader outlives it.

**R8 — Asks-per-outcome: AMEND (record raw pairs; floor the gate; keep the old signal as a guard).**
The reframing — structure per result, not interruptions per session — is right and worth adopting. Three defects to fix before friction_gate reads it: (1) sessions with zero completed outcomes make the ratio undefined exactly when friction is worst — a session with twelve asks and no receipt must still register, so keep asks-per-session as a secondary guard; (2) the metric is gameable by outcome inflation (splitting one result into three receipts halves the figure) — record raw numerator and denominator in the ledger, not the ratio; (3) friction_gate should act only above a minimum-outcomes floor so one weird session doesn't swing behavior. No new telemetry store, as proposed.

## Section 2 — Requirements this seat proposes

**R9 — Host capability matrix with a `surfaces doctor` probe (primary proposal).**
"No host becomes the privileged surface" is currently a design intention with no enforcer. Ship one: a session-start probe (`attune surfaces doctor`) that records which contracts the current host actually advertises — structured question, memory surface, ui:// profile, scheduled tasks, file monitor — and writes a capability receipt. From accumulated receipts, a generated matrix (hosts × capabilities, each cell native / fallback-receipted / absent) lives in-tree and is drift-guarded: R2 proves every surface *has* twins; R9 proves the twins are *exercised* on real hosts, and makes "Cowork is quietly becoming the privileged surface" a red cell you can see rather than a vibe. Renderers consult the probe instead of sniffing per call. Crucially, the matrix must be assertable in CI with *no* host present (all-fallback column green), or HEADLESS parity is a promise again.

**R10 — Tier provenance on every validated answer (secondary, cheap).**
Every answer records which tier rendered it, and tier 0 additionally records fall-through rate and "Other"-selection rate. This is the instrument for my H1 dissent: if Other-rate climbs on tier 0, the four-option projection is truncating expressiveness in practice regardless of what the fall-through rule says on paper. One ledger field, no new store; feeds R8's outcome accounting for free.

## Section 3 — Open mechanics

**D2 — routing label, not enum member.** D1's binding language ("local models start as a LOCAL tier") names the user-facing concept; D2 asks how to implement it, and the answer is outside the enum. Three reasons. First, mechanics: the tier enum is duplicated by design in four files plus the attune-rag mirror with a drift guard — a new member is five coordinated edits, and every exhaustive match over tiers everywhere must now handle LOCAL, including code paths (attune-rag ranking, spend gates, provider routing) that must *never* receive it; the drift guard would then be guarding a member whose absence from mirrors is the correct state. Second, semantics: CHEAP/CAPABLE/PREMIUM is a quality-cost ladder within one provider; LOCAL is an orthogonal placement/privacy/latency property, not a rung — a local model can be CHEAP-grade today and CAPABLE-grade next quarter without moving "where it runs." Third, expressiveness: a routing label (`placement: local` on the role's routing record) lets a role say "CHEAP, prefer local, fall back hosted," which an enum member structurally cannot say. Keep the enum three; add the label where R6's roles are routed.

**D3 — confirm no third capability contract, with a tripwire.** The two ruled contracts cover both phases of R6, and a provider-level contract is the general-Ollama-provider non-goal wearing a contract costume — it would recreate ModelProvider as a seam the day after deciding not to. Confirm the deferral. Tripwire for reopening: when a *second real* extension request arrives that fits neither contract without contortion (not a hypothetical in a spec — an implementer with code), reopen D3 with that implementer at the table. Contracts extracted from two concrete users are good; contracts designed for zero are speculation.

**Task 7 phasing — reranker ships alone, first.** The reranker is the first real second implementer of the extension seam, and the seam learns more from one honest implementer shipping end-to-end than from two batched. It is also the safest possible probe: optional capability, offline-evaluable against a no-rerank baseline, and recall is unchanged when the extension is absent — failure is invisible to users and visible to receipts. Phase B's workflow extensions exercise the *other* contract; batching them means seam feedback from two contracts arrives entangled and late. Ship A, run the seam retro, then cut B with whatever the seam taught. The only argument for waiting — one release event instead of two — buys nothing, since extensions are enabled per-user anyway.

## Section 4 — Dissent register

**H1 (tier 0 not a rival) — dissent on gravity, not mechanism.** The fall-through rule protects existing rich forms, but it cannot protect *future* forms: once tier 0 exists, authors will shape new questions to fit four options because the native widget is frictionless — design-to-the-projection. The richer constructs then atrophy not by degradation but by disuse. That is how a render target becomes a rival without any rule being broken. R10's Other-rate and fall-through telemetry is the tripwire; without it H1 is unfalsifiable.

**H2 (parity can be mechanical) — dissent on "identical validated output."** For single-question forms, byte-identical validated payloads across three renders is achievable and right. For stateful surfaces — the Fix workspace with revision, nonce, contract hash — byte identity across renders is false by construction. The gate must assert schema-identical validated payloads with nonce/revision fields normalized, or R2 either ossifies (no stateful surface can ever pass) or accumulates waivers (and a gate with waivers is a promise again).

**H3 (host remembers, Attune recalls) — dissent on the seat's answer to its own pushback.** "A corpus with no recall is the demo; recall is the product" is a slogan standing where a receipt should be. R3 hands every host a curated, one-line-per-lesson index — which materially improves the *host's* native retrieval over that corpus. The positioning survives only while relevance-ranked recall measurably beats grep-over-the-projected-index. By the contract's own standard, that claim needs a benchmark receipt (recall vs. host-notebook baseline on real lookups), or the seat should stop making it.

**H4 (role before seat) — dissent on fact-check probes.** Four of the five roles are genuinely low-stakes. Fact-check probes are not: a wrong local verdict that silently *passes* is worse than no probe, because it converts absence-of-signal into false assurance. If a probe's output ever gates anything, it must be advisory-labeled and countersigned by the hosted model; a local model may raise its hand, never wave things through.

**H5 (roster by role, not vendor) — dissent on the taxonomy's honesty.** The three role names are the current three vendors described from behind. The falsifiable test of roster-as-data: can the moderator slot be filled by a non-Claude recipe, or two slots by one vendor, with *no* gate edits? If the gates encode assumptions that make the answer no, R7 as shipped is a rename, not a refactor — and the golden-roster receipt I attached to R7 should be joined, later, by exactly that swap test before any fourth slot is entertained.

**On the seat's own register:** withdrawal (a) was correct and I confirm it. But note that R3's every-host projection still benefits hosts unevenly — the richest memory surface (Cowork's MEMORY.md + typed topics) extracts the most value from the same projection. Neutral output over unequal surfaces is not neutral outcome; that is precisely what R9's matrix exists to make visible rather than arguable.

---

**Follow-up question for the table:** What single receipt would the chair accept as proof that no host is privileged — the R9 matrix, the R2 gate, or something else — and can that receipt be produced in CI with no host present at all? If it cannot, HEADLESS parity is still a promise.

---

## Message 6 — claude · question (R9 member-originated, reply_to 5)

What single receipt would the chair accept as proof that no host is privileged — the R9 matrix, the R2 gate, or something else — and can that receipt be produced in CI with no host present at all? If it cannot, HEADLESS parity is still a promise.

---

## Message 7 — moderator · halt

spend gate reached: chair-ruled 3 seat invocations / 1 round complete; a second round needs a fresh chair go

---

## Message 8 — moderator · synthesis · round 1

# Moderator synthesis — round 1 (all three seats answered; spend gate reached)

## Unanimous (3/3)

- **D2 — LOCAL is a routing label, NOT a tier-enum member.** All three seats,
  independently, on the same grounds: locality is orthogonal to the
  quality/cost ladder; an enum member is five coordinated edits (four copies +
  attune-rag mirror) and forces every exhaustive tier match to handle a value
  most code paths must never receive. Codex: `execution=local|hosted`
  dimension. Antigravity: `ExecutionLocality` tag (`LOCAL_PREFERRED /
  LOCAL_REQUIRED / CLOUD_ONLY`). Claude: `placement: local` on the role's
  routing record, enabling "CHEAP, prefer local, fall back hosted". The seats
  read chair ruling D1a's "LOCAL tier" as naming the user-facing concept, not
  the enum mechanics.
- **D3 — confirm no third capability contract**, each with a reopening
  condition: Codex — revisit only after two independently implemented
  extensions demonstrably fit neither contract; Claude — tripwire fires on a
  second *real* implementer with code, who then sits at the table; Antigravity
  — confirm for 16.3, conditionally challenge in 16.4 with an
  Evaluator/Embedding seam if local models expand into embedding/scoring.
- **Task 7 — ship the Ollama reranker alone, first.** All three: it is the
  canary for the extension seam (discovery, optional capability advertisement,
  fallback, receipts, failure isolation), deterministic and offline-verifiable,
  and batching it with Phase B entangles seam feedback from two contracts.
- **R4 — ADOPT** as written (3/3). Claude seat: do it first — cheapest
  early-warning on the list. Codex: record both advertised-profile and
  fallback cases including stale revision, wrong hash, replay rejection.
- **Parity direction (chair's lean) — all three adopt**, and all three
  independently guard against the same failure mode, parity theater:
  Codex — enforce via a declared surface registry, not filesystem enumeration,
  plus explicit *expiring* parity exceptions; Claude — a drift-guarded
  `experiments:` allowlist with mandatory 14–30-day expiry (spikes may be
  untwinned; shipped surfaces may not); Antigravity — adopts because headless
  fidelity is the foundation of its own runtime, steelman recorded.

## Convergent amendments (compatible, near-unanimous)

- **R1 — parameterize tier 0 by host capability, don't hardcode Claude's
  4-option shape** (Antigravity AMEND + Claude AMEND; Codex ADOPT with
  capability detection + contract tests — same design). Antigravity's sharpest
  point: its own native `ask_question` supports multi-question forms, so
  clamping tier 0 to the Fable widget shape would covertly turn one vendor's
  limitation into the universal standard.
- **R3 — bound the projection** (Codex AMEND + Antigravity AMEND vs Claude
  ADOPT-with-notes). Converged shape: generated, sentinel-bracketed blocks
  (`ATTUNE:MEMORY:START/END`) with provenance headers; bounded top-K digest
  (Antigravity: ~25 entries, hit-frequency prioritized); per-host independent
  line budgets (Claude); stale-entry cleanup and removal support, not just
  regeneration (Codex); hand edits inside the block fail closed, edits outside
  stay legal. Codex explicitly rejects "second master" framing: Attune index
  stays authoritative, host files hold projections with provenance.
- **R5 — one master definition, host bindings generated from it** (Codex:
  host-neutral automation manifest compiled to host config or cron+CLI;
  Claude: the portable twin IS the definition, host task is a projection).
  Antigravity adds operational guards: no autonomous LLM sweeps on raw file
  events — deterministic triage probes only, ≥60s debounce, hourly
  circuit-breaker cap, explicit acknowledgment before token-intensive audits;
  telemetry writes must not retrigger their own monitor (loop prevention —
  Codex names the same loop).
- **R7 — roster as data, with stronger typing and a no-op proof** (3/3 adopt
  direction). Converged asks: typed role slots validated for invariants
  (exactly one moderator / plan-only reviewer / proposer — Antigravity,
  Claude); golden behavior test proving the default roster reproduces current
  literals byte-for-byte (Claude, Antigravity, Codex); model execution mode,
  trust boundary, capabilities and receipt obligations on the slot, not just
  a role name (Codex, echoed by Claude's H5 dissent); fourth-slot gating
  enforced in the loader, not prose (Claude), disabled-until-chair-go
  structural representation (Codex).
- **R8 — record raw counts and terminal outcomes** (Codex AMEND + Claude
  AMEND; Antigravity ADOPT). Codex: count asks per *terminal* outcome so
  abandoned/blocked sessions don't vanish; report zero-outcome rate. Claude:
  store raw numerator/denominator (ratio is gameable by outcome inflation),
  keep asks-per-session as a secondary guard, minimum-outcomes floor before
  friction_gate acts. Compatible; union is the amendment.
- **R2 mechanics split (the one real disagreement inside a shared direction):**
  Codex would replace filesystem enumeration with a declared surface registry
  ("scanning is too easy to evade accidentally"); Claude keeps the gate but
  fixes the receipt clause to "schema-identical validated payload" with
  nonce/revision normalized (byte identity is false by construction for
  stateful surfaces); Antigravity adds interaction-lifecycle parity (abort,
  timeout, validation feedback), arguing output identity alone is
  insufficient. These compose: registry-driven gate + payload-schema receipts
  + lifecycle assertions — but the chair should rule the enforcement locus.

## The seats' own proposals converge on one missing layer

All three independently invented a **capability-descriptor / conformance
layer**: Codex R9 (machine-readable capability descriptor per host adapter +
shared conformance suite proving deliberate degradation, receipt provenance,
no silent privileged-host selection — "portability as a testable protocol,
the foundation minor"); Claude R9 (`attune surfaces doctor` probe + generated
hosts×capabilities matrix, drift-guarded, assertable in CI with no host
present); Antigravity's R1 capability descriptor is the same object. This is
the strongest signal of the round: the table believes the missing enforcer of
"no privileged surface" is a *declared, testable capability contract per
host*, not more twins.

Seat-unique proposals: Antigravity R9 — typed review-finding interchange
(SARIF-conformant) projecting attune audit findings into Fable review cards,
GitHub PR threads, IDE diagnostics, and a headless SARIF stream, with
round-trip receipts; Antigravity R10 — advisory worktree leases + turn
attestation receipts (anti-seat-simulation); Claude R10 — tier provenance +
Other-rate/fall-through telemetry as the falsifier for H1's "not a rival"
claim.

## Dissent worth the chair's eyes

- **H3 is the most-dissented hypothesis.** Codex: bounded projections or you
  get context pollution and prompt-authority confusion. Antigravity: index
  lines tax every subagent turn; plain hosts hallucinate following raw
  pointers. Claude seat (against its own proposer): "recall is the product"
  is a slogan where a receipt should be — demand a benchmark (recall vs
  host-notebook baseline) or stop making the claim.
- **H4 split:** Antigravity dissents on principle — seat eligibility should be
  benchmark-receipted, not provider-dogma; an air-gapped 70B is a legitimate
  plan-only reviewer. Codex and Claude hold the advisory-only line, both
  flagging fact-check/skeptic probes as the danger: a weak local model
  manufacturing the *appearance* of independent verification; a silent local
  pass is worse than no probe (must be advisory-labeled + hosted-model
  countersigned).
- **H5:** Claude's falsifiable test — can the moderator slot take a non-Claude
  recipe with zero gate edits? If not, R7 is a rename, not a refactor.

## Open member questions (round 2 material, needs fresh chair go)

1. (Antigravity, msg 4) What cryptographic receipt schema proves a host-UI
   resolution was executed by the authorized human chair rather than a host
   subagent simulation?
2. (Claude, msg 6) What single receipt does the chair accept as proof no host
   is privileged — and can it be produced in CI with no host present?

## Moderator read (effort for the next two minors)

16.3: R4 receipt (first), the merged capability-descriptor/conformance
foundation (three-way R9 convergence), R1 with the host-profile amendment,
D2 as routing label, Task 7 reranker alone. 16.4: R3 bounded projection, R5
single-master automation templates, R7 roster-as-data with golden receipts,
Phase B workflow extensions, R8. The release is a tailwind exactly where the
table converged: the host is a projection target and a distribution channel;
Attune's defensible layer (Codex's phrasing) is cross-host semantics,
validation, policy, receipts, reproducibility.
