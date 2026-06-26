# Doc-Import Gate — the FINAL guard against doc fiction

**Created:** 2026-06-26
**Source:** the recurring doc-fiction cleanups
(`doc-fiction-cleanup`, `orchestration-doc-fiction-cleanup`,
`empathy-doc-fiction-cleanup`) — each removed docs that still imported
a symbol deleted in an earlier PR. This gate stops the recurrence.

---

## What it does

`scripts/audit_doc_imports.py` extracts every `from attune… import …` /
`import attune…` line from `python` code fences in the published docs and
verifies each resolves against the installed package (import-only,
in-process — fence bodies are never executed). It runs as the
`doc-import-audit` job in `.github/workflows/docs.yml`.

A reader who copies a doc fence should never hit `ImportError`. Before
this gate, that guarantee was enforced reactively (a cleanup spec months
after the breakage); now it is enforced per-PR.

---

## Scope — published surfaces only

- **Checks:** `content/features/**`, `content/blog/**`, and the
  **served** `docs/` pages. A `docs/` page is "served" if it is in the
  mkdocs `nav` OR not matched by `exclude_docs` (nav wins the occasional
  nav-vs-`exclude_docs` conflict, e.g. `hooks.md`). Read from `mkdocs.yml`
  via `pathspec` (mkdocs's own matcher); falls back to the coarse
  substring excludes if `mkdocs.yml`/`pathspec` is unavailable.
- **Why scoped:** orphaned/internal docs (`docs/pitch/`,
  `docs/blog/social/`, archived/excluded pages) are not served to
  readers, so a stale import there is not a reader-facing bug. Policing
  them is noise. `content/blog` IS the website source (the Next.js site
  reads `content/blog`, NOT `docs/blog`), so it is always checked.
- **Always excluded:** `docs/specs/**` and any `**/archive/**` (history
  legitimately names removed symbols), and generated bundles
  (`plugin/help/generated/**` — fix those at their source).
- **Only `attune` imports** are verified. Stdlib/third-party imports are
  ignored — we only guarantee our own symbols resolve.
- **Import resolution only.** It does NOT check `obj.method()` accuracy
  or run code. That deeper layer is intentionally out of scope (high
  false-positive risk for low marginal signal).
- **Fast:** ~0.9s for ~440 imports across ~380 fences (importlib caches
  modules), well under the job's 8-minute budget.

---

## The escape hatch

Some fences intentionally show removed/old code — a migration "before:"
block, a "this no longer works" example. Mark the fence to skip it:

```markdown
<!-- doc-import-skip: shows the pre-9.0.0 API, removed in #1073 -->
```python
from attune import EmpathyOS  # historical — no longer importable
```
```

The marker must sit within 3 lines above the fence opener (blank lines
allowed) and the **reason is required** (it is reported in the audit
output). Use it sparingly — a skip is a promise the prose makes clear
the code is historical.

---

## Running it

```bash
python scripts/audit_doc_imports.py                # human report
python scripts/audit_doc_imports.py --format json  # CI-shaped
python scripts/audit_doc_imports.py --paths docs/reference  # a subset
```

Exit `0` when every in-scope `attune` import resolves (or is skipped with
a reason); exit `1` on any unresolved import. Needs `attune` importable
(the script adds in-repo `src/` to `sys.path`; CI installs the package).

---

## Advisory → required (promotion path)

The gate ships **advisory** — it runs on every docs/content/src PR and
reports, but is NOT in `required_status_checks` yet, because adoption
surfaced a pre-existing backlog. After scoping to served surfaces the
backlog is **11 findings** across three published docs —
`reference/TROUBLESHOOTING.md` (the old `attune_llm` package name),
`hooks.md` (`HookMatcher` not re-exported), and `EXCEPTION_HANDLING_GUIDE.md`
(illustrative exceptions falsely attributed to `attune.exceptions`) —
cleared by the backlog PR. (The other ~10 original findings were in
orphaned/excluded docs and are now out of scope.)

**Promote to required once `python scripts/audit_doc_imports.py` is
clean on main** — same play as `wiring-audit` (advisory until a green
streak, then added to branch protection). Do NOT promote while it is red.

---

## When you remove a symbol from `src/`

This gate fires on `src/**` changes too, so removing a public symbol will
flag every doc that imported it — fix the docs in the SAME PR (or add a
`doc-import-skip` with a reason if the doc is deliberately historical).
That is the whole point: the docs trailing edge no longer drifts.

---

## Cross-references

- `.claude/rules/attune/website-content-accuracy.md` — the website
  counterpart (verify counts/claims against live code).
- `scripts/audit_docs_wiring.py` — the sibling anchor/link gate (catches
  cross-file `#anchor` breaks that `mkdocs --strict` misses).
- `docs/specs/orchestration-doc-fiction-cleanup/`,
  `docs/specs/empathy-doc-fiction-cleanup/` — the cleanups that motivated
  this gate.
