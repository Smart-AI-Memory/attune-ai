# Safe Parallel Task Execution Across Multiple LLMs — Research & Planning Packet

**Version 2.1** (revised after two adversarial review rounds; preconditions P1 and P2 now **answered from source** — see §0.5).
**Status:** research only. No implementation authority requested or granted.
**Prepared:** 2026-09-02. **Repository state inspected:** `main` @ `78661a787`, **4 commits behind `origin/main`** — see the staleness caveat in §0.3.
**Operating principle under test:** *Parallel evidence and controlled mutation; serialized authority and integration.*

**Classification legend** — every substantive statement carries one:
`[VEF]` verified external fact (the cited source *states* this) · `[VRF]` verified repository fact (observable at a named path) · `[INF]` inference · `[PROP]` proposal.

**Access date for every external source: 2026-09-02.**

---

## 0. Review record

### 0.1 What happened

v1 of this packet was reviewed adversarially by a separate agent running on the `fable` model, briefed to find what was wrong rather than to praise. **Its verdict on v1 was "No — not signable as a basis for the decision."** It raised 9 BLOCKERs, ~22 MAJORs and ~14 MINORs. That verdict was correct, and the most damaging finding was one the packet's own classification scheme was supposed to prevent: a load-bearing `[VRF]` about budget safety that was wrong in the direction that mattered.

A caveat on the review's provenance, in the spirit of D3 below: the reviewing agent was requested on the `fable` model. **I cannot verify it was "Fable 5.1" specifically** — model identity is selected by parameter and not confirmable from inside the session. Treat the review as "a second model, different from the author's, adversarially briefed", which is what actually matters for its value, and not as an attested model version. This is the same failure mode D3 legislates against, appearing in the packet's own production process.

### 0.2 The nine blockers and what changed

| # | Blocker | Resolution in v2 |
|---|---|---|
| 1 | Session spend ledger claimed as concurrency-safe for *budget enforcement*. The cited code prevents a **lost record**, not a **cap overrun** — N launchers each reading "sum < cap" is a TOCTOU. Also: `codex` and `agy` bill to other accounts and may never enter the ledger at all. | §2 row rewritten and split; §5 `budget` demoted to `[PROP]`; new blocker-class risk in §4A; **new P0 probe** and a gating item in §8. The cap governs at most one of three seats — this is now stated. |
| 2 | The ADOPT case for Architecture A **conflated two modules**. The deterministic synthesizer is in `diagnosis/panel.py`; the sequential seat loop is in `roundtable/routine.py`. Nothing verified that routine.py seats are independent of *earlier seats' board posts* — and "promoted board messages" suggests they are not. | §1 and §4A rewritten. Split into two `[VRF]`s plus an explicit unknown. **E1 is now gated on a P0 probe** (§3 A0) establishing seat-input independence. If seats read siblings' posts, parallelising changes the product and A is not "already built minus the parallelism". |
| 3 | Read-lane success criterion "byte-identical promoted content" is **unmeetable** — the seats are CLI subprocesses with no seed control, so two *sequential* runs differ too. The one confident recommendation could only ever fail its own test. | §8.5 rewritten: parallel-vs-sequential divergence is compared against a **sequential-vs-sequential noise floor**, on a structural measure (finding set, ranks), not bytes. |
| 4 | Control arm was **one seat**, but the status quo is **three seats sequentially**. Biased every comparison toward the parallel arm and confounded provider diversity with parallelism. | §8.2 rewritten. Baseline is the current three-seat sequential round table. Provider assignment for write lanes is now stated (and it forced an admission — see §0.4). |
| 5 | `stale` defined as inadmissible ⇒ **at most one write lane can ever integrate**, since lane 3 integrating makes lane 4 stale. Directly defeats Architecture B, and contradicted §7's own "rerun at the integration base". | §7 and §9 rewritten: stale is a **flag requiring re-verification**, with an explicit re-apply policy (clean apply at integration HEAD ⇒ rerun; else ⇒ serialize). |
| 6 | Two contradictory crash policies, and neither addressed **orphaned lanes** — subprocesses that outlive the orchestrator, keep spending, and keep writing to worktrees whose reservations no longer exist. | §7 gains an explicit orphan failure mode and mechanism; §8.3 injection updated. One policy chosen. Platform stated. |
| 7 | Cooperative cancel + **immediate** reservation release recreates exactly the split-brain the packet uses to reject leases. | §7: reservations release only on **confirmed process exit (`waitpid`)**, never on cancel-intent. |
| 8 | Decision register D5 carried an **unsourced `[VEF]`** ("lane-authored tests are the single largest reason agent PRs go unmerged"). | Relabelled `[INF]`, sourced to the partially-verified arXiv:2602.00164 with its verification caveat carried over, and D5's argument weakened accordingly. |
| 9 | Idempotency key and retry policy are **mutually exclusive** as written: Stripe semantics return the cached *failure* for a same-key retry, so the specified retry is impossible. | §5: `attempt` added to the key; Stripe semantics scoped to result delivery, not lane execution. |

### 0.3 Standing caveats the review forced into the open

- **Every `[VRF]` is against a branch 4 commits behind `origin/main`.** The absence claims are the exposed ones — "no OpenAI or Gemini SDK adapter exists", "no `merge_group:` trigger", "no production caller of ghosts". Any of the 4 missing commits could invalidate these. **Fetch and re-verify the absence claims before acting on §10.**
- **`docs/specs/shared-command-workspaces/` is untracked** in a working tree with 7 modified and 7 untracked paths. It is a working-tree observation, not a repository fact, and its authorship is unconfirmed. Everything built on SCW-2 inherits that. Relabelled throughout.
- **Estimates like "~70% of B exists" and "~80% of the receipt is specified" are `[INF]`**, not `[VRF]`. Corrected.
- **Version/date claims I could not confirm from my own knowledge** are marked *suspect, verify* in §11 rather than asserted: the MCP `2026-07-28` revision and SEP-2663 "Final" status, A2A v1.0 dating, OTel semconv v1.44.0 and the genai repo split, and the MAST framework count.

### 0.4 What the review changed in the *conclusion*, not just the prose

Two substantive shifts, both toward less confidence:

1. **Architecture A moves from ADOPT to ADOPT-PENDING-PROBE.** The recommendation was resting on a module conflation. If routine.py seats read each other's board posts, the round table is not a fan-out at all — it is a relay, and parallelising it changes the output rather than the schedule. That is a one-hour check and it must happen first.
2. **The "cross-agent" premise for write lanes is not currently instantiated.** `PLAN_ONLY_SEATS = frozenset({"antigravity"})` `[VRF]`, so only `claude` and `codex` can write. The dogfood's write pair is therefore a 2-provider experiment, and the 41.7% cross-agent conflict figure — which the review correctly identified as a population mismatch anyway — cannot be cited as the applicable prior. Both corrections are now in §2 and §8.

**Also newly flagged as a cheaper alternative the packet never considered** (review's point, and it is a good one): if seat correlation is as high as the evidence suggests, **dropping a seat** cuts cost with a similar wall-clock effect and none of the concurrency risk. This is now an explicit option in D1 rather than an unexamined assumption that three seats are fixed.

### 0.5 Second review round — and the two preconditions, answered

The revised packet went back to the same reviewing agent. **Verdict moved from "No" to "Yes with the remaining BLOCKERs fixed"**: 4 of 9 blockers closed outright, 5 partially closed, none open, with the residue confined to §8's decision procedure and three mechanism details. Its sharpest point was not about evidence at all:

> *"A packet whose headline recommendation is conditional on a fact it could have supplied is asking Patrick to decide with less information than the author had access to."*

That was correct. **P1 and P2 have now been answered by reading the source**, and both answers change the packet.

**P1 — seat independence: CONFIRMED, and the round table is a fan-out.** `routine.py:338` computes `brief = BRIEF_PREAMBLE + question` **once, before the loop**, and line 362 passes that same `brief` to every seat. `BRIEF_PREAMBLE` says verbatim: *"You are one seat at a three-model round table (Claude, Antigravity, Codex)… **Answer independently**… do not run tools, write files, or take actions."* Seats `post_message` to the board but never read sibling posts `[VRF]`. **Parallelising the seat loop cannot change any seat's input.** Architecture A's premise holds.

**But P1 also overturned a v1/v2 claim in the other direction.** I had said the round-table synthesis was deterministic, borrowing that from `panel.py`. It is not — `routine.py:381–389` builds a `synthesis_brief` and makes **another `claude` LLM call** to produce the digest `[VRF]`. `panel.py` is deterministic and *"never a further LLM call"*; `routine.py` does the opposite. So the packet was wrong about routine.py twice, in opposite directions, and only reading it settled either. Three consequences, all now in the design:

1. Round-table output is **non-deterministic regardless of parallelism**. This independently confirms that byte-identity was never an achievable criterion, and makes the §8.2 noise-floor arm mandatory rather than merely prudent.
2. `positions` is built by **append order** `[VRF]`. Under concurrency, seats finish in nondeterministic order, so the synthesis prompt's section ordering would change — **injecting a new source of variance that has nothing to do with the seats' content**. The parallel implementation must sort `positions` into canonical seat order before building `synthesis_brief`. This is the single most important implementation constraint the probe surfaced, and neither review round predicted it.
3. `invocations` / `spec.max_invocations` is a check-then-increment that becomes a race under concurrency `[VRF]`.

**P2 — the budget cap: the blocker is confirmed, and it is now `[VRF]`, not `[INF]`.** `default_invoke_seat`'s docstring states it outright: *"a `claude` seat bills the Anthropic API key on CLI-spawned runs, so the ledger is checked BEFORE the subprocess spawns… **`codex`/`agy` seats bill other providers and are neither checked nor recorded (R4)**."* The code matches: `billed = recipe[0] == "claude"` gates both the `check` at line 250 and the `record` at line 259 `[VRF]`. And the shape is textbook check-then-act — `check` → spawn (long) → `record` — so under concurrency N billable launches can all pass the check before any records `[VRF]`.

**One correction in Attune's favour, which v2 got wrong by over-correcting.** v2 warned that a 3-seat fan-out "spends 3× against a cap that may not hold". In the round table it does not: only the `claude` seat is billable, so a read fan-out is **one** billable seat plus **one** billable synthesis call — two, not three, and the TOCTOU window admits at most one extra. The estimate is also deliberately conservative, *"so it overcounts rather than undercounts"* `[VRF]`. **The read-lane budget risk is materially smaller than v2 claimed.** The write-lane risk is not: dogfood lanes 4, 6 and 7 are all `claude` and do race.

---

## 1. Executive recommendation

**Proceed to a controlled dogfood, in two stages. The precondition that gated this recommendation has now been checked, and it cleared.**

**Stage one is read-lane parallelism, and it is the confident recommendation.** The seat loop is sequential today — `routine.py:349` is a plain `for seat, recipe in SEAT_RECIPES:`, and no module under `roundtable/` contains a single concurrency primitive `[VRF]`. The seats are genuinely independent: one `brief` is built before the loop and handed identically to all three, the preamble instructs each to *"Answer independently"*, and no seat reads another's board post `[VRF]` (§0.5). So parallelising changes the schedule and not the product — which was an assumption in v1 and v2, and is now a verified fact. Read lanes touch nothing: no worktree, no branch, no reservation, no merge. The failure taxonomy already exists (`SEAT_ABSENT`, `BUDGET_EXHAUSTED` in `panel.py` `[VRF]`). The risk is bounded by construction rather than by policy, which is the only kind of bound worth relying on.

**Two things stand between that and an implementation, both discovered by actually reading the code rather than reasoning about it** (§0.5). The synthesis step is itself an LLM call, so the round table's output is non-deterministic *today*, before any parallelism — which means success can only be defined against a measured run-to-run noise floor, never against byte-identity. And `positions` is assembled in seat-completion order, so concurrency would silently reorder the synthesis prompt and inject variance unrelated to seat content; the implementation must sort into canonical seat order. Neither review round predicted that second one.

**The budget gate is real but smaller than v2 feared.** `codex` and `agy` seats *"are neither checked nor recorded"* `[VRF]`, so the $10 session cap governs exactly one of three seats, and the cap check is a check-then-act race `[VRF]`. For a read fan-out that means two billable calls (the `claude` seat plus the synthesis) against a conservative, deliberately-overcounting estimate — a bounded exposure. For write lanes, where every dogfood lane is `claude`, it is not.

**Stage two — write lanes — is an experiment to characterise failure, not to harvest speed.** The strongest single number available is Geng & Neubig's isolation ablation: worktree isolation 63.3%, shared-workspace soft isolation 55.5%, single agent 57.2% `[VEF]`. The direction is what matters; the 1.7-point gap between soft isolation and single-agent is small, reported without a confidence interval in the material available to me, and comes from one method on two benchmarks — so "unisolated concurrency is actively worse than not doing it" is `[INF]` and should not be leaned on `[review finding]`. What the same paper reports without ambiguity is less flattering to the whole enterprise: **runtime increased** (2080s vs 1803s), cost rose 2–3×, and performance degraded past four concurrent engineers `[VEF]`.

The vendors point the same way. Anthropic's own multi-agent post — the strongest pro-parallel artifact in existence — scopes coding out of its own result: *"Most coding tasks involve fewer truly parallelizable tasks than research"* `[VEF]`. Google's guidance is blunter: *"Exercise caution with parallel subagents for tasks that require heavy code edits"* `[VEF]`. And Anthropic's 16-Claude C-compiler run, which is the best existence proof there is, hit precisely the failure this design must survive: on the kernel, *"every agent would hit the same bug, fix that bug, and then overwrite each other's changes"* — solved only by an artificial task-splitter backed by an unusually strong oracle `[VEF]`.

**Strongest counterargument to my own recommendation.** The binding constraint is not model wall-clock — it is Patrick's review throughput, and parallelism attacks the wrong resource. METR's RCT found experienced developers on mature repositories were **19% slower** with AI assistance while forecasting 24% faster `[VEF]`; that study measured single-agent assistance, not parallel lanes, so it belongs here as an argument about the *bottleneck's location* and not as evidence about parallelism `[review finding]`. DORA 2025 found AI adoption positively related to throughput and negatively related to delivery stability `[VEF]`. One lead already owns synthesis and central receipt reruns; N lanes multiply the artifact stream feeding that single serialized human. If that is right, the correct move is not parallel lanes — it is better receipts, fewer and higher-yield lanes, and possibly *dropping* a seat rather than parallelising three.

**§8 is designed so that this counterargument can win.** Integration rework and human intervention are primary metrics with pre-registered definitions, and the reject thresholds fire on them.

---

## 2. Evidence table

Rows marked **⚠** carry a correction from the v2 review. Applicability columns state what the source can bear, not what would be convenient.

| Claim | Class | Primary source | Date | Applicability | Limitation |
|---|---|---|---|---|---|
| Worktree isolation 63.3% / soft isolation 55.5% / single agent 57.2% | VEF | [arXiv:2603.21489](https://arxiv.org/html/2603.21489) Geng & Neubig, CMU | v2 2026-07-08 | Supports isolation as *directionally* load-bearing | ⚠ No CI available to me; 1.7pt soft-vs-single gap may be noise. "Unisolated is worse than single" is **[INF]**, not settled |
| Degradation past ~4 concurrent engineers (Commit0-Lite), past ~2 (PaperBench); wall-clock "not substantially reduced"; cost 2–3× | VEF | same | 2026-07-08 | Caps write-lane count; the cost/runtime figures are the honest counterweight | ⚠ Measured on *write* engineers sharing a repo. Does **not** transfer to read-only lanes with no shared state |
| Multi-agent research uplift 90.2%; coding explicitly scoped out | VEF | [Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system) | 2025-06-13 | The 90.2% may not be cited for coding — its own source forbids it | Vendor-authored; undisclosed n; research eval |
| 16 parallel Claudes → 100k-line C compiler; but *"every agent would hit the same bug… and then overwrite each other's changes"* | VEF | [Anthropic Engineering](https://www.anthropic.com/engineering/building-c-compiler) Carlini | 2026-02-05 | Existence proof **and** the exact failure B must survive | n=1; greenfield; exceptional oracle (GCC + torture suites) |
| *"Exercise caution with parallel subagents for tasks that require heavy code edits."* | VEF | [Google Developers Blog](https://developers.googleblog.com/subagents-have-arrived-in-gemini-cli/) | 2026-04-15 | Only vendor rule on concurrent writes, and it is "don't" | Vendor guidance, unmeasured. ⚠ Date *suspect, verify* |
| Concurrent agent PRs conflict textually 19.8% intra-agent / 41.7% cross-agent; 42% structural | VEF | [arXiv:2607.04697](https://arxiv.org/abs/2607.04697) | 2026-07-06 | ⚠ **A prior for *unpartitioned* concurrent work only.** Declared-disjoint write sets remove textual conflict by construction, and this paper *excludes* semantic conflicts — so it is neither the risk B removes nor the residue B leaves | Preprint; replayed merges. ⚠ v1 cited it as both; that was wrong |
| 27.67% of agent PRs conflict; Claude Code 25.93%, Codex 31.85% | VEF | [arXiv:2604.03551](https://arxiv.org/html/2604.03551v2) | v2 2026-05-12 | Per-seat prior, same unpartitioned caveat | Preprint; simulated merges |
| Independent architectures amplify trace errors 17.2×; centralized coordination contains to 4.4× | VEF | [arXiv:2512.08296](https://arxiv.org/abs/2512.08296) | v3 2026-04-08 | ⚠ "Centralized" there is a **coordinator-agent architecture on largely non-coding traces**. Mapping it to "Patrick reruns pytest" is **[INF]**. Central rerun stands on its own merits | Preprint; R²=0.373 |
| Diminishing returns above ~45% single-agent accuracy; tool-heavy penalty β=−0.096, p=0.002 | VEF | same | 2026-04-08 | Coding agents are definitionally tool-heavy | ⚠ v1 said returns "go negative" and asserted Attune is above threshold. The source says *diminishing*; Attune's baseline accuracy is **unmeasured** |
| MAS failure rates 41%–86.7% across open-source frameworks; ~17.3% of traces show verification failures | VEF | [arXiv:2503.13657](https://arxiv.org/abs/2503.13657) MAST | v3 2025-10-26 | Failure taxonomy input to §7 | Frameworks weaker than frontier harnesses. ⚠ Framework count *suspect, verify* |
| *"many communication and coordination failures in MAS are fundamentally concurrency control problems"* | VEF | [arXiv:2608.18092](https://arxiv.org/html/2608.18092) | 2026-06-06 | Frames C as a database problem | Position paper; re-aggregates others' numbers |
| Coding agents co-fail **3.7× more than independence predicts**; 81/146 cross-*language* pairs at φ=1 | VEF | [arXiv:2606.20158](https://arxiv.org/html/2606.20158) KTH | 2026-06-18 | Kills "different families ⇒ independence" (D) | Preprint; algorithmic tasks, not repo maintenance |
| 9 judges across 7 families ≈ **2.18 effective voters**; panel 72.0% vs best single 71.8% | VEF | [arXiv:2605.29800](https://arxiv.org/html/2605.29800v1) Apple | 2026-05-28 | Argues against **seat count**, not against parallelising the seats you have | ⚠ NLI/reward benchmarks; transfer to code review is [INF] |
| Experienced OSS devs 19% slower with AI; forecast 24% faster, post-hoc estimate 20% faster | VEF | [METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) / [arXiv:2507.09089](https://arxiv.org/abs/2507.09089) | 2025-07-10 | ⚠ **Bottleneck-location evidence only.** Single-agent assistance, early-2025 models — not evidence about parallel lanes | n=16 devs, 246 tasks; CI not published |
| AI adoption: positive on throughput, negative on delivery stability | VEF | [DORA 2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report) | 2025-09-23 | Predicts where lanes hurt | Self-reported, correlational |
| Worktrees share the object DB, refs, config, hooks, `info/`, **stash** | VEF | [git-worktree](https://git-scm.com/docs/git-worktree), [gitrepository-layout](https://git-scm.com/docs/gitrepository-layout) | no date shown | Core of C | ⚠ Per-worktree set is larger than v1 said — also `refs/bisect`, `refs/worktree`, `refs/rewritten`, `MERGE_HEAD`. And **`extensions.worktreeConfig` makes config per-worktree** — a mitigation v1 omitted |
| *"users who run commands concurrently have to live with some risk of corruption"* (concurrent gc, shared object DB) | VEF | [git-gc](https://git-scm.com/docs/git-gc) NOTES | no date shown | Motivates `gc.auto=0` | ⚠ Git's own hedge is "low in practice"; default prune expiry is two weeks, which lane work is not. Threat was overstated in v1 |
| `.git/config.lock` is `O_CREAT\|O_EXCL` with no retry; lane spawn contends | INF | [claude-code#34645](https://github.com/anthropics/claude-code/issues/34645), closed not-planned | 2026-03-15 | Serialize lane spawn | ⚠ **Demoted from VEF.** A third-party bug report is not a fact about git internals, and the stated mechanism (`worktree add` writing `.git/config`) is *suspect, verify* — it normally writes `.git/worktrees/<id>/*`. Serializing spawn may be right for other reasons |
| *"It is NOT recommended to make multiple checkouts of a superproject"* | VEF | [git-worktree](https://git-scm.com/docs/git-worktree) BUGS | no date shown | Gate before adopting B | — |
| Merge queue exists because green-individually ≠ green-together | VEF | [GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) | no date shown | Named remedy for semantic conflict | Requires `merge_group` wiring |
| Bazel: *"An artifact… must only be generated by at most one action"* — overlap is a plan-time error | VEF | [Bazel glossary](https://bazel.build/reference/glossary) | no date shown | ⚠ **Precedent for, not proof of**, declared write sets — it holds under hermetic sandboxing with fully declared inputs, which LLM lanes with subprocess access do not have | Needs `exclusive` for ports/DBs |
| `merge=union` on a lockfile merges silently and incoherently; uv "should not be edited manually"; Cargo's fix is reset-and-regenerate | VEF | [gitattributes](https://git-scm.com/docs/gitattributes), [uv layout](https://docs.astral.sh/uv/concepts/projects/layout/), [Cargo FAQ](https://doc.rust-lang.org/cargo/faq.html) | no date shown | §6 Class 3 | npm/Poetry guidance undocumented |
| MCP Tasks: `working \| input_required \| completed \| failed \| cancelled`; terminal states immutable | VEF | [SEP-2663](https://modelcontextprotocol.io/seps/2663-tasks-extension) | rev 2026-07-28 | Borrowed in §7 | ⚠ Revision date and "Final" status *suspect, verify* |
| MCP progress: `progress` MUST increase monotonically even when `total` is unknown; MUST stop after completion | VEF | [MCP progress](https://modelcontextprotocol.io/specification/2026-07-28/basic/utilities/progress) | 2026-07-28 | §9 rule 1. ⚠ *Added — cited in v1 body without a table row* | — |
| MCP tools: annotations are **untrusted**; there SHOULD be a human in the loop able to deny invocations | VEF | [MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | 2026-07-28 | §8.6. ⚠ *Added* | — |
| A2A TaskState is 9 SCREAMING_SNAKE values incl. `AUTH_REQUIRED`, `REJECTED` | VEF | [a2a.proto](https://raw.githubusercontent.com/a2aproject/A2A/main/specification/a2a.proto) | v1.0 2026-03-12 | Rejected in §7 | ⚠ Dating *suspect, verify*; v1.0.1 date unresolved |
| Temporal: *"the Activity may be executed multiple times and may even partially complete more than once"* | VEF | [Temporal](https://docs.temporal.io/activity-definition) | no date shown | Why durable-execution engines are rejected | Rolling docs |
| Stripe idempotency: cache the full outcome incl. failure; same key + different params is an **error**; 24h retention | VEF | [Stripe](https://docs.stripe.com/api/idempotent_requests) | no date shown | §5 — ⚠ and the reason v1's retry policy was incoherent | `Idempotency-Key` IETF draft-07 **expired**, never an RFC |
| Chubby: locks are advisory; a **sequencer** validated at the resource is what makes a lock sound; `lock-delay` covers the dead-holder case | VEF | [Chubby, OSDI 2006](https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/) | 2006 | §6 rejection of leases. ⚠ *Added — cited in v1 body without a row.* Gray & Cheriton body not retrieved; no lease mechanics quoted from it | — |
| `flock` is **kernel-held and released on process death**; a hand-rolled lock *file* is the thing that leaks on SIGKILL | VEF | [flock(2)](https://man7.org/linux/man-pages/man2/flock.2.html) | page updated 2026-02-08 | ⚠ **Corrects v1**, which said "lock files leak on SIGKILL" in a way that read as applying to `flock`. It does not | Advisory only; unreliable over NFS |
| OTel GenAI is `Development`; `gen_ai.system` renamed to `gen_ai.provider.name`; **no cost attribute exists** | VEF | [semconv-genai](https://github.com/open-telemetry/semantic-conventions-genai) | semconv v1.44.0 | §9 field names | ⚠ Version and repo split *suspect, verify* |
| Claude Code emits `tool_decision`, `permission_mode_changed`, `commit.count`, `cost.usage`; **no per-egress-destination event** | VEF | [monitoring-usage](https://code.claude.com/docs/en/monitoring-usage) | no date shown | §8.6 item 6. ⚠ *Added* | Not framed by the vendor as an audit facility |
| Claude Code permission deny rules do **not** cover arbitrary subprocesses: *"For OS-level enforcement… enable the sandbox"* | VEF | [permissions](https://code.claude.com/docs/en/permissions) | no date shown | §8.6 item 3. ⚠ *Added* | — |
| Gemini CLI: *"`excludeTools`… is not a security mechanism and should not be relied upon"* | VEF | [Gemini CLI config](https://google-gemini.github.io/gemini-cli/docs/get-started/configuration.html) | no date shown | §5 allowlist-not-denylist. ⚠ *Added* | — |
| Lethal trifecta; *"we still don't know how to 100% reliably prevent this"* | VEF | [simonwillison.net](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) | 2025-06-16 | Egress is the amputable leg | Practitioner analysis |
| 12 injection defenses broken at **ASR >90%**; 8 agent defenses at >50% | VEF | [arXiv:2510.09023](https://arxiv.org/abs/2510.09023), [arXiv:2503.00061](https://arxiv.org/abs/2503.00061) | 2025-10-10 / 2025-02-27 | Prompt-level lane rules are decorative | Adaptive-attack setting |
| Nx s1ngularity: malware invoked installed Claude Code / Gemini CLI / Amazon Q with `--dangerously-skip-permissions`, `--yolo`, `--trust-all-tools`; harvested `.env`, SSH keys, tokens **from the home directory** | VEF | [Wiz](https://www.wiz.io/blog/s1ngularity-supply-chain-attack) | 2025-08-27 | ⚠ The **home directory** detail is why v1's repo-scoped containment was insufficient | Vendor research blog |
| GitHub MCP: public-issue injection exfiltrated **private** repos into a public PR; *"GitHub alone cannot resolve this… through server-side patches"* | VEF | [Invariant Labs](https://invariantlabs.ai/blog/mcp-github-vulnerability) | 2025-05-26 | Why push/PR stays a human gate | Vendor research blog |
| Claude Code sandbox: isolation *"reduces the impact of a breach, but it does not eliminate risk"*; built-in Bash sandbox does **not** cover MCP servers or hooks | VEF | [sandbox-environments](https://code.claude.com/docs/en/sandbox-environments) | no date shown | §8.6 | — |
| CaMeL: provable security at **77% vs 84%** undefended | VEF | [arXiv:2503.18813](https://arxiv.org/abs/2503.18813) | 2025-03-24 | Architectural containment costs ~7 points | No droppable implementation for these CLIs |
| Agent PRs go unmerged most often for **test failures**, then **prior resolution by another PR** | INF | [arXiv:2602.00164](https://arxiv.org/abs/2602.00164) | date unconfirmed | D5. ⚠ **Demoted from an unsourced VEF in v1.** Sample sizes and top-two reasons rendered; authors, date and overall rate did **not** | Partially verified only — do not quote a percentage |
| Round table is **fully sequential**: `for seat, recipe in SEAT_RECIPES:` at `routine.py:349`; zero concurrency primitives under `roundtable/` | VRF | `src/attune/roundtable/routine.py` | — | The available win | — |
| **Round-table seats are independent.** `brief` is built once at `routine.py:338` and passed identically to every seat at :362; `BRIEF_PREAMBLE` instructs *"Answer independently… do not run tools, write files, or take actions"*; seats post to the board but never read sibling posts | VRF | `src/attune/roundtable/routine.py:108–114, 338, 362` | — | ⚠ **P1 answered.** Parallelising cannot change seat inputs — Architecture A's premise holds | — |
| **Round-table synthesis is another `claude` LLM call**, not deterministic | VRF | `routine.py:381–389` | — | ⚠ **Reverses a v1/v2 claim.** Output is non-deterministic *before* any parallelism ⇒ the noise-floor arm is mandatory | — |
| **`positions` is built in seat-completion order**; `invocations`/`max_invocations` is check-then-increment | VRF | `routine.py:355–378` | — | ⚠ Under concurrency both become races. Must sort to canonical seat order before synthesis | Neither review round predicted this |
| `panel.py`: independent seats over one bounded pack, *"seats never run tools"*, moderator synthesis **deterministic — never a further LLM call** | VRF | `src/attune/diagnosis/panel.py` | — | Verified for **panel.py only** — and it is the *opposite* of routine.py | ⚠ v1 attributed this to the round table. It does not follow |
| `SEAT_RECIPES` = `claude` / `agy --mode plan` / `codex exec`; `PLAN_ONLY_SEATS = {antigravity}`; seats are **CLI subprocesses** | VRF | `roundtable/routine.py:95` | — | ⚠ Only **two** seats can write. The "cross-agent" write premise is a 2-provider premise | — |
| Only provider adapter is Anthropic; no OpenAI or Gemini class | VRF | `src/attune/llm/providers/` | — | Heterogeneity is process-level | ⚠ Absence claim against a branch 4 behind |
| Ghost Simulator implements per-lane worktrees at `.attune/ghosts/<id>` with ff-only promotion; runner is *"sequentially in-process"*; no production caller | VRF | `src/attune/orchestration/ghosts/` | — | Reusable lifecycle | ⚠ Promotion is **commit-based**, so it does *not* apply to diff-returning lanes. "~70% exists" was **[INF]** and is withdrawn |
| Base-SHA pinning exists: `head_sha`, `merge_base`, stale comparison; *"a report, not a go signal"* | VRF | `src/attune/handoff/verify.py:72–87,124` | — | Answers B2 with shipped code | — |
| `FixReceipt` carries `attributed_changes`, `pre_existing_dirty`, `scope_violations`, `probe_outcomes`, `scope_verified`; success requires all probes PASS **and** no scope violations — *"never from workflow exit"* | VRF | `src/attune/cli_commands/fix_receipt.py` | — | Receipt precedent | ⚠ "~80% specified" was [INF] and is withdrawn |
| Session ledger **append** is race-safe: *"no read-modify-write race can lose a spend record under concurrent launchers"*; `DEFAULT_CAP_USD = 10.0`; hard refusal | VRF | `src/attune/gates/session_ledger.py` | — | Recording is safe | — |
| **Cap enforcement is check-then-act**: `check` at `routine.py:250` → subprocess spawn → `record` at :259 | VRF | `routine.py:248–259`, `session_ledger.check` | — | ⚠ **P2 answered — promoted from INF.** N billable launches can all pass the check before any records | — |
| **`codex`/`agy` seats *"bill other providers and are neither checked nor recorded (R4)"*;** `billed = recipe[0] == "claude"` gates both calls | VRF | `routine.py` `default_invoke_seat` docstring + body | — | ⚠ The cap governs **exactly one of three seats** — stated by the code, not inferred | — |
| Seat spend estimate is flat and *"deliberately above the typical… cost, so it overcounts rather than undercounts"* | VRF | `session_ledger.seat_estimate_usd` | — | ⚠ **Corrects v2's over-warning.** A read fan-out is 2 billable calls (seat + synthesis), conservatively estimated — a bounded exposure, not 3× against a broken cap | Write lanes are all `claude` and do race |
| SCW-2 specifies revision + nonce + contract digest; *"Stale, altered, replayed, unknown, or concurrent actions fail closed"* | working-tree observation | `docs/specs/shared-command-workspaces/requirements.md` | 2026-08-31 | Authority model precedent | ⚠ **Demoted from VRF** — untracked file in a dirty tree, authorship unconfirmed |
| 36 worktrees registered, 35 prunable; 23 under `.claude/worktrees/` | VRF | `git worktree list` | 2026-09-02 | Sprawl is already live | ⚠ Interacts badly with denying `.claude/**` — see §8.6 |
| No `merge_group:` trigger; merge automation is label-gated + fail-closed guard | VRF | `.github/workflows/` | — | No semantic-conflict defense today | ⚠ Absence claim against a stale branch |
| `attune-forms` extracted to a standalone PyPI package by chair decision D4 | VRF | `docs/specs/workflow-intake-forms/decisions.md` | 2026-08-12 | The proven extraction path | ⚠ The *cost* of that extraction is unknown — see D7 |

---

## 3. Research-question matrix

⚠ **A0 is new and gates everything else.**

| # | Question | Current evidence | Hypothesis | Falsifying probe | Priority |
|---|---|---|---|---|---|
| **A0** | Are routine.py seats independent? | ✅ **ANSWERED.** One `brief` built before the loop, passed identically to all seats; preamble says *"Answer independently"*; no seat reads sibling posts `[VRF]` | — | — | **CLOSED** |
| **A0-a** | ⚠ **New, from answering A0:** does parallel completion order change the synthesis? | Synthesis is an LLM call over `positions`, built in **completion order** `[VRF]` | Sorting `positions` to canonical seat order removes the ordering variance entirely | Run parallel twice with forced-opposite completion orders; compare digests. Divergence ⇒ sorting is mandatory, not optional | **P0 — implementation gate** |
| **A0b** | Does the spend cap hold under concurrency, and see all three seats? | ✅ **ANSWERED — no, and no.** `check`→spawn→`record` is check-then-act `[VRF]`; *"codex/agy… are neither checked nor recorded"* `[VRF]` | Read fan-out exposure is bounded (2 billable calls, overcounting estimate); write-lane exposure is not | Concurrent-spawn test against a $0.01 cap quantifies the TOCTOU window | **P0 for writes; bounded for reads** |
| A1 | Which tasks gain from parallel models? | Read-only fan-out is the only case with clean support; round table is sequential `[VRF]` | Parallelising 3 read seats cuts wall-clock, with finding-set divergence **within the sequential run-to-run noise floor** | §8.5's noise-floor comparison. ⚠ Byte-identity is unmeetable with CLI seats and is withdrawn as a criterion | **P0** |
| A1b | **How long does the sequential round table actually take today?** | Unmeasured — v1 never established the baseline it proposed to improve | Unknown; D1's own counter says "minutes, not hours" | Time 5 threads. ⚠ Without this number E1 is unjustified in either direction | **P0** |
| A2 | Where does orchestration overhead eat the win? | Wall-clock *rose* in CAID; tool-heavy penalty β=−0.096 `[VEF]` | Below ~90s of model time, lane setup exceeds the saving | Instrument setup vs model time; find the crossover | **P0** |
| A3 | Should lanes be typed beyond read/write? | `PLAN_ONLY_SEATS` already encodes a capability distinction `[VRF]` | Two types suffice | Name one enforcement rule needing a third type inexpressible as read/write + write_set | P1 |
| B1 | What must a lane receive? | Handoff pins SHAs; FixReceipt carries scope + probes `[VRF]` | §5 is sufficient; no field added during dogfood | Log every "needed X, didn't have it". >2 distinct fields falsifies | P0 |
| B2 | How does a worker prove it acted on intended state? | `verify.py` emits `packet <sha> vs current <sha>` `[VRF]` | `base_sha` echoed + `git rev-parse HEAD` at start and end is sufficient | Inject a mid-run base change; receipt must be flagged. ⚠ `git diff --check` is a whitespace/conflict-marker lint and proves **nothing** about base state — withdrawn as proof | P0 |
| B3 | What makes a result inadmissible? | Class-M gates boundary classes; *"absence is not a pass"* `[VRF]` | Three conditions: write outside declared set, missing required receipt, model identity not captured from invocation | Attempt each. ⚠ *Stale* is **not** here any more — it triggers re-verification, not rejection (§7). And "unverifiable model identity" would make every CLI lane inadmissible, so the condition is *not captured*, not *not verifiable* | P0 |
| C1 | Is read-only isolation sufficient? | `panel.py` enforces "seats never run tools" `[VRF]` | Yes — no worktree needed | Pre/post tree hash; any mutation falsifies | P0 |
| C2 | Does every write lane need a worktree? | 63.3 vs 55.5 `[VEF]`; ghosts exists `[VRF]` | Yes, necessary not sufficient | ⚠ The soft-isolation control is **weak** — two lanes on disjoint files in one checkout will likely not clobber. See §8.2 for what was changed | P1 |
| C3 | What does a worktree still not isolate? | Shares object DB, refs, config, hooks, stash `[VEF]` | Six residual surfaces | Concurrent stash from two lanes; concurrent spawn ×3. ⚠ Add: shared `.pytest_cache`, `__pycache__`, `.coverage`, `*.egg-info`, `.venv` in the soft-isolation arm — v1 omitted these entirely | P0 |
| C4 | Detect overlap before start? | Bazel precedent `[VEF]` | Static glob intersection catches **declarable** overlap, **conservatively** | ⚠ Two lanes both declaring `tests/unit/new_*.py` for files that do not yet exist cannot be resolved by expansion against `base_sha`; symbolic `**` intersection is nontrivial. Overlap detection must be **conservative (refuse on doubt)**, and this is now stated rather than assumed | P0 |
| C5 | Which surfaces serialize regardless? | Ecosystem docs converge on regenerate-don't-merge `[VEF]` | §6 Class 3 is complete for this repo | Any post-hoc conflict outside the list extends it | P0 |
| C6 | OCC, leases, CAS, or reservations? | Lease expiry under a paused holder ⇒ split brain; Chubby needs a sequencer at the resource `[VEF]`; kernel `flock` releases on death, hand-rolled lock *files* do not `[VEF]` | Explicit reservation + CAS on `base_sha`; **not** leases | Pause a lane past any proposed term; if the design reassigns its write set, it is unsound | P1 |
| D1 | What drives model selection? | Only Anthropic has an SDK adapter; only 2 seats can write `[VRF]` | Three inputs: mode, tool access, budget | Show a routing decision needing a fourth | P2 |
| D2 | Does diversity buy independence? | **No** — 3.7× excess co-failure; 9 judges ≈ 2.18 voters `[VEF]` | Cross-seat agreement is worth much less than seat count implies | ⚠ Measure φ — but note this argues against **seat count**, not against parallelising. The cheaper response is *dropping a seat*. See D1 in the register | P1 |
| D3 | Record provider/model for reproducibility? | OTel names exist; models resolve per-call from env `[VRF]` | Capture from the invocation environment, never self-report | Compare a lane's self-report to env | P0 |
| E1 | Patches, commits, or artifacts? | `solutions.py` materializes in a scratch worktree and refuses tracked branches `[VRF]` | Unified diff + receipts; never a commit from a lane | ⚠ Consequence: ghosts' **ff-only promotion does not apply**. The integration path must be written, not reused | P0 |
| E2 | What must the lead rerun centrally? | FixReceipt distrusts workflow exit `[VRF]` | Full suite at the **integration** base | ⚠ Justified on its own merits; the 17.2×/4.4× number is `[INF]` support, not proof | P0 |
| E3 | How to stop advice becoming authority? | MCP terminal states immutable `[VEF]` | Two-axis machine (§7): a lane reaches `completed`, never `ready_for_integration` | Find any path where a lane's output changes what is integrated without a lead transition | P0 |
| F1 | Can siblings continue after one lane fails? | `ParallelStrategy` uses `return_exceptions=True` `[VRF]` | Yes for reads; for writes only when the dead lane held no needed reservation | Kill a lane mid-run; siblings complete, reservation releases **on confirmed exit** | P0 |
| F2 | Which retries are safe? | Stripe: same key + different params must error `[VEF]` | Safe iff `base_sha` unchanged, worktree discarded, **and `attempt` incremented** | ⚠ Without the attempt counter the cached failure replays forever — v1's retry was impossible | P1 |
| F3 | Resume after orchestrator restart? | Temporal's price is determinism + versioning `[VEF]` | Append-only run log + idempotency key; no engine | ⚠ **And an orphan sweep.** Lanes are subprocesses that outlive the parent, keep spending and keep writing. Kill the parent; confirm the sweep finds and kills them | P1 |
| G1 | Provider isolation or OS containment? | Every recorded incident defeated a *policy* control `[VEF]` | OS-level per-lane containment + default-deny egress | Any containment resting on a lane's prompt is falsified by construction | P0 |
| G2 | What stops writes outside the declared set? | *"For OS-level enforcement… enable the sandbox"* `[VEF]` | Mount-level | Write outside via a Python script rather than a file tool | P0 |
| G3 | What audit trail is required? | `tool_decision` etc. exist; egress destination does not `[VEF]` | Egress logged at the proxy | Reconstruct "which lane reached which host" from agent logs alone | P1 |
| H1 | What to borrow? | MCP Tasks fits; A2A solves cross-org distrust `[VEF]` | MCP's 5 states + accept/decline/cancel + Stripe idempotency | Name a lane failure the subset cannot express | P1 |
| H2 | Local contract or protocol? | attune-forms extracted only after a third consumer `[VRF]` | Local first | If a second library needs lanes during dogfood, revisit | P1 |
| I1 | What must the UI show? | *"Truncated promotion UI is a failure receipt"* (SCW D6, working-tree observation) | §9 field set | ⚠ **And the dashboard's own attention cost must be counted** — 11 fields × 5 lanes aimed at the human the packet calls the bottleneck. The cold-reader probe is now in §8.3 | P1 |
| I2 | How to avoid activity ≈ progress? | Progress MUST be monotonic and stop at terminal `[VEF]` | Display receipts produced, not tokens or time | A lane at 15 minutes with no receipt must render visibly empty | P1 |

---

## 4. Architecture options

### A. Read-only parallel advisors, one writer

| | |
|---|---|
| **Benefits** | The only configuration with clean supporting evidence. Zero mutation risk *by construction* — no worktree, no reservation, no merge, so the safety is structural rather than policy-based. The round table is sequential today `[VRF]`, so the wall-clock headroom is real (magnitude unmeasured — A1b). `panel.py` demonstrates the deterministic-synthesis pattern in-repo `[VRF]`. |
| **Risks** | ⚠ **Seat independence is now verified `[VRF]`** — that risk is retired. Three remain. **(1) The synthesis is an LLM call, not deterministic** `[VRF]`, so the round table's output already varies run to run; parallelism must be measured against that floor, not against a fixed expectation. **(2) Two ordering races** — `positions` in completion order and the `invocations` counter `[VRF]` — mean a naive `gather()` changes the synthesis prompt and can overshoot the invocation cap. Both are cheap to fix and neither is optional. **(3) An internal tension the packet cannot resolve by design:** `panel.py` ranks by *confidence and agreement* `[VRF]`, but at n_eff ≈ 2.18 `[VEF]` agreement is weaker evidence than it looks, and "confidence" is seat self-report — which D3 declares inadmissible for model identity while this accepts it for ranking. Treat agreement-weighting as a **known defect to characterise in E1**, not a feature. Neither module documents what happens when two seats flatly contradict each other. |
| **Complexity** | Low. Bounded concurrency around an existing loop, plus a sort and an atomic counter. |
| **Failure containment** | Excellent. A failed seat is a missing opinion; `SEAT_ABSENT` already exists `[VRF]`. Budget exposure is 2 billable calls with an overcounting estimate `[VRF]`. |
| **Status** | ⚠ **ADOPT.** Restored from v2's ADOPT-PENDING-PROBE — the probe was run (§0.5) and cleared. |

### B. Disjoint write lanes in separate worktrees

| | |
|---|---|
| **Benefits** | The isolation ablation supports it directionally `[VEF]`. Declared write sets have strong precedent `[VEF]`. Worktree lifecycle, arg-injection guards and base-SHA verification exist in-repo `[VRF]`. |
| **Risks** | ⚠ The **residue is semantic coupling**, and no cited number measures it — the 41.7% figure is a prior for *unpartitioned* work and explicitly excludes semantic conflicts, so it can be neither the risk B removes nor the residue B leaves. Worktrees share far more than the name implies, including the **stash** `[VEF]`. ⚠ **`read_set` is incoherent for a lane that runs tests:** pytest reads `conftest.py`, `src/**`, fixtures. Either `read_set` is advisory (and Class 2's write∩read condition is unenforced) or mount-scoped (and any realistic `read_set` makes any two write lanes mutually exclusive). §6 now picks. ⚠ **Overlap detection is only conservatively decidable** — two lanes declaring not-yet-existing files under the same glob cannot be resolved by expansion. ⚠ **ff-only promotion does not apply** to diff-returning lanes, so the integration path is new work; "~70% exists" is withdrawn. Degradation past ~4 `[VEF]`. Sprawl already live: 36 worktrees, 35 prunable `[VRF]`. |
| **Complexity** | ⚠ **Medium-to-high** (raised). Overlap detection, reservation with confirmed-exit release, orphan sweep, provisioning under default-deny egress, a new integration path, receipt validation, cleanup. |
| **Failure containment** | Good within the declared model, weak outside it. Requires `gc.auto=0`, serialized spawn, a stash prohibition, and process-group ownership to reach that. |
| **Status** | **PILOT, NARROWLY.** One disjoint pair plus two conflict probes (§8). |

### C. General dependency-DAG execution

| | |
|---|---|
| **Benefits** | Expresses A and B plus staged pipelines; `orchestration/_strategies/` has 14 strategies already `[VRF]`. |
| **Risks** | The configuration the evidence is most hostile to. Tool-heavy overhead compounds with environmental complexity `[VEF]`; MAS failure rates 41–86.7% `[VEF]`; coordination returns diminish above ~45% single-agent accuracy — ⚠ though whether Attune is above that threshold is **unmeasured**, so this is `[INF]` not `[VEF]`. Inter-lane dependencies are exactly what Anthropic warns against `[VEF]`. Cognition's argument — that actions carry implicit decisions and conflicting ones surface only at integration — applies directly ([cognition.com](https://cognition.com/blog/dont-build-multi-agents), 2025-06-12; ⚠ *added, cited without a source in v1*). Invites durable-execution machinery whose price is determinism, versioning and history caps for a guarantee that is only "observed as completed exactly once" `[VEF]`. |
| **Complexity** | High, and load-bearing. |
| **Failure containment** | Poor. One stale upstream invalidates downstream lanes, detected late. |
| **Status** | **REJECT for now.** |

---

## 5. Proposed minimal lane manifest `[PROP]`

Design rule: every field must be **checkable by the orchestrator without asking the model**.

| Field | Required | Semantics | Enforcement |
|---|---|---|---|
| `run_id` | yes | One run = one integration decision | — |
| `lane_id` | yes | Unique within run; names worktree and branch | `^[A-Za-z0-9][A-Za-z0-9._-]*$` (reuse `_GHOST_ID_PATTERN` `[VRF]`) |
| `base_sha` | yes | Immutable 40-char SHA, never a ref | Orchestrator resolves; echoed in receipt and compared |
| `attempt` | yes | ⚠ **Orchestrator-assigned**, monotonic per (lane_id, base_sha) | Increments on retry. ⚠ **Must not be submitter-supplied** — a caller who can bump it can re-execute a completed write lane, which is exactly the replay the key exists to prevent `[review finding]` |
| `idempotency_key` | yes | `hash(base_sha + attempt + objective + read_set + write_set + provider + model)` | ⚠ **`attempt` included** so a retry after a transient failure is a new key. Stripe semantics govern **result delivery** (a duplicate submission of the same attempt replays); they do **not** forbid re-execution under a new attempt |
| `mode` | yes | `read` \| `write` | `read` ⇒ no worktree, no branch, no write authority |
| `objective` | yes | One bounded outcome | Human-checkable |
| `read_set` | yes | ⚠ **Advisory for both modes, and explicitly so.** A lane that runs tests reads far beyond any honest declaration | ⚠ Class 2's write∩read condition is therefore evaluated against the **write sets and the always-serialized list only** (§6). v1's condition was unenforceable |
| `read_mount` | `write` only | ⚠ **The lane's own worktree, full stop.** All manifest paths are worktree-relative | v2 wrote `"."`, which is ambiguous and wrong either way `[review finding]`: the main checkout would expose Patrick's dirty tree instead of `base_sha`, and a repo-rooted mount would contain sibling worktrees under `.attune/lanes/`, letting "independent" lanes read each other's in-progress diffs. **Sibling worktrees must live outside every lane's mount** |
| `write_set` | `write` only | Globs the lane may create or modify | Conservatively intersected against siblings **before provisioning**; refuse on doubt. Post-hoc: any path outside ⇒ `scope_violations` `[VRF]` |
| `write_mount` | `write` only | ⚠ **New.** The only writable subtree — the lane's worktree | The actual boundary. Declaration alone is advisory `[VEF]` |
| `forbidden_paths` | yes | Overrides `write_set`; defaults to §6 Class 3 | Refuse to arm on intersection |
| `dependencies` | yes | Must be empty in the dogfood | Non-empty ⇒ Architecture C ⇒ refuse |
| `provider` / `model` / `model_source` | yes | `model_source` ∈ `env` \| `cli_flag` \| `config`, **with the key name** | `self_report` is not an allowed value |
| `tool_inventory` | yes | Allowlist, never a denylist `[VEF: Gemini's `excludeTools` "is not a security mechanism"]` | Empty for `read` |
| `authority` | yes | `{external_send, commit, push, merge, publish}`, all default `false` | Boundary-enforced; every `true` is a human gate |
| `budget` | yes | `{maximum_usd, maximum_minutes}` | ⚠ **`[PROP]`, not existing capability.** Requires a *reservation-before-launch* the ledger does not implement, and per-seat spend capture for `codex`/`agy` that may not exist at all. Blocking item — see §8.0 |
| `stop_conditions` | yes | ⚠ **Mechanically detectable only** | See below |
| `required_receipts` | yes | Evidence without which the result is inadmissible | *"absence is not a pass"* `[VRF]` |
| `egress_allowlist` | yes | Hosts reachable. ⚠ Must include **provisioning** hosts | Proxy-enforced and proxy-logged |

⚠ **Stop conditions, corrected.** v1 included *"an instruction is encountered in repository or fetched content"*. That is not mechanically detectable — it depends on the model noticing — and testing it would measure the very prompt-level control §3/G1 calls decorative. **Removed.** Injection is contained by the boundary (§8.6), not by a stop condition, and §8.3's probe now measures whether the *boundary* holds, not whether the model behaves.

### Worked example

```json
{
  "run_id": "parallel-dogfood-001",
  "lane_id": "impl-tests-board",
  "base_sha": "78661a787c4e1f0a9b2d5e8c3f6a1b4d7e0c9f2a",
  "attempt": 1,
  "idempotency_key": "sha256:4f1c…",
  "mode": "write",
  "provider": "anthropic",
  "model": "<resolved at launch>",
  "model_source": "env:ATTUNE_MODEL_PREMIUM",
  "objective": "Add regression coverage for Board TTL refresh on post; no production changes.",
  "read_set": ["src/attune/roundtable/board.py", "tests/unit/roundtable/test_board.py"],
  "read_mount": "<lane worktree root>",
  "write_set": ["tests/unit/roundtable/test_board.py"],
  "write_mount": "<lane worktree root>",
  "forbidden_paths": [
    "pyproject.toml", "uv.lock", "CHANGELOG.md",
    "docs/specs/**/decisions.md", ".github/**", "src/**", ".attune/**"
  ],
  "dependencies": [],
  "tool_inventory": ["read_file", "write_file", "run_tests"],
  "authority": { "external_send": false, "commit": false, "push": false, "merge": false, "publish": false },
  "budget": { "maximum_usd": 3, "maximum_minutes": 20 },
  "egress_allowlist": ["api.anthropic.com", "pypi.org", "files.pythonhosted.org"],
  "stop_conditions": [
    "base_sha != git rev-parse HEAD in lane worktree",
    "a write outside write_set is required",
    "a failing test is outside lane ownership",
    "budget would be exceeded"
  ],
  "required_receipts": [
    "unified diff",
    "argv of every test command actually run",
    "test results with returncode and duration",
    "git rev-parse HEAD at start and end",
    "unresolved risks"
  ]
}
```

⚠ **Corrections carried through the example.** `model` is no longer a literal string asserting an identity the packet says cannot be self-reported — it is resolved at launch and recorded. `git diff --check` is gone from the receipts: it is a whitespace and conflict-marker lint and proves nothing about base state. `egress_allowlist` includes package hosts, because provisioning a fresh worktree needs them and v1's provider-only allowlist would have deadlocked the lane before it started.

⚠ **And one correction to v2's own fix, which was worse than the bug.** v2 tried to scope the `.attune/**` denial with `.attune/**/!(lanes/impl-tests-board/**)`. That is bash extglob — not POSIX glob, not Python `fnmatch`, not gitignore/wildmatch semantics — and even in bash `!(…)` matches a single path segment, so a pattern containing slashes never matches and **the exclusion was inert** `[review finding]`. The underlying cause was mixing worktree-relative entries (`src/**`) with repo-root-relative ones (`.attune/**`) in one list. With all paths worktree-relative and sibling worktrees outside the mount, the exclusion is unnecessary and `.attune/**` is a plain deny.

---

## 6. Contention policy `[PROP]`

### Class 1 — Automatically parallelizable

All `mode: read` lanes. No worktree, no branch, no reservation.

⚠ **Concurrency cap: 3, and it is `[PROP]`, not evidence-derived.** v1 cited "degradation past 4" as if it applied. It does not: that was measured on *write* engineers sharing a repository, and the mechanism (contention, overwrites) does not exist for read lanes with no shared state. The paper's other number is 2. Choosing 4 because it made the cap non-binding for three seats was motivated reasoning `[review finding]`. The cap is set at the current seat count because that is the actual configuration, and it should move only on measurement.

⚠ **And a real Class 1 constraint v1 omitted: the budget cap.** A fan-out of 3 seats spends 3× in the same window against a cap whose concurrent-correctness is unestablished, with two of three seats possibly unmetered `[INF]`. **§8.0 gates the fan-out on fixing this.**

### Class 2 — Conditionally parallelizable

| Condition | Why |
|---|---|
| Declared `write_set` globs **conservatively disjoint** — refuse on undecidable overlap | Bazel precedent `[VEF]`; ⚠ not-yet-existing files make exact intersection undecidable |
| No `write_set` intersects Class 3 | Below |
| ⚠ *(withdrawn: "no write_set intersects a read_set")* | Unenforceable — a lane running pytest reads the world. `read_set` is advisory; `read_mount` is the real read boundary |
| Each lane has its own worktree **and its own `write_mount`** | 63.3 vs 55.5 `[VEF]`; declaration alone is advisory `[VEF]` |
| `gc.auto=0` repo-wide | Shared object DB `[VEF]`. ⚠ Cheap insurance; note git's own hedge is "low in practice", and this does not stop `git maintenance` or an explicit `git gc` from a lane |
| Lane spawn serialized | `[INF]` — mechanism *suspect, verify*, but serializing is cheap |
| No lane may `git stash` | `refs/stash` is shared `[VEF]` |
| No submodules | *"NOT recommended"* `[VEF]` |
| Provisioning is port-, DB- and cache-disjoint | ⚠ v1 said "port and DB". Add `.pytest_cache`, `__pycache__`, `.coverage*`, `*.egg-info`, `.venv` — per-worktree by default, but **shared in the soft-isolation arm**, which is where they will bite |
| Lanes run in a process group killed on orchestrator exit | ⚠ New — orphan prevention (§7) |

⚠ **`extensions.worktreeConfig` is the documented mitigation for shared config** `[VEF]`, which v1 omitted while calling shared config a hazard. It is opt-in and makes the repo unreadable to older git — a real trade, but it should be named.

**Honest limit** `[INF]`: these catch *declarable* overlap. Semantic coupling — a shared interface, a fixture, an assumed constant — is the residue, and **no cited number measures it**. The only defense is central re-verification at the integration base.

### Class 3 — Always serialized

Derived files here are **regenerated from merged sources, never merged** `[VEF]`.

| Surface | Paths | Reason |
|---|---|---|
| Lockfiles / dep manifests | `uv.lock`, `pyproject.toml` | `merge=union` is silently incoherent `[VEF]` |
| Governance documents | `docs/specs/**/decisions.md`, `**/tasks.md` | Chair rulings are authority, not content |
| Receipt ledgers & run records | `.attune/**` (excluding a lane's own worktree), `.empathy/**`, `**/receipts.md` | Append-only by design `[VRF]` |
| Changelog / release metadata | `CHANGELOG.md`, version strings | Ordering *is* the content |
| Generated projections | `.help/**`, framework-docs, help-site, `website/` output | Regenerate from merged sources `[VRF]` |
| CI and policy surface | `.github/**`, `.pre-commit-config.yaml`, `.mcp.json` | Self-referential; `auto_merge_guard.py` applies this reasoning to itself `[VRF]` |
| Git configuration surface | `.git/config`, `.git/hooks`, shell rc files | Shared across worktrees; persists **unsandboxed** `[VEF]` |
| Byte-budgeted / drift-pinned | `form-theme.css`, `model_tiers.py`, chartkit kernel | A drift guard and a concurrent writer are incompatible `[VRF]` |
| Cross-repo surface | `server.json`, `.claude-plugin/marketplace.json` | Single coordination point |

⚠ **`.claude/**` is deliberately *not* in Class 3 as a blanket rule**, because 23 of 36 registered worktrees live under `.claude/worktrees/` `[VRF]` — a blanket denial would forbid a Claude Code lane from provisioning where it actually provisions. Deny `.claude/settings*.json`, `.claude/commands`, `.claude/agents` specifically; leave `.claude/worktrees/<this lane>` writable. v1 got this wrong.

**Reservation, not lease** `[PROP]`. Explicit single-owner reservation, released **only on confirmed process exit (`waitpid`)** — ⚠ never on cancel-intent, which v1 specified and which recreates precisely the split-brain used to reject leases `[review finding]`. Not a lease: expiry under a live-but-paused holder is the *expected* case with LLM latency, and soundness would require a Chubby-style sequencer validated at the resource `[VEF]` — more machinery than 2–5 local lanes justify. Not a hand-rolled lock file either: those leak on SIGKILL, whereas kernel `flock` does not `[VEF]`.

---

## 7. Failure and recovery state machine `[PROP]`

The brief's eleven states should not be one machine: they mix what the *worker* did with what the *lead* decided. A lane that can put itself in `ready-for-integration` has asserted its own admissibility.

### Axis 1 — Execution state (worker-observable; the lead never sets it)

```
  pending ──► armed ──► running ──► completed  (terminal)
     │          │         │  ▲
     │          │         │  └──── blocked  (interrupted; resumes on decision)
     │          │         │
     └──────────┴─────────┴──────► failed     (terminal)
                          └──────► cancelled  (terminal)
```

⚠ v1's diagram had `blocked` with no return edge and a `pending` arrow pointing at a terminal state that did not exist. Corrected: `blocked` returns to `running` on a lead decision; `pending`, `armed` and `running` can all reach `failed`.

| State | Meaning | ⚠ Note |
|---|---|---|
| `pending` | Submitted, not validated | — |
| `armed` | Overlap check passed, reservations held, **budget reserved**, worktree provisioned. Not yet spending | ⚠ v1 called this "the last point at which refusal is free" while also saying the worktree exists. Both cannot hold. **Checks run at `pending → armed`; provisioning is the last step of the transition.** Refusal before provisioning is free; after it costs a teardown |
| `running` | Model invoked, budget consuming | — |
| `blocked` | Halted on a stop condition; needs a decision | Interrupted, not terminal |
| `completed` | Finished and produced required receipts. **Says nothing about admissibility** | — |
| `failed` | Crashed, over budget, or invalid receipt | — |
| `cancelled` | Stopped by lead | Reservations release on **confirmed exit**, not on the cancel signal |

`completed`, `failed`, `cancelled` are terminal and immutable (MCP's rule `[VEF]`). `armed` is Attune-native and matches the existing `P4-ROTATION: armed` chair vocabulary `[VRF]`.

### Axis 2 — Disposition (lead-owned, after a central verification pass)

```
completed ──► unreviewed ──► integrated | rejected | deferred
```

⚠ v1 claimed this vocabulary came from MCP elicitation's accept/decline/cancel. It does not — the mapping is cosmetic and `cancel` (dismissed without choosing) is not `deferred` (intend to return) `[review finding]`. The *distinction worth keeping* is real and is the reason for three values: an explicit no is not a non-answer. Sourcing claim withdrawn.

**Only the lead transitions this axis, and only after rerunning verification at the integration base.**

### Staleness — a flag, not a verdict

⚠ **This is the correction that matters most for Architecture B.** v1 said a `completed` lane on a superseded base was "equally unusable" as a failed one. Under two write lanes, lane 3 integrating makes lane 4 stale *immediately* — so at most one write lane could ever integrate, which defeats B entirely `[review finding]`.

**Policy** `[PROP]`: `stale` is `base_sha != integration HEAD`, computed on demand, and it **triggers re-verification rather than rejection**:

1. Patch applies cleanly at integration HEAD ⇒ apply, **rerun the full check set at integration HEAD**, then dispose.
2. Patch does not apply ⇒ the lane is **serialized**: rebased onto integration HEAD and re-run, or returned to the queue.
3. Re-run fails at integration HEAD though it passed at the lane base ⇒ that is a **semantic conflict**, and it is the single most valuable observation the dogfood can produce. Record it explicitly.

`handoff/verify.py` already computes this comparison and returns *"a report, not a go signal"* `[VRF]` — the right posture, and now the packet matches it.

`partial` is likewise a property of the *receipt* (`ProbeOutcome.status` is already `PASS | FAIL | SKIPPED` `[VRF]`), and `conflicting` is a property of a *set* of results at integration time.

### Orphaned lanes ⚠ (new)

Lanes are subprocesses. When the orchestrator dies they keep running, keep spending, and keep writing into worktrees whose reservations no longer exist anywhere `[review finding]`. v1 offered two contradictory crash policies and addressed neither the spend nor the writes.

**Single policy** `[PROP]`: **reconstruct-or-refuse.** On restart, read the append-only run log, sweep `.attune/lanes/*` and the worktree registry against it, and kill anything unaccounted for before doing anything else.

**Prevention, not just cleanup** ⚠. A sweep runs on *restart*, so between crash and restart orphans keep spending against a cap that is already check-then-act `[VRF]` — the sweep alone is insufficient `[review finding]`. Launch every lane in a dedicated process group; on Linux set `PR_SET_PDEATHSIG`. ⚠ v2 said macOS "has no equivalent" and left the sweep as the primary mechanism there — that overstated the problem. The standard userland substitute is a small wrapper holding a pipe to the parent that kills its own process group on EOF; it is a dozen lines and works on both platforms. **Platform note:** that the primary platform is macOS is an assumption from the seats being local CLIs, not a verified fact — if Linux, `PR_SET_PDEATHSIG` alone closes most of this.

### Cancellation

Cooperative, with MCP's race rules `[VEF]`: cancel is an intent; the lane should stop and free resources; cancelling a terminal lane is a defined non-fatal condition; **any result arriving after cancellation is ignored**.

⚠ **Release condition, corrected twice.** v1 released reservations on the cancel signal, which recreates the split-brain used to reject leases. v2 released on `waitpid`, which still leaves two holes `[review finding]`: a lane that **hangs** rather than exits never reaches `waitpid`, so a sibling waiting on a Class 3 surface blocks forever; and the lane is a CLI that spawns `pytest` and `git`, so reaping the direct child says nothing about grandchildren still writing the worktree. **Correct condition: the lane's process group is empty, after a SIGTERM → timeout → SIGKILL escalation.** Reaping a child is not the same as the work having stopped.

Cancelling one lane cancels no sibling.

### Rejected findings are recorded

`{lane_id, run_id, base_sha, provider, model, finding, reason, decided_by, decided_at}`, appended to the run log — because verification failures are MAST's largest category `[VEF]`, and because a per-seat rejection rate is the only way to spot a seat quietly consuming review capacity.

---

## 8. Minimal dogfood experiment `[PROP]`

### 8.0 Gating preconditions ⚠ (new — none of these is optional)

| # | Precondition | Status | Why |
|---|---|---|---|
| P1 | Seat-input independence in `routine.py` | ✅ **DONE** (§0.5) | Seats are independent; A's premise holds. Surfaced two ordering races and the non-deterministic synthesis |
| P2 | Budget cap under concurrency; per-seat metering | ✅ **DONE** (§0.5) | Cap is check-then-act and covers one of three seats, both `[VRF]`. Read exposure bounded; **write exposure is not** |
| P2a | ⚠ **New:** decide whether to fix the TOCTOU or cap the write dogfood out-of-band | **OPEN — blocks write lanes only** | Reserve-before-launch is real work. A hard `ATTUNE_SESSION_SPEND_CAP_USD` set for the run, plus manual reconciliation, is the cheap alternative |
| P3 | Sequential round-table baseline timed, **≥3 replicates** | **OPEN — blocks E1** | Without it E1 is unjustifiable in either direction. ⚠ Three, not two: the noise floor needs a range, not a single difference |
| P4 | Fetch `origin/main`; re-verify the absence claims | **OPEN** | Every `[VRF]` is 4 commits stale; the absence claims are the exposed ones |
| P5 | Confirm no submodules | **OPEN — blocks write lanes** | Vendor recommends against worktree-per-lane on a superproject `[VEF]` |

### 8.1 Lanes

⚠ Provider assignment is now explicit. Only `claude` and `codex` can write (`PLAN_ONLY_SEATS = {antigravity}` `[VRF]`), so the write pair is a **2-provider** experiment.

| # | Lane | Mode | Provider | Write set | Purpose |
|---|---|---|---|---|---|
| 1 | `review-security` | read | claude | ∅ | Existing seat work, concurrent |
| 2 | `review-spec-closure` | read | codex | ∅ | Second read seat |
| 3 | `review-plan` | read | antigravity | ∅ | ⚠ Third seat — the status quo is three, so the parallel arm must be three |
| 4 | `impl-tests-board` | write | claude | `tests/unit/roundtable/test_board.py` | Disjoint write A |
| 5 | `impl-tests-rotation` | write | codex | `tests/unit/roundtable/test_rotation.py` | Disjoint write B |
| 6 | `probe-overlap` | write | claude | overlaps #4 | ⚠ Must be refused at `pending → armed`. **Tests overlap detection only** |
| 7 | `probe-class3` | write | claude | `uv.lock` | ⚠ **Split from v1's lane 5.** One rule per probe, so one named reason is observable |
| 8 | `probe-semantic` | write | codex | `tests/unit/roundtable/test_helpers.py` (path-disjoint from #4, **shared fixture**) | ⚠ **New — the C4 probe v1 promised and omitted.** Must *pass* arming and *fail* at integration. This is the only lane that tests the residue |
| — | lead integration | — | — | — | Central rerun at integration base |

⚠ v1 called its single conflict lane "the most important lane in the experiment". It was a smoke test of list intersection against a manifest built to fail it, and it bundled two rules so only one reason could be observed `[review finding]`. Lanes 6–8 replace it, and **lane 8 is the important one**: it is the only probe that can produce evidence about semantic coupling, which is the failure mode no cited number measures.

### 8.2 Control arms

1. **Sequential read baseline = the current three-seat round table**, not one seat, run **≥3 times on identical input**. v1's one-seat baseline was cheaper and lower-quality than the system being replaced `[review finding]`. ⚠ These same runs *are* the noise-floor sample — v2 listed them as two arms, which double-counted; three replicates give a range rather than a single difference.
2. **Sequential write baseline** ⚠ **with providers stated**: lane 4 on `claude` and lane 5 on `codex`, run in sequence. Running both on `claude` would reintroduce exactly the provider/parallelism confound that fixing the read baseline removed `[review finding]`.
3. **Soft-isolation arm:** lanes 4 and 5 in one checkout. ⚠ **Stated honestly as weak** — two lanes writing disjoint *files* will probably not clobber, so it cannot reproduce the CAID mechanism. Retained to test *shared-cache* hazards (`.pytest_cache`, `__pycache__`, `.coverage*`, `.venv`, `*.egg-info`), a real and distinct surface. **Its result may not be read as evidence about file clobbering in either direction**, and v1's pre-commitment to reading "not worse" as "isolation unjustified" is withdrawn.

**Finding identity, pre-registered** ⚠. The divergence measure needs a way to say two findings are "the same", and §8.4 elsewhere calls that an undefined judged operation — so it cannot be left implicit `[review finding]`. **Pre-registration:** findings are matched by `(file path, symbol or line range, defect class)` where all three are extracted mechanically from the seat's reply; anything unmatched is judged by Patrick against a rubric written *before* the first run, and the judged fraction is reported alongside the result. If more than a third of findings need judging, the measure is not usable and the read verdict is **Defer**, not Proceed.

**Cost, totalled** ⚠ — v2 spent a blocker on the $10 cap and never added up its own experiment. Read arms: 4 runs × 2 billable calls ≈ 8 `claude` invocations. Write arms: 2 lanes × 2 replicates + 3 probes + soft-isolation pair ≈ 9 lanes, of which 7 are `claude`, at `maximum_usd: 3` ⇒ **≈ $21 worst-case for the write half alone**, against a `DEFAULT_CAP_USD` of 10 `[VRF]`. **The write dogfood cannot run inside the default cap**, which is P2a: either raise the cap explicitly for the run and reconcile manually, or split the write arms across sessions. Recording continues even when the ledger is disabled `[VRF]`, so the audit trail survives either choice.

### 8.3 Failure injection

| Injection | Method | Expected |
|---|---|---|
| Declarable overlap | Lane 6 | Refused at `pending → armed`, named reason, **no worktree created** |
| Class 3 violation | Lane 7 | Refused, **distinct** named reason |
| ⚠ Semantic conflict | Lane 8 | **Passes arming**, completes, then fails the central rerun at integration HEAD. Record the diagnosis path |
| Stale base | Commit to `main` mid-run | Flagged; re-apply policy (§7) executes; **not** silently accepted, **not** auto-rejected |
| Worker crash | `SIGKILL` a write lane | → `failed`; reservation releases **on `waitpid`**; sibling completes |
| ⚠ Orchestrator crash → orphans | Kill the parent while lanes run | Sweep on restart finds and kills orphans; **measure how much they spent before the sweep** |
| Malformed receipt | Omit test argv | `completed` on axis 1, **inadmissible** on axis 2 |
| Budget exhaustion | `maximum_usd: 0.01` | Hard refusal before spend — ⚠ **and this is P2, not a formality** |
| Concurrent spawn | Arm 3 write lanes at once, repeatedly | Serialized spawn succeeds. ⚠ If parallel, observe whether `config.lock` fails — **a non-failure across a few trials is not evidence of safety**, only a failure is informative, so this can confirm the `[INF]` but never retire it |
| Shared stash | Two lanes `git stash` | Prohibited at validation; if attempted, detected |
| ⚠ Egress denial | Provision a fresh worktree with a provider-only allowlist | **Expected to fail** — this is why §5 adds package hosts. Confirms the allowlist is complete before a real lane deadlocks |
| ⚠ Cold-reader UI probe | Show the dashboard mid-run to someone uninvolved; ask "which lane is closest to being useful?" | Answered by receipts, not elapsed time. Falsifies §9 if not |

⚠ v1's "injection probe" is **removed**. It tested a prompt-level stop condition that §3/G1 already declares decorative — measuring something the packet has argued is worthless `[review finding]`. Injection resistance is a property of §8.6's boundary and is tested there.

### 8.4 Metrics ⚠ (definitions pre-registered before the run)

**Primary:**

- **Integration rework** = lead-minutes **actively spent** on conflict resolution, rebase, re-application and re-runs. ⚠ v1 defined it as the interval from first `completed` to `integrated`, which measures *latency*, including time spent waiting for other lanes `[review finding]`.
- **Human intervention count**, against a **taxonomy fixed before the run** (arm a lane, answer a `blocked`, resolve a conflict, re-run, dispose). ⚠ v1 defined it as a counterfactual judged by an unblinded n=1 who wants the result.
- **Wall-clock to integration**, not to last `completed`.
- **Accepted yield**, defined **per mode** ⚠: read lanes → findings integrated ÷ findings produced; write lanes → **patches integrated ÷ patches produced**. v1 applied "accepted finding yield" to lanes that produce patches, not findings.

**Secondary:** cost and tokens per accepted unit (⚠ *including* any spend the ledger fails to capture — P2); time to first useful result; conflicts; retries; rollback success; **defect escape** (passes at lane base, fails at integration base — lane 8 is the designed instance); pairwise seat overlap.

⚠ **On seat correlation:** v1 proposed a φ̄ > 0.4 threshold. That is a category error — correlated seats argue against **having three seats**, not against parallelising them, and parallelisation does not change φ `[review finding]`. Also, φ on free-text findings requires matching findings across seats, an undefined judged operation on ~10 items. **Demoted to an observation**, reported as a Jaccard overlap of finding sets with no threshold attached, feeding D1's drop-a-seat option rather than the proceed/defer decision.

### 8.5 Thresholds ⚠ (two independent verdicts, one shared gate)

v2 used a single ordered list, which meant a write-lane failure could pre-empt the read verdict and vice versa — collapsing two decisions the packet insists are separable `[review finding]`. **There are two verdicts.** They share only the Disqualifiers.

**Disqualifiers — any one voids both verdicts and the run.**

- Lane 6 or 7 reaches `running` (arming failed to refuse a declared violation).
- `scope_violations ≠ ∅` at integration for any lane. ⚠ **Restored** — v2 replaced this with "succeeds in writing outside `write_mount`", which can only fire on a sandbox escape and so was nearly vacuous. The declared-write-set check is the one that tests the *design*; the mount check tests the *boundary*. Both belong, and this one is primary.
- Any result integrated without a central rerun at the integration base.

**Read verdict** — evaluated on the read arms alone.

| Verdict | Condition |
|---|---|
| **Proceed** | Parallel-vs-sequential finding-set divergence falls **inside the range of the ≥3 sequential replicates' pairwise divergence**; judged-match fraction ≤ ⅓; median wall-clock improvement exceeds the **replicates' own spread** (⚠ v2 wrongly used P3's *between-task* variance as the denominator); no new intervention category |
| **Defer** | Divergence exceeds the floor, or judged-match fraction > ⅓ (the measure is not usable), or the improvement is inside the spread |

**Write verdict** — evaluated on the write arms alone.

| Verdict | Condition |
|---|---|
| **Reject** | Lane 8's semantic conflict is **not detected** by the central rerun — the design has no defense against its own residue |
| **Proceed, narrowly** | Lanes 6–8 behave as specified; each disjoint lane yields ≥1 integrated patch; **integration rework ≤ 15 lead-minutes per integrated patch**, median across replicates |
| **Modify** | Rework is 15–40 lead-minutes per integrated patch. ⚠ **One re-run, with the manifest change stated in advance** |
| **Defer** | Anything else |

⚠ **The rework threshold is absolute, not relative.** v2 said "≤ sequential + 25%", but §8.4 defines rework as minutes *actively spent* on conflict resolution and rebase — which in a sequential baseline is ≈ 0 by construction, making "+25%" mean "≤ 0" and "25–75% above" undefined `[review finding]`.

⚠ **Byte-identity is gone for a second, stronger reason than v1's.** Not only do CLI seats lack seed control — the synthesis step is itself an LLM call `[VRF]` (§0.5), so the round table is non-deterministic *today*, sequentially. Any criterion demanding identical output would have failed against the current system.

### 8.6 Containment for the run

⚠ Substantially widened — v1 scoped everything to the repository worktree, but s1ngularity harvested from the **home directory** `[VEF]`, and the seats read and write `~/.claude/`, `~/.codex/`, MCP configs and credential stores there.

1. **Default-deny egress per lane**, allowlisting the provider endpoint **and the package hosts provisioning needs**. The only control that breaks the trifecta `[VEF]`; ⚠ v1's provider-only allowlist would have deadlocked provisioning.
2. **`$HOME` is in scope, not just the repo.** Per-lane HOME (or a container) so a lane cannot read another seat's credential store. ⚠ v1 scoped containment to the repo and missed this entirely. ⚠ But v2 overclaimed the fix: a per-lane HOME still holds *that lane's own* provider credentials, which is precisely what s1ngularity ran as `[VEF]`. Blast radius narrows from three credential stores to one — **narrowed, not closed** — and provisioning secrets into N per-lane HOMEs is itself a new secret-handling problem that §8.0 does not yet gate on.
3. **Only the lane's `write_mount` writable.** Declaration is advisory; the mount is the boundary — deny rules do **not** cover arbitrary subprocesses `[VEF]`.
4. **Deny `.git/hooks`, `.git/config`, `.mcp.json`, `.claude/settings*.json`, `.claude/commands`, `.claude/agents`, shell rc files** — these persist *unsandboxed* into the next session `[VEF]`. ⚠ Scoped, not blanket: `.claude/worktrees/<this lane>` must stay writable `[VRF]`.
5. **Pin every MCP server; treat tool annotations as untrusted** `[VEF]`.
6. **No `--dangerously-skip-permissions` / `--yolo` / `--trust-all-tools`** — these *were* the attack surface `[VEF]`.
7. **Egress logged at the proxy**; no agent emits a per-destination event `[VEF]`.

Explicitly not done: per-lane microVMs, TLS-terminating proxy, CaMeL-style taint tracking (~7 points of utility, no droppable implementation `[VEF]`).

---

## 9. UI and observability `[PROP]`

Per lane, receipts first, elapsed last:

`lane_id` · `mode` · execution state · **receipts (n / required)** · disposition · staleness flag · owned paths · provider + model + `model_source` · spend vs budget · stop reason · elapsed.

1. **Progress is receipts, not time or tokens** — monotonic, stopping at terminal `[VEF]`. A lane at fifteen minutes with no receipt renders visibly empty.
2. **Stale is visible but not fatal.** ⚠ Corrected from v1: a stale `completed` lane shows "needs re-verification at HEAD", not a failure state — under two write lanes staleness is the *normal* condition (§7).
3. **Disposition is never inferred from execution state.** `completed` renders as *awaiting review*, never as done or green.

⚠ **The dashboard has an attention cost and it is charged to the bottleneck.** Eleven fields × five lanes plus seven controls is aimed at the one human the packet identifies as the constraint. The cold-reader probe is now in §8.3, and if the dashboard cannot be read in ten seconds it is a cost, not a capability.

Controls: pause, cancel, retry (only with `base_sha` unchanged, worktree discarded, `attempt` incremented), inspect patch, accept, reject with reason, serialize. Log-line names copy OTel GenAI (`gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.*`); ⚠ `gen_ai.system` is renamed and **no cost attribute exists**, so spend stays in Attune's namespace `[VEF]`.

---

## 10. Proposed next artifact — and the plugin question

### Recommendation: preconditions, then a small experiment, then a spec. `[PROP]`

1. **P1–P5 (§8.0).** Cheap, and P1 and P2 can each cancel or reshape everything downstream.
2. **Experiment E1 — read-lane parallelism only**, if P1 clears. Touches `roundtable/routine.py`. No manifest, no worktree, no reservation.
3. **If E1 proceeds → spec `parallel-lane-execution`** in the standard four-file shape, covering only what E1 proved plus the §5 manifest and §7 state machine.
4. **Write lanes stay experiment E2** until E1's spec exists and §8.5's write threshold is met.

An **XML task is the wrong container** `[INF]`: the repo's XML surface is a prompt/response convention with one shipped template plus a philosophy doc `[VRF]`. This needs requirements, decisions and receipts — the four-file spec shape, which is what a chair ruling attaches to.

### The plugin question — pushback, revised

⚠ The review found my v1 argument partly motivated, and it was right about the weaker half. Restating with the bad argument removed.

**The timing argument stands.** You have one consumer. The repo's own discipline is rule-of-three gating, and `attune-forms` was extracted only after a chair-fiat third consumer `[VRF]`. Extracting now means designing the seam against zero evidence.

**The composition argument stands, narrowed.** The portable part is thin — manifest, state machine, worktree lifecycle, conservative overlap check. The valuable part is policy: which paths are Class 3, what a receipt must contain, what `armed` requires, who the chair is. That policy is inseparable from attune-ai's governance.

⚠ **The authority argument I made in v1 does not stand, and I withdraw it.** I claimed a Claude Code plugin would make Claude "simultaneously the runtime, one of the participants, and the thing that decides". Three problems: the shape I *recommended* — a Python package driven by a Claude skill with Claude as a seat — has the identical property; "the thing that decides" is Patrick under the packet's own operating principle, so the sentence was false under its own design; and a plugin can bundle a Python CLI that Codex and Antigravity invoke, so "a plugin cannot deliver cross-provider driving" was a false dichotomy about the wrapper, not the code `[review finding]`. I also cited "self-preference evidence" for it that appears nowhere in the evidence table.

**⚠ The steelman of your position, which the review sharpened and which I now think is stronger than v1 allowed:** building on `ghosts`, `verify.py`, `session_ledger` and `fix_receipt` *guarantees* attune-specific coupling, which makes "the portable part is thin" self-fulfilling. Extracting early is what forces a clean seam. And my v1 claim that deferring is "low cost" was an unlabelled assertion — I have no evidence about what the `attune-forms` extraction actually cost.

**Revised recommendation** `[PROP]`: build as `src/attune/lanes/` — **but write the seam against interfaces from day one**, which v1 did not propose and which is what makes the deferral honest rather than convenient. Concretely: `LaneManifest`, `LaneState`, `WorktreeProvider`, `OverlapChecker` and `ReceiptValidator` as protocols, with attune-specific policy (Class 3 list, receipt requirements, chair gates) injected as configuration rather than imported. Then extraction is a packaging change, not a rewrite. If a third consumer appears, extract as **`attune-lanes` on PyPI** — the proven path `[VRF]` — and ship a *skill* as the Claude-facing driver.

**Where you're right and I'd defer:** if the goal is that *other people's* repos adopt this, a plugin is the distribution channel and the argument flips. That is a product decision about audience, and it does not need making before the dogfood.

---

## Decision register for Patrick

**D1 — Split the dogfood: read lanes after P1/P2 clear; write lanes as a bounded experiment. ⚠ And consider dropping a seat instead.**
*Recommendation:* §8. Gate on §8.0.
*Counter:* ⚠ Strengthened by the review. If seats are as correlated as the evidence suggests (n_eff ≈ 2.18 across nine judges `[VEF]`; 3.7× excess co-failure `[VEF]`), the cheaper move is **dropping a seat** — ~33% less cost, a similar wall-clock effect, and none of the concurrency risk. The packet never considered this in v1. Parallelising three correlated seats may be optimising the wrong variable.
*Deferring:* The round table stays sequential for no reason, and the write-lane question gets answered by ad-hoc usage rather than measurement.

**D2 — Two-axis state machine; lanes reach `completed`, only the lead sets disposition; stale triggers re-verification, not rejection.**
*Recommendation:* §7.
*Counter:* Two axes is more machinery than one enum, and for five lanes a flat list is legible at a glance.
*Deferring:* A lane that can declare itself ready has been granted authority by omission. ⚠ And v1's stale-as-inadmissible would have silently capped Architecture B at one integrable write lane — a design-defeating bug found only by review.

**D3 — Model identity is captured from the invocation environment; self-report is inadmissible.**
*Recommendation:* `model_source` required, never `self_report`.
*Counter:* Bookkeeping that will drift.
*Deferring:* Reproducibility claims become unfalsifiable. ⚠ Two worked examples now exist in this packet's own production: the session that wrote it was addressed as "Fable 5.1" while configured as `claude-opus-5`, and the review agent's model version cannot be attested either (§0.1).

**D4 — Adopt the Class 3 always-serialized list before any write lane runs.**
*Recommendation:* §6 Class 3 as `forbidden_paths` defaults, enforced at `armed`.
*Counter:* Conservative — `pyproject.toml` and spec `tasks.md` are edited constantly.
*Deferring:* `merge=union` on a lockfile merges silently and incoherently `[VEF]`; a lane editing `decisions.md` resolves a governance question it has no authority to resolve. ⚠ Note the scoping fix: blanket-denying `.claude/**` or `.attune/**` breaks lane provisioning `[VRF]`.

**D5 — Central re-verification at the integration base is mandatory and non-waivable.**
*Recommendation:* No lane result integrated on its own receipts.
*Counter:* It is the expensive step and removes most of the wall-clock win.
*Deferring:* ⚠ **Weakened from v1, honestly.** The 17.2×/4.4× contrast is `[INF]` support (measured on coordinator architectures over largely non-coding traces), not proof. Test failures being the top reason agent PRs go unmerged is `[INF]` from a partially-verified source. The decision rests mainly on the structural argument — lane-authored tests verifying lane-authored code is not verification — plus lane 8, which is designed to produce direct local evidence.

**D6 — Containment is OS-level, default-deny egress, and covers `$HOME`.**
*Recommendation:* §8.6, all seven.
*Counter:* Disproportionate for a solo developer on a trusted repo.
*Deferring:* Twelve injection defenses fall at >90% ASR `[VEF]`, and s1ngularity's leverage was the agents' own bypass flags plus **home-directory** credential stores `[VEF]` — which v1's repo-scoped containment did not cover at all.

**D7 — Build inside attune-ai as `src/attune/lanes/`, but write the seam against interfaces from day one.**
*Recommendation:* §10.
*Counter:* ⚠ Strengthened. Building on four attune-specific subsystems guarantees coupling and makes "the portable part is thin" self-fulfilling; extracting early is what forces a clean seam. And "deferring is low cost" is an assertion — the actual cost of the `attune-forms` extraction is unknown.
*Deferring:* Lower cost **only if** the interface discipline is adopted with it. Without that, the counter wins.

---

## 11. Verification notes

**Known residual label defects** ⚠, named rather than quietly left: *"persists unsandboxed"* (§6 Class 3, §8.6 item 4) and *"every recorded incident defeated a policy control"* (§3 G1) are carried as `[VEF]` but are generalisations across sources rather than statements any single source makes. They should be `[INF]`. Flagged here rather than silently corrected, because the second review found them and the honest record is that this packet's own labelling needed three passes.

**Corrected in v2** (v1 asserted these; they were wrong or unsourced): the session ledger's concurrency guarantee; the attribution of deterministic synthesis to the round table; "lock files leak on SIGKILL" as applied to `flock`; "coordination returns go negative"; the 41.7% figure used as both removed risk and residue; the MCP-elicitation sourcing of the disposition vocabulary; the "~70%/~80% exists" estimates; D5's unsourced `[VEF]`; and roughly ten `[VEF]`s in the body with no evidence-table row (now added or demoted).

**Suspect, verify before quoting** — plausible, unconfirmed from my own knowledge: MCP revision `2026-07-28` and SEP-2663 "Final"; A2A v1.0 dated 2026-03-12 (v1.0.1 unresolved); OTel semconv v1.44.0 and the `semantic-conventions-genai` repo split; the Gemini CLI subagents post date; arXiv 2603.21489 authorship; MAST's framework count; and the mechanism in claude-code#34645 (`git worktree add` writing `.git/config`).

**Could not confirm:** METR's 95% CI (not published); OWASP 2026 exact ID-to-title mapping; RFC 9110 §13.1.1 verbatim (quoted wording is from RFC 7232, which 9110 obsoletes); the Gray & Cheriton paper body (bibliographic details only — all lease mechanics quoted come from Chubby); npm automatic lockfile conflict resolution; CVE-2025-54794; Google first-party Antigravity security documentation (404); Apple's `sandbox-exec` deprecation timeline; SLSA v1.2 per-level requirements; arXiv:2602.00164's authors, date and overall unmerged rate.

**Repository facts** were gathered read-only on 2026-09-02 at `78661a787`, **4 commits behind `origin/main`**, in a working tree with 7 modified and 7 untracked paths. Nothing in the repository was edited, committed, or branched. ⚠ **Absence claims are the stale ones — re-verify after P4.**

---

## 12. Open items before Patrick decides

From the second review's must-fix list. Items 1–4 were closed in v2.1; 5–9 are implementation-time and do not affect the decision.

**Closed in v2.1** — §8.5 split into independent read and write verdicts with shared disqualifiers; `scope_violations` restored as a disqualifier; rework threshold made absolute (lead-minutes per integrated patch); the wall-clock denominator corrected to the replicates' own spread; the unreachable P2 clause removed; finding-identity pre-registered with a judged-fraction ceiling; baseline replicates raised to ≥3; write-baseline provider assignment stated; dogfood cost totalled against the cap (**≈$21 for the write half against a $10 default — this is P2a**); and **A0/A0b answered from source** (§0.5).

**Still open, and none needs new research:**

| | Item | Blocks |
|---|---|---|
| P2a | Decide: fix the spend TOCTOU, or raise the cap explicitly for the run and reconcile manually | Write lanes only |
| P3 | Time the sequential round table, ≥3 replicates | E1 |
| P4 | Fetch `origin/main`; re-verify the absence claims | §10's conclusions |
| P5 | Confirm no submodules | Write lanes |
| — | Implementation-time: process-group-empty release with SIGTERM→SIGKILL escalation; worktree-relative manifest paths with siblings outside every mount; orchestrator-assigned `attempt`; pipe-EOF orphan wrapper; per-lane HOME credential provisioning; canonical `positions` ordering and an atomic invocation counter | E1/E2 code, not the decision |
