# Doc-Fiction Triage — pre-flight checklist before a doc cleanup

**Created:** 2026-06-26
**Source:** the orchestration / empathy doc-fiction cleanups. Three
traps recurred — scope undercount, "dead" claims that were actually
LIVE symbols at a different path, and policing orphaned docs — each
costing rework or shipping a wrong claim to a committed spec. This is
the checklist that prevents them.

Run this BEFORE deleting/rewriting any doc that references a "removed"
symbol. It is the human/agent counterpart to the CI
[doc-import-gate](./doc-import-gate.md) and pairs with
[removing-dead-code](./removing-dead-code.md) (the delete-vs-rewrite
decision once a symbol is confirmed dead).

---

## 1. Inventory with the FULL property, not one symbol

The single biggest scope error: grepping for ONE name
(`import EmpathyOS`) when the real surface is a SET. You will undercount
and re-discover the rest mid-execution.

- Build the complete dead-symbol set first (every removed class, every
  removed alias, the old package name).
- Inventory with `git grep -lnE '<full|set|here>' -- docs/ content/
  plugin/help/` and treat THAT file list as the scope.
- Re-grep the full set after each batch (stray copies hide in
  `examples/` vs `tutorials/examples/`, JSON blobs, ASCII diagrams,
  and line-wrapped identifiers a single-line grep misses).

## 2. NEVER label a symbol "dead" without locating it in `src/`

Deadness is a CODE fact — verify it, never infer it from a related
framework's removal or a shared name. The same trap hit
`target_level` (a live param read as fiction), `HookMatcher` (real,
just not re-exported), and `EmpathyLLMExecutor` (alive at
`attune.models.empathy_executor`, wrongly called dead in a committed
spec — see empathy-doc-fiction-cleanup D7).

For each symbol the docs reference, classify it:

```bash
grep -rnE "class <Sym>\b|def <Sym>\b|^<Sym> ?=" src/        # defined?
git log --oneline -S "class <Sym>" -- src/                  # ever real?
```
```python
import importlib, inspect
# probe likely module paths AND submodules, not just the top level:
for m in ["attune", "attune.x", "attune.x.submodule"]:
    mod = importlib.import_module(m); print(m, hasattr(mod, "<Sym>"))
inspect.signature(Cls.__init__)   # is the "dead" kwarg actually a live param?
```

Then bucket — only **(c)** is a delete:

| Bucket | Tell | Fix |
|--------|------|-----|
| (a) wrong import path / not re-exported | imports from a SUBMODULE but not the package | repoint the import (one line) |
| (b) old package name | `attune_llm` → `attune.llm` (pre-rename) | repoint |
| (c) genuinely removed | `git log -S` shows it deleted, no successor | delete fence + prose (per removing-dead-code) |
| (d) live param / live class read as fiction | `inspect.signature` / `hasattr` says alive | KEEP — do not touch |

A no-API-key `ValueError` or a missing-dep `ImportError` is a runtime
gate, NOT a dead symbol. A construct that gets past the signature is
alive.

## 3. Verify the REPLACEMENT before writing it

Every "after" fence must import against the live code
(`PYTHONPATH=src python -c "<imports>"` → exit 0) BEFORE it ships.
Construct the canonical example once, verify it, then reuse it. Don't
fake a removed API's shape onto its successor (e.g. AgentTeam is
fan-out+gate ONLY — no `strategy=`/`build_from_*`).

## 4. Scope to PUBLISHED surfaces

A stale import in an orphaned/unserved doc is not a reader-facing bug.
Don't burn effort polishing it; don't let it block.

- Served = in mkdocs `nav` OR not in `exclude_docs` (the two conflict;
  nav wins — see doc-import-gate.md).
- `content/blog` is the website source (the Next.js site reads
  `content/blog`, NOT `docs/blog`). `docs/blog/social/*` is an
  unpublished orphan.
- `docs/specs/**`, archives, and generated bundles are append-only /
  built artifacts — never the cleanup target.

## 5. Delegate wide, but CENTRALLY verify — never trust self-reports

Parallel subagents are fine for per-file rewrites, but a subagent
reporting "grep 0, fences verified" is necessary-not-sufficient
("registered ≠ working"). After the fan-out, re-run the WHOLE
acceptance set yourself:

- `git grep` the full dead set → zero outside history.
- Extract every `attune` import from every touched fence → all resolve.
- Surviving-symbol counts did not DROP (section surgery can silently
  delete live content — the audit's whole point).
- `mkdocs build --strict` green; `audit_docs_wiring.py` 0 findings
  (catches cross-file anchor breaks from deletions);
  `audit_doc_imports.py` 0 on served surfaces.

## 6. Record decisions truthfully — and audit them

A "dead" claim in a `decisions.md` is load-bearing: it spawns follow-up
work and is cited later. If you write one, it must pass §2 first. When
a prior decision is found wrong, CORRECT it in place with a dated note
(don't silently rewrite, don't leave it) — see empathy D7.

---

## Cross-references

- [removing-dead-code.md](./removing-dead-code.md) — the
  delete-vs-rewrite / should-it-exist gate (after §2 confirms dead).
- [doc-import-gate.md](./doc-import-gate.md) — the CI enforcement of §3.
- [website-content-accuracy.md](../../rules/attune/website-content-accuracy.md) — verify
  counts/claims against live code (the website counterpart).
