# attune-author Consolidation — Decisions

**Status:** draft (2026-06-30) · log for
[requirements.md](requirements.md) / [design.md](design.md).

## D1 — The split is authoring vs. mechanics, not "the package"

**Decided.** The unit of the retire/absorb decision is not the package but
the *kind of work* each part does. Authoring (judgment) → the driving
session + a skill; mechanics (deterministic transform/hash/verify) → code
in attune-ai. A model is the right tool for the first and the wrong tool
for the second, because the second's value is invariance. This is the line
the whole spec follows; everything else is bookkeeping.

## D2 — Absorb the projector/staleness/fact-check; do NOT replace them with instructions

**Decided.** Pushback resolved: "replace code with instructions" is right
for the LLM authoring machinery and *wrong* for the deterministic
distribution machinery. The projector's value is that the fan-out can't
vary; staleness is a hash comparison; the import gate is deterministic
truth. Replacing any of these with model judgment reintroduces the drift
single-source exists to eliminate. They move as code.

## D3 — Retire the authoring machinery; the session replaces it

**Decided.** `generator`/`polish`/`doc_gen`/`maintenance_batch`/
`faithfulness` and the `ai` deps are deleted, not absorbed. The lesson is
empirical: the keyless regen is a content-*stripping* regression and the
driving session is a *superior* polish layer that also catches correctness
bugs the API polish cannot. We are deleting a measured-worse path.

## D4 — Fold #1191's T1 into the move, don't bolt it on

**Decided.** #1191 (merged spec) called for an authoritative resolver. Its
T1 originally meant "wire attune-ai's resolver across the package line."
Once the fact-check moves *into* attune-ai (D2), the resolver is just a
shared in-repo helper — strictly cleaner. So #1191's implementation
happens *inside* this consolidation (design Step 2 / T2), not as a separate
cross-package patch. The merged #1191 spec stays the rationale; this spec
is its execution venue.

## D5 — Code move and package retirement are SEPARATE decisions

**Decided.** Moving the code into attune-ai (reversible, low-risk) and
yanking the `attune-author` PyPI package (irreversible-ish) are decoupled.
Capture the architectural win first (T1–T3); make the package's fate a
deliberate, later step (T4). Because there are no adopters (confirmed
beta), archive-and-yank is viable — but it's still its own PR so the
irreversible action is intentional.

## D6 — `polish_template` degrades, by design

**Decided.** `personal.py`'s optional polish (the one non-docs consumer of
the LLM path) drops to its existing `_build_skeleton` fallback. It is safe
(already `try/except → None`) and consistent with the thesis (no API
polish; the session is the polish layer). Named as a behavior change in
the changelog, not discovered silently later.

## D7 — Absorb staleness as-is; fixing it is a separate spec

**Decided.** `staleness.py`'s known weaknesses (single-file hash, no
completeness check — lessons corpus) are real but out of scope. Absorbing
and then rewriting in one move would balloon the change and couple a
mechanical migration to a behavioral redesign. Absorb first; the staleness
hardening is a tracked follow-on.

## D8 — Dogfooding the absorb reframes T2: it is a bug-fix + design call, not a mechanical repoint

**Decided (2026-07-01).** Refines D7. Copied `staleness.py` +
`manifest.py` + `freshness/symbols.py` verbatim into `attune.authoring`
(imports repointed, provenance headers, imports clean). Then dogfooded the
absorbed `check_staleness` against this repo's real `.help/` — and against
the *current* live behavior of the `help_data` consumer — and found two
facts that make a "behavior-preserving repoint" of `help_data` impossible:

1. **The current dashboard staleness signal is a masked crash.** The
   `attune-author` CLI shim on this machine points at a Python without
   `attune_author` installed → `ModuleNotFoundError`. `help_data`'s
   `_attune_author_stale_features` runs it via `subprocess.run(check=False)`,
   the subprocess exits non-zero with an empty stdout, and
   `_parse_status_output("")` returns `frozenset()`. So a **crash reads as
   "nothing stale"**, and because the return is an empty set (not `None`),
   callers never reach the age-based fallback. This is a latent bug the
   absorb surfaced — a broken CLI silently reports every feature fresh.
2. **Hash-staleness is N/A for this repo.** Post single-source rollout all
   27 features are `status: manual` with **no `files:` globs**
   (projector-owned from `content/features/*.md`). `manifest.py` doesn't
   even parse the `status` field — manual-skip lives in the generator layer,
   not in `check_staleness`. So a faithful `check_staleness` computes the
   empty-input hash for every feature and flags **all 27 stale** (leftover
   stored hash ≠ empty). Faithful behavior is pure noise here.

So T2 is not "absorb → repoint, behavior-preserving." The current behavior
is a bug; the faithful behavior is noise. Doing it right means teaching
staleness to treat glob-less/manual features as **untracked (N/A)** — a
product-semantics decision. **Parked** (Patrick, ~5am) to make that call
rested. The three absorbed modules live on branch `feat/authoring-staleness`
(WIP, no PR) for the next session. Pairs with the "registered ≠ working /
dogfood the real path" and "should-this-exist" (removing-dead-code) lessons.

## Open

- **Staleness semantics for single-sourced/manual features** (from D8) —
  glob-less features should be reported as *untracked*, not *stale*. Decide
  the shape (skip in `check_staleness`? filter in `help_data`?) before the
  absorb lands.
- **Fix the masked-crash bug regardless** (from D8) — `help_data` should
  distinguish "CLI failed" (→ `None` → age fallback) from "genuinely
  nothing stale" (→ empty set). Small, shippable independent of the absorb.
- **Where exactly the absorbed module lives** — settled toward
  `attune.authoring` (T1 landed there); the staleness trio follows.
- **Shim vs. archive** for the package (T4) — decide with the (near-zero)
  download numbers in hand at execution time.
