# R7 — Rollout Playbook: Single-Source Help + Docs

**Status:** drafted from the pilot (2026-06-21) · **Builds on:**
[design.md](design.md), [decisions.md](decisions.md) (D6–D10),
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
   Writes 13 outputs (10 `.help` + how-to/architecture/reference docs).
   `faq` and `tutorial` are skipped by the driver's `skip_kinds`.

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

5. **Verify serve** through the **real** consumer (see "Verification"
   below) — all 10 projected kinds serve with non-empty bodies and the
   feature reports complete (faq retained).

6. **Verify mkdocs:** `mkdocs build`. Add `!architecture/<F>.md` to
   `mkdocs.yml`'s `exclude_docs` whitelist so the architecture page
   publishes (see P4 — until the convention is generalized).

7. **Apply DD5 (only after serve verified):** remove the `<F>` entry
   from `.help/features.yaml` so the weekly help-freshness regen never
   runs `attune-author generate <F> --all-kinds` and overwrites the
   projected content. Leave a comment in place (see the spec-engine /
   models entries for the template). The retained `faq.md` stays on
   disk, served, frozen.

---

## Verification recipe (copy-paste)

The live consumer of the feature-dir `.help/templates/<F>/` layout is
`attune.ops.help_data` (the ops living-docs dashboard) — **not**
`attune_help.HelpEngine(template_dir=...)`. The t2 check named the
latter, but the HelpEngine override path needs a `cross_links.json` and
uses a kind-pluralized layout, so it falls back to bundled templates
and silently misses the feature dir. Verify against the real consumer:

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

Use the **main** venv's python + `PYTHONPATH=<worktree>/src` (the
worktree venv lacks the `[ops]` extras; the editable-install MAPPING
otherwise points `attune` at the main checkout — see CLAUDE.md).

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
- **mkdocs nav wiring is not automatic (P4).** Architecture pages are
  excluded wholesale; how-to/tutorial/reference pages build but are
  "not in nav." The pilot re-includes architecture per feature — this
  does not scale. Resolve the convention (P4) before bulk rollout.
- **Worktree traps.** `project_features.py` resolves the repo root from
  its own path, so it writes to the worktree correctly — but any
  verification that imports `attune` needs `PYTHONPATH=<worktree>/src`
  or it runs the main checkout's code against the main checkout's
  `.help`.

---

## Prerequisites / sequencing before bulk rollout

Resolve these first so the per-feature loop is mechanical:

1. **P4 — nav-wiring convention.** Otherwise every feature needs a
   manual `mkdocs.yml` edit and its pages stay out of the menu.
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
