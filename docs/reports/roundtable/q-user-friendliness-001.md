# Round table — increasing attune-ai's user-friendliness (q-user-friendliness-001)

**Thread:** `q-user-friendliness-001` · **Date:** 2026-07-23 ·
**Roster:** claude, antigravity, codex · **Rounds:** 2 (halted on
convergence, D3) · **Promoted items:** #2 #3 #4 #8 #9 #10 #11
(chair-approved; ruling #12).

Chair ruling (2026-07-23): promote this report; QUEUE for the
07-27 sitting — golden-path first-contact design, activation-metric
adoption (return-visit definition recommended), single-provider
first-five pitch ruling; UNPARK the attune-ai.dev 404 fix as a
chip task (redirect-first, tar-pit trip-wire). Build items do NOT
start now — usage reads pick what's next per the north star.

## #1 — question (chair)

> What can be done to increase the user-friendliness of attune-ai?
>
> Grounding (current product state, 2026-07-23):
> - attune-ai is an AI developer-workflow plugin for Claude Code
>   (PyPI 10.5.0; 10.6.0 releases 07-27): 25 auto-triggering skills,
>   53 registered MCP tools, CLI (`attune`), multi-LLM roundtable
>   (Claude/Antigravity/Codex seats), cross-provider shared memory
>   (Redis-derived index), ops dashboard (FastAPI, localhost).
> - Install is zero-config (`pip install attune-ai`), subscription-first
>   routing with API fallback. Codex marketplace + Antigravity MCP
>   config are secondary distribution channels.
> - Core UX principle: Socratic discovery — workflows ask scoping
>   questions (AskUserQuestion forms) before executing; `/attune` routes
>   any request; `/coach` gives progressive help (concept -> procedural
>   -> reference); a living `.help` system (AI-maintained templates) and
>   mkdocs site back it.
> - Known reality checks: phone-home telemetry shipped default-OFF and
>   external usage signal is ~0 — the maintainer's standing task is
>   "talk to 5 real users"; docs site (attune-ai.dev) currently 404s its
>   mkdocs tree (parked); the sole active user today is the maintainer
>   (dogfooding); marketplace directory submission awaiting approval.
> - Post-10.6.0 north star: multi-LLM collaboration is the emerging
>   identity; growth surface = cross-provider adapters; usage-signal
>   reads (07-27) pick what's next.
>
> Answer for THIS product at THIS stage (pre-first-real-users), not a
> mature product: what changes would most increase user-friendliness,
> for whom (first-touch installer, daily driver, non-Claude-provider
> user), and what would you deliberately NOT do yet?

## #2 — position, round 1 (claude, 34s)

POSITION: User-friendliness pre-first-real-users = "can a stranger
get from pip install to one visible win in under five minutes,
unassisted." Three moves, in order:
1. Repair the front door: attune-ai.dev 404ing its mkdocs tree is
   the single worst UX bug — it fires before any UX inside the tool
   can. Even a temporary redirect to GitHub-rendered docs beats a
   404. Hours, not a project (tar-pit trip-wire: it was parked over
   a trailingSlash-vs-mkdocs conflict — if the fix fights back,
   ship a redirect and stop).
2. Golden path, not a catalog: 25 skills / 53 tools is a wall. A
   first-run experience detects the repo, runs ONE high-value
   workflow end-to-end on the user's actual code (bug-predict or
   security-audit), shows the receipt, then names exactly three
   next steps. Catalog stays behind /catalog. Soften Socratic for
   first contact: demo-first-once, Socratic-by-default after.
3. Then STOP and do the standing task: "talk to 5 real users" IS
   the highest-leverage UX work. The 07-27 read should include one
   live-observed onboarding.
FOR WHOM: almost entirely the first-touch installer. Daily driver =
maintainer, already served. Non-Claude polish is premature —
second floor first.
NOT YET: onboarding wizard/GUI, videos, broad doc rewrites, more
elicitation surface, config options, telemetry expansion, skill
consolidation (curating the entry point is cheap; deleting skills
before usage signal exists risks removing what a first user loved).
RISK: optimizes a funnel with zero people in it, using maintainer
intuition as proxy for stranger behavior — the exact failure mode
the 5-users task corrects. Real friction may be upstream: value
proposition and trust, not navigation. If so: recruit 5 users
first, fix 404 second, build nothing else until they speak.
QUESTION: Should the first-five pitch (and golden path) lead with
the multi-LLM roundtable — the differentiator, but a three-provider
setup burden — or a single-provider five-minute win that onboards
easily but looks like a dozen other plugins?

## #3 — position, round 1 (antigravity, 43s)

### 1. Position

At the **pre-first-real-users stage**, user-friendliness is strictly a function of **time-to-first-value** and **baseline trust**. Adding features, skills, or complex scoping prompts right now will increase cognitive load before a user understands what `attune-ai` does.

To maximize user-friendliness at this exact juncture:

* **For the First-Touch Installer (Zero-Friction Landing)**:
  * **Fix the baseline surface first**: Repair the 404ing `attune-ai.dev` documentation tree immediately. A 404 on initial discovery destroys trust before installation.
  * **Default-to-Action over Socratic forms on first run**: Replace multi-field Socratic discovery forms on initial command executions with sensible zero-config defaults + a post-execution refinement hint. Socratic forms gate value behind interrogation when the user doesn't yet know what answers to give.
  * **Add a single zero-dependency onboarding command (`attune doctor` / `/attune-doctor`)**: Run a 5-second environment check (API keys, Redis reachability, MCP registration) and execute a minimal sanity check workflow so the user sees `attune-ai` work in under 30 seconds.

* **For Non-Claude-Provider Users (Codex & Antigravity Seats)**:
  * **Auto-discover environments**: Automate MCP tool and adapter registration via standard environment paths so non-Claude users don't have to manually configure sidecars or Redis index connections. Silent degradation when Redis is missing must remain rock-solid.

* **For the Daily Driver**:
  * **Streamline routing feedback**: Make `/attune` routing outputs visually transparent (showing *why* a specific skill/workflow was chosen and estimated API cost tier) to build confidence in automated execution.

#### What to DELIBERATELY NOT do yet:
* **Do NOT expand the skill count** beyond the existing 25 skills.
* **Do NOT invest in building out the FastAPI ops dashboard GUI**.
* **Do NOT build complex opt-out/opt-in telemetry infrastructure** until the maintainer completes direct 1:1 user feedback sessions with the first 5 real users.

---

### 2. Main Risk

**Loss of Scope Control and Increased Unintended API Costs**.
Bypassing initial Socratic discovery forms in favor of immediate execution with smart defaults risks running multi-agent workflows on under-specified user prompts. If an LLM misinterprets an un-scoped command, it could execute redundant subagents or consume extra token quota, undermining `attune-ai`'s core value proposition of cost optimization and guided orchestration.

---

### 3. Follow-Up Question for the Table

*"Should we pivot initial workflows to 'execute immediately with conservative defaults and offer refinement after', or does preserving mandatory pre-execution Socratic forms remain essential to protect users from unexpected LLM API spend?"*

## #4 — position, round 1 (codex, 17s)

1) POSITION: Optimize for a first successful outcome, not more capability. Before building new features, recruit five external users and observe them install attune-ai, choose a task, and complete it without maintainer guidance. Use those sessions to create one paved journey:

- First-touch installer: after install, run a 60-second readiness check, explain in plain language what attune can do, and offer three concrete starter outcomes. `/attune` should route directly into one, with an escape hatch to skip Socratic questions.
- Daily driver: reduce repeated questioning by remembering project preferences and showing a concise execution preview: goal, actions, provider(s), cost/approval boundaries, and expected artifact. End with a useful receipt and an obvious next action.
- Non-Claude-provider user: provide one canonical adapter setup command per provider, then verify it with a real round-trip and clearly report which capabilities are available or degraded.

Immediately fix or temporarily redirect the broken docs site; a 404 destroys trust at first touch. Instrument only local/default-private funnel events, with an explicit opt-in for sending aggregate telemetry. Pair that with interviews because telemetry cannot explain confusion.

I would deliberately not add more skills, MCP tools, dashboard features, provider adapters, or elaborate onboarding personalization yet. Nor would I make telemetry default-on. The current problem is unvalidated comprehension and activation, not insufficient surface area.

2) MAIN RISK: Five early users may produce noisy, contradictory feedback, and overfitting the paved journey could hide attune-ai’s broader multi-LLM identity or weaken the Socratic workflow that differentiates it.

3) FOLLOW-UP QUESTION: What single user-visible outcome should define activation—for example, “completed one workflow and used its artifact”—and can all three provider paths be measured against it?

## #8 — position, round 2 (claude, 40s)

(A) FIRST-CONTACT: first run = no ~/.attune/state/first_run.json
marker, checked at every entry point. Bare first /attune skips the
scoping form and runs a read-only demo on the user's actual repo
(bug-predict/quality on git-recently-changed files, capped). One
preview LINE (not a confirm): "Running quality scan on 12
recently-changed files — subscription routing, no API spend.
Ctrl-C to stop." Post-execution refinement hint is where Socratic
lives at first contact: invited after value, not imposed before.
Second invocation on: Socratic-by-default for ambiguous asks;
stated preferences remembered per-project, never re-asked.
Specificity IS the escape hatch — a user arriving with "audit src/
for secrets" never sees the demo. SPEND: structural, not
conversational — first run pins subscription-only (API fallback
hard-disabled until the marker exists); fallback thereafter is
one-time opt-in + per-engagement estimate line with y/n — a spend
gate at the moment of spend, never a form at the moment of
curiosity. ATTUNE_MAX_BUDGET_USD defaults to a small cap.

(B) SINGLE-PROVIDER five-minute win. The first five must reach
activation before differentiation can matter; a 3-provider
credential burden multiplies drop-off pre-value. Roundtable =
day-2 reveal, surfaced contextually at the first judgment-shaped
question ("want a second opinion from another model?") — it demos
better against already-experienced single-provider value.

(C) ACTIVATED = a second workflow run completes on the user's own
repo, in a session distinct from first-run, within 7 days of
install. Operationally: two workflow_completed events in local
~/.attune/telemetry/usage.jsonl with distinct session ids,
target repo ≠ demo/attune's own, non-empty output. Emitted in
attune core below the provider adapter seam — all three paths
count identically; measurable default-private, no phone-home.
First run measures curiosity; a return measures value.

## #9 — position, round 2 (antigravity, 43s)

### (A) FIRST-CONTACT DESIGN

**1. First-Run Detection**
`attune` checks for the existence of `~/.attune/state.json` (or project-local `.attune/state.json`). If `first_run_at` is absent, First-Contact Mode triggers.

**2. What Runs & Reconciled Interactive Behavior**
We reconcile *demo-first-once*, *defaults + post-execution refinement*, and *escape hatch* into a **Zero-Gate Run with Post-Execution Refinement**:
* **Immediate Zero-Gate Execution:** The moment the user types `attune` (or invokes the skill in Claude/AGY/Codex), `attune` executes a 5-second, non-destructive, subscription-routed audit on the local workspace (`attune discovery-sweep --dry-run`). No preliminary questionnaire, no form, no blocking questions.
* **Inline Result + Refinement Hint:** The output displays the initial findings immediately, followed by a non-blocking footer prompt:
  > *Result ready (0 paid API tokens used).*
  > `[Press Enter to accept defaults | Type /elicit to customize scope | Type /roundtable for multi-LLM review]`
* **Subsequent Behavior:** The Socratic scoping form (`/elicit`) remains the core UX for complex, ambiguous workflows, but on First Contact, it appears **after** value is demonstrated as a suggestion, never before as a gatekeeper.

**3. Spend Protection Without Scoping Interrogation**
* **Strict Default Guardrail:** First-Contact Mode forces `routing.allow_paid_api_fallback = False`. All work executes via available subscription endpoints or zero-cost local heuristics.
* **Explicit Cost Gate Only On Failover:** If a workflow explicitly requires a paid API call (e.g., no active subscription token present), `attune` halts with a single explicit confirmation prompt showing estimated ceiling cost: `Paid API required (~$0.02 max). Proceed? [y/N]`. No interactive scoping survey is required just to guard spend.

---

### (B) FIRST-FIVE PITCH

**Choice:** **Single-provider five-minute win.**

* **Reason:** Friction at minute zero kills activation faster than lack of differentiation; proving instant value using whatever single provider credentials or subscription the user already has active establishes the credibility needed to ask for multi-provider setup.
* **What the multi-LLM Roundtable becomes:** **The Day-2 Level-Up.** After the user completes their first single-provider win, `attune` surfaces a contextual hint: *"Want Claude, Antigravity, and Codex to deliberate on your next refactor? Run `/roundtable` to configure secondary providers."*

---

### (C) ACTIVATION METRIC

**Definition:** **First Verified Local Receipt Created.**

A user is "Activated" when `attune` logs a local event indicating that a workflow completed with exit status `0` and generated a verified local output artifact (such as a passing test receipt, a generated/projected spec file, or an applied clean diff) within 24 hours of first-run detection.

**Measurability across all engines (Claude, Codex, Antigravity):**
* Tracked locally and privately in `~/.attune/usage_telemetry.json` (or `.attune/telemetry.json`).
* Standard payload written uniformly regardless of client interface:
  `{"event": "activation_receipt_generated", "workflow": "<workflow_id>", "provider": "<active_provider>", "timestamp": "<ISO-8601>"}`
* Evaluated by reading local signal files during audit sittings without requiring telemetry server uploads or remote network calls.

## #10 — position, round 2 (codex, 17s)

(A) On first invocation, detect first contact from the absence of a versioned local project preference file. Show a three-line execution preview:

> I can inspect this project and return one prioritized, evidence-backed improvement.
> Read-only; no files will change. Subscription routes are preferred. API fallback requires confirmation.
> Press Enter to run, or type what you want help with.

Enter runs the same provider-neutral golden path: inspect repository context, execute one bounded read-only analysis using conservative defaults, and return one concrete finding with evidence plus a recommended next action. Free text enters normal Socratic discovery; `skip` opens the command/catalog escape hatch.

After the result—not before—ask one refinement question: “Should future runs optimize for fixes, tests, review, or planning?” Remember the answer per project, while keeping it editable and showing the execution preview on materially different actions.

Spend protection is route-level, not an upfront interrogation: use authenticated subscription routes first; if none can complete the run, stop before any billed API call and show the provider, estimated maximum spend or token cap, and an explicit `Approve API fallback` action. No consent, no charge. Mutating work always gets its own preview and confirmation.

(B) Lead with the single-provider five-minute win: the first five users must reach value before setup complexity can obscure whether the product is useful. The multi-LLM roundtable becomes the day-two reveal: “Now challenge this result with two independent models,” with provider setup guided only when chosen.

(C) Activated means: **within a project, the user completes one Attune workflow that produces a concrete result and then takes an explicit result-level action—accepting the recommended next step, requesting refinement, or saving/applying the output.**

Measure this locally as a provider-neutral pair: `workflow_result_presented` followed by `result_action_taken`, sharing project-scoped run ID and occurring within 24 hours. Merely invoking Attune, viewing a catalog, configuring providers, or receiving an error does not count.

## #11 — synthesis (moderator)

SYNTHESIS (moderator, after 2 rounds — halted on convergence).

UNANIMOUS FRAME: at the pre-first-real-users stage,
user-friendliness = time-to-first-value + baseline trust, for the
FIRST-TOUCH INSTALLER above all. The daily driver (the maintainer)
is already served; non-Claude onboarding polish is premature until
the Claude path converts a stranger.

RANKED CONSENSUS ACTIONS:
1. FIX THE FRONT DOOR (3/3, round 1): attune-ai.dev 404ing its
   mkdocs tree is the worst UX bug in the product — it fires
   before any in-tool UX can. Even a temporary redirect to
   GitHub-rendered docs beats a 404. Tar-pit trip-wire: parked
   over a trailingSlash-vs-mkdocs conflict — if the real fix
   fights back, ship the redirect and stop.
2. FIRST-RUN GOLDEN PATH (3/3, converged design in round 2):
   - Detection: local first-run marker, checked at every entry
     point (CLI, /attune, MCP dispatch).
   - Bare first invocation runs ONE bounded read-only analysis on
     the user's actual repo with conservative defaults
     (recently-changed files, capped) — no scoping form. A 1-3
     line preview states scope + "read-only" + "no API spend";
     seats split only on Enter-to-run (Codex) vs run-with-Ctrl-C
     (Claude/Antigravity) — chair's call, cosmetic.
   - Socratic RELOCATED, not removed (binding principle intact):
     the refinement question comes AFTER the demonstrated result;
     Socratic-by-default resumes from invocation two for ambiguous
     asks; stated preferences remembered per-project.
   - Specificity is the escape hatch: a user who arrives with a
     concrete request never sees the demo.
   - SPEND PROTECTION IS STRUCTURAL (3/3, near-identical): first
     run pins subscription-only routing with API fallback
     hard-disabled; thereafter fallback requires explicit consent
     at the moment of spend with an estimate line. No scoping
     interrogation needed to guard money.
3. TALK TO / OBSERVE THE FIRST FIVE USERS (3/3): itself the
   highest-leverage UX work; build almost nothing else until
   they've spoken. Include one live-observed onboarding.
4. FIRST-FIVE PITCH (3/3, round 2): lead SINGLE-PROVIDER
   five-minute win; the multi-LLM roundtable is the DAY-2 REVEAL,
   surfaced contextually at the first judgment-shaped question.
   Differentiation cannot matter before activation.

ACTIVATION METRIC (split, moderator recommendation): Claude wants
a RETURN signal (2nd completed workflow, distinct session, own
repo, ≤7 days); Codex wants an ENGAGEMENT signal (result presented
+ explicit result-level action, ≤24h); Antigravity wants first
verified receipt (weakest — measures success of run 1, not
value). Recommend: adopt Claude's return-visit metric as THE
activation definition (honest value signal, provider-neutral,
locally measurable from usage.jsonl), with Codex's
result-action-taken as a leading indicator. Formal adoption
belongs to the 07-27 usage-signal sitting.

UNANIMOUS DO-NOT-YET: expand skills/tools; dashboard GUI
investment; telemetry expansion (local/default-private only);
non-Claude onboarding polish; skill consolidation; onboarding
wizard/GUI; broad doc rewrites.

STANDING RISK (Claude round 1, unrebutted): all of this optimizes
a funnel with zero people in it — if first-user friction is
upstream (value proposition/trust), the golden path is polish on a
door nobody is opening. The 5-user observation corrects this;
schedule it before building item 2.
