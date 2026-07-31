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

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-user-friendliness-001.md` and is
not distributed with the repository.*
