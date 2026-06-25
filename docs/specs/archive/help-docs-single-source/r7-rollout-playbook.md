# R7 — Rollout Playbook: Single-Source Help + Docs

**Status:** rollout COMPLETE (2026-06-24) — every feature is
single-sourced (`status: manual`); the `remaining` set in
`.help/features.yaml` is empty. Drafted from the pilot (2026-06-21);
**nav/hub gate implemented** (P4/P6 done via the help-docs-rollout-gate
spec, 2026-06-21) — the per-feature loop no longer requires a manual
`mkdocs.yml` edit. The recipe below stays the canonical procedure for
single-sourcing any NEW feature. · **Builds on:** [design.md](design.md),
[decisions.md](decisions.md) (D6–D13),
[t2-projector-build.md](t2-projector-build.md),
[follow-ups.md](follow-ups.md)

This is the per-feature procedure for migrating a feature off
LLM-generated help/docs and onto the deterministic projector. It is
written from executing the full chain on two contrasting features —
`spec-engine` (Python-API shape) and `models` (CLI/tabular shape).

---

## What the pilot proved

- The chain works end-to-end: one hand-authored master file
  (`content/features/<feature>.md`) → `attune_author.projector` →
  **10 non-faq `.help` kinds + 3 docs pages** (how-to, architecture,
  reference), fact-checked, served unchanged by the live consumer,
  `mkdocs build` clean.
- **The win is real.** Projection replaced concrete LLM fiction with
  grounded hand-authored content. Examples caught and killed:
  - `spec-engine`: a fictional `spec-engine [OPTIONS] SUBCOMMAND` CLI
    (it has no CLI — `/spec` is a skill); properties called as methods
    (`result.summary()`, `.success()`, `.severity()`); a sync call to
    the async `execute_with_approval`.
  - `models`: property-vs-method and a sync/async executor error,
    avoided by grounding against the real API.
- **Fact-check is a live guard, not decoration.** `cli_refs` runs the
  real `attune <sub> --help` for every backtick `` `attune <sub>
  --flag` `` reference. Injecting a fake `--bogus-flag` into the
  `models` master produced exactly one finding
  (`flag not found in attune auth status --help`); the real flags
  passed. Author CLI content from real `--help` output.

---

## Per-feature procedure

For each feature `<F>`:

1. **Author `content/features/<F>.md`** by consolidating the existing
   hand-authored `docs/` pages + the good parts of the current `.help`
   corpus into the master-file schema (frontmatter + the named H2
   sections — see design.md). No invented prose; this is a merge that
   preserves the hand-authored feel. Ground every API/CLI claim in the
   real code: read the source, capture exact signatures, and note
   **property vs method** (the most common fiction). For CLI features,
   copy flags from real `<cli> <sub> --help`.

   Frontmatter must include `feature`, `summary`, `tags`,
   `source_globs` (drives fact-check + import_repair), and `nav.mkdocs`
   with `how-to` / `architecture` / `reference` (omit `tutorial`).
   Add `cli: { command: <name> }` for CLI-backed features (declarative;
   not rendered, but records intent).

2. **Fact-check (warn-only):** `python scripts/project_features.py <F>
   --dry-run`. Resolve every finding in the master file before the real
   write — a clean dry-run is the quality bar (0 findings, as both
   pilot features achieved).

3. **Project (real write):** `python scripts/project_features.py <F>`.
   Writes 14 outputs (10 `.help` + how-to/architecture/reference docs +
   the Variant-1 **hub** at `docs/features/<F>.md`). `faq` and `tutorial`
   are skipped by the driver's `skip_kinds`. The hub (attune-author 0.21.0,
   D11) heroes the first present of tutorial → how-to → reference and
   grids the remaining present {how-to, reference, architecture} — fully
   automatic, no per-feature authoring.

4. **Diff the win:** `git diff .help/templates/<F>/`. Confirm fiction
   is replaced (no invented CLIs, no property-as-method, no
   sync-vs-async errors). This diff is the deliverable, not a
   regression.

4b. **Adversarial fact-check the prose (MANDATORY).** The static
   fact-check (step 2) only proves symbols/imports/CLI-flags exist — it
   is structurally blind to *behavioral* and *runtime* correctness.
   Run an adversarial reviewer (or a careful human pass) over the
   master file, specifically checking: (a) procedural claims ("edit X
   to extend Y" — is X actually the thing you edit, or is it derived?);
   (b) behavioral claims (defaults, what drives control flow, what a
   function actually returns); (c) **async/runtime correctness of every
   code example**. For (c), run the example-execution gate
   `scripts/check_doc_examples.py content/features/<F>.md` (with
   `PYTHONPATH=<worktree>/src` + the main venv) — it compiles each
   block and flags coroutine functions called without `await`,
   grounding "is it async?" in the real code. The pilot found
   real bugs here that the fact-checker AND two LLM reviewers missed
   (a derived map documented as hand-edited; an `async` `run_all`
   called synchronously across a whole file; reversed AUTO-mode logic;
   wrong dict keys). See follow-up P5.

5. **Verify serve through BOTH consumers** (see "Verification" below) —
   all 10 projected kinds serve with non-empty bodies on each:
   - **Probe 1 — ops dashboard** (`attune.ops.help_data`): feature
     reports complete (faq retained).
   - **Probe 2 — in-conversation** (`populate` / MCP `help_lookup`):
     `populate("con-<F>")` (and the other kinds) return non-empty bodies
     and `populate_progressive("<F>")` is not `None`. **Required
     acceptance** — a green Probe 1 with a `None` Probe 2 means the
     content reaches the dashboard but NOT conversation users (the
     "projected ≠ served" trap that hid through 9 features). Never
     declare a feature done on Probe 1 alone.

6. **Verify mkdocs:** `mkdocs build --strict`. **No per-feature
   `mkdocs.yml` edit is needed** (P4/D12 implemented): the
   `docs/hooks/feature_nav.py` `on_config` hook wires the hub into the
   top-level **Features** nav section automatically, and the architecture
   page builds (the blanket `architecture/` exclude is dropped). The only
   exception is a feature that still carries a **pre-pilot legacy**
   `architecture/<F>.md` exclude line in `mkdocs.yml` — remove that one
   line when you migrate it. Net-new features need nothing.

7. **Apply DD5 (only after serve verified):** remove the `<F>` entry
   from `.help/features.yaml` so the weekly help-freshness regen never
   runs `attune-author generate <F> --all-kinds` and overwrites the
   projected content. Leave a comment in place (see the spec-engine /
   models entries for the template). The retained `faq.md` stays on
   disk, served, frozen.

---

## Verification recipe (copy-paste)

A feature has **two** served surfaces, and BOTH must be probed — the
Tier-1/2/3 rollout verified only the first and shipped 9 features that
the second never served (the "projected ≠ served" trap; fixed by the
help-serving-bridge resolver fallback, 8.9.1). Run **both** probes
below for every feature; the in-conversation one is non-negotiable
acceptance.

Use the **main** venv's python + `PYTHONPATH=<worktree>/src` for both
(the worktree venv lacks the `[ops]` extras; the editable-install
MAPPING otherwise points `attune` at the main checkout — see CLAUDE.md).

### Probe 1 — the ops dashboard surface (`attune.ops.help_data`)

The living-docs dashboard reads the feature-dir `.help/templates/<F>/`
layout directly — **not** `attune_help.HelpEngine(template_dir=...)`
(the t2 check named the latter, but the HelpEngine override path needs a
`cross_links.json` and a kind-pluralized layout, so it silently falls
back to bundled templates and misses the feature dir).

```bash
PYTHONPATH=<worktree>/src <main-venv>/bin/python - <<'PY'
from pathlib import Path
from attune.ops.config import Config
import attune.ops.help_data as hd
cfg = Config(project_root=Path("<worktree>"), attune_home=Path("/tmp/x"))
feat = {f.name: f for f in hd.list_features(cfg)}["<F>"]
print("kinds:", feat.kinds, "complete:", feat.is_complete)
for k in ("concept","task","reference","quickstart","comparison",
          "error","troubleshooting","warning","note","tip"):
    r = hd.get_template(cfg, "<F>", k)
    print(k, "OK" if r and r.body else "MISSING", len(r.body) if r else 0)
PY
```

### Probe 2 — the in-conversation surface (`populate` / MCP `help_lookup`)

**This is the one the rollout missed.** MCP `help_lookup` →
`attune.help.engine.populate` / `populate_progressive` resolve against
the type-organized bundle first, then fall back to
`.help/templates/<F>/<kind>.md` (8.9.1+). If this probe returns `None`,
the grounded content is NOT reaching conversation users no matter how
green the dashboard probe is. Assert it for every feature:

```bash
PYTHONPATH=<worktree>/src <main-venv>/bin/python - <<'PY'
from attune.help.engine import populate, populate_progressive
F = "<F>"
prefix_kind = {"con":"concept","tas":"task","ref":"reference",
               "qui":"quickstart","com":"comparison","err":"error",
               "tro":"troubleshooting","war":"warning","not":"note",
               "tip":"tip","faq":"faq"}
missing = []
for prefix in prefix_kind:
    r = populate(f"{prefix}-{F}")
    if r is None or not r.body.strip():
        missing.append(prefix)
assert populate_progressive(F) is not None, f"progressive: {F} not served"
assert not missing, f"NOT served in-conversation: {missing}"
print(f"in-conversation surface OK — {F} served via populate()/help_lookup")
PY
```

---

## Known gotchas (from the pilot)

- **Title degradation (P1).** Projected `.help` files have no `# H1`,
  so dashboard card titles fall back to `"<F> / <kind>"`. Cosmetic,
  graceful — fixed properly by the attune-author `_wrap_help` change
  (P1). Don't hand-patch per feature.
- **DD5 is all-or-nothing (D9).** `features.yaml` has no per-`.help`-
  kind field, and the weekly regen is `generate <F> --all-kinds` per
  feature. You cannot "keep faq regenerating, skip the other 10" with
  0.19.0 — remove the whole feature. faq freezes (acceptable: the FAQ
  Generator is its eventual owner; FG1). P3 is the cleaner future path.
- **Tutorial is not projected (D10).** It stays hand-authored.
  Restore `docs/tutorials/<F>.md` from the pre-projection version if a
  prior `--all-kinds` run clobbered it.
- **mkdocs nav wiring is automatic (P4/D12 — IMPLEMENTED).** The
  `docs/hooks/feature_nav.py` `on_config` hook builds the top-level
  **Features** nav section from `docs/features/*.md` at build time (one
  entry per hub). The blanket `architecture/`/`features/` excludes and the
  per-feature `!architecture/<F>.md` re-includes are gone, so a projected
  feature's hub + architecture page build with no per-feature `mkdocs.yml`
  edit. how-to/reference/architecture stay "not in nav" by design (reached
  via the hub + search). Only pre-pilot legacy `architecture/<F>.md`
  exclude lines need a one-line removal at migration.
- **Worktree traps.** `project_features.py` resolves the repo root from
  its own path, so it writes to the worktree correctly — but any
  verification that imports `attune` needs `PYTHONPATH=<worktree>/src`
  or it runs the main checkout's code against the main checkout's
  `.help`.

---

## Prerequisites / sequencing before bulk rollout

Resolve these first so the per-feature loop is mechanical:

1. **P4 — nav-wiring convention. ✅ DONE (2026-06-21).** Implemented as
   `docs/hooks/feature_nav.py` + the `mkdocs.yml` `hooks:`/exclude
   cleanup (help-docs-rollout-gate T3). The per-feature loop no longer
   needs a manual `mkdocs.yml` edit; `mkdocs build --strict` is clean and
   lists both pilot hubs. **P6 — hub-emit ✅ DONE** alongside it
   (attune-author 0.21.0 `projector._render_hub`, gate T1/T2).
2. **P1 — `_wrap_help` H1.** Otherwise every feature ships a degraded
   dashboard title. (attune-author release + pin bump.)
3. **P2 — drop tutorial from `DOCS_PAGE_SECTIONS`.** Removes reliance
   on each driver passing `skip_kinds`. (attune-author release.)
4. **FM1 — failure-modes sourcing review.** Decide whether
   `## Failure modes` is author-owned or partly sourced (like FAQ)
   before authoring it at scale.
5. **(Optional) P3 — `maintenance: projected`.** If adopted, DD5
   changes from "remove the feature" to "mark the 10 kinds projected,"
   keeping faq on the LLM path and ending the freeze.

Items 1–3 are small, high-leverage, and pay off on every one of the
~270 features. Do them before the loop, not during it.

---

## Effort shape

Per feature, the cost is **authoring the master file** (a careful
merge + grounding pass — the slow part) plus a fast deterministic
projection and a scripted verify. The projector, fact-check, serve
check, and DD5 step are seconds each. Budget the human time on
authoring + grounding; the chain itself is cheap and repeatable.
