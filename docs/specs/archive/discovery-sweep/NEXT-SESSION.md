# Starter Prompt — Discovery Sweep Follow-On

**For the next session.** Copy the prompt block below verbatim.

---

## Context (read first)

- Phase 1 of `discovery-sweep` merged to `main` as
  [PR #303](https://github.com/Smart-AI-Memory/attune-ai/pull/303)
  on 2026-05-13.
- Phase 1 polish is in flight as draft
  [PR #306](https://github.com/Smart-AI-Memory/attune-ai/pull/306)
  on branch `fix/discovery-sweep-false-positives`. Quick same-line
  quoted-region + `# noqa: BLE001` filters + single-file path
  rendering fix. Awaiting CI when this session paused; check
  `gh pr checks 306` before deciding next move.
- Whole-tree dogfood audit completed and recorded at
  [docs/specs/discovery-sweep/dogfood-audit-2026-05-13.md](docs/specs/discovery-sweep/dogfood-audit-2026-05-13.md).
- Spec: [docs/specs/discovery-sweep/](docs/specs/discovery-sweep/).
- Plan: [.claude/plans/discovery-sweep.md](.claude/plans/discovery-sweep.md).

## What's still open

The whole-tree audit found one real signal and 14 false positives
of a class PR #306's filter doesn't catch: pattern keywords
mentioned in **multi-line module docstrings** (the line containing
`eval(` / `exec(` is just prose, the opening `"""` is many lines
above, so the line-local quote walk falls through).

**Decided (Patrick, 2026-05-13): AST-based string-region map.**
Three options were enumerated in the audit doc (§ Three fix
options); Patrick approved Option 1 inline. Implementation: parse
each `.py` file with `ast.parse`, walk string nodes, build set of
`(line, col)` ranges inside any string region, filter findings
against that set. Robust against multi-line strings, f-strings,
raw/b-strings. Stdlib `ast`, no new deps. Do not re-evaluate the
other two options.

The one real signal: `src/attune/ops/routes/specs.py:274` — cleanup
broad-except missing the project-required `# noqa: BLE001` +
`# INTENTIONAL: cleanup` annotation. Either annotate or narrow the
except. Two-line fix.

## Suggested next-session prompt

```
Resume discovery-sweep work. Read these first:
- docs/specs/discovery-sweep/NEXT-SESSION.md
- docs/specs/discovery-sweep/dogfood-audit-2026-05-13.md

State check before doing anything:
1. `gh pr view 306 --json state,mergedAt` — is the false-positive
   filter PR merged yet? If MERGED, work from main; if OPEN, check
   CI (`gh pr checks 306`) and consider merging via the temp-
   remove-reviews dance before starting new work.
2. `git fetch origin && git log --oneline origin/main -5` — confirm
   we're synced.

Two pieces of work, do them in this order:

(A) Fix the one real signal from the audit. Add
    `# noqa: BLE001  # INTENTIONAL: cleanup` to
    src/attune/ops/routes/specs.py:274 (or narrow to specific
    excepts — your call). One commit, small PR, fold the audit
    doc into the PR body.

(B) Ship the AST-based string-region filter for PatternScanSource.
    Approved approach (don't re-evaluate alternatives): new module-
    private helper in
    src/attune/workflows/discovery_sweep/sources/pattern_scan.py
    that uses `ast.parse` to walk Constant/Str nodes and build a
    set of (line, col)-range tuples representing string regions
    per file. Filter findings whose (line, col) falls inside any
    region. Keep the existing line-local _is_inside_quoted_region
    as a fast-path fallback for files that fail to parse (SyntaxError
    or otherwise — never let a malformed file crash the scan).
    Add a test fixture with a known multi-line docstring and assert
    zero queue findings on it. Then re-run the whole-tree sweep and
    assert queue drops to 1 (just the real signal from (A) — or 0
    if (A) already merged).

Phase 2A (LLM source adapters) is still NOT started — don't drift
into it. The DECIDE callouts for Phase 2A are in
docs/specs/discovery-sweep/decisions.md, still open.

Spec rule: skip the spec-first interview, this is two narrowly-
scoped fixes to a shipped feature, not new feature work.
```

## Side-effects to be aware of

- Branch `fix/discovery-sweep-false-positives` is local + remote
  (PR #306). Don't delete it; merge it.
- Pre-existing dirty tree in main checkout (memdocs_storage/, a
  few `docs/specs/*` entries) is unrelated leftover state — don't
  fold it into either PR.
- The `Vercel – attune-ai` CI check fails on every PR (legacy
  preview, documented in lessons). `Run Security Scanner: cancel`
  is also expected — both ignored when admin-merging.
- This repo allows squash merges only; require-reviews dance is
  documented in CLAUDE.md lessons.

## Status of session-end work

- [x] PR #303 merged
- [x] PR #306 opened (draft)
- [x] Dogfood audit run + written up
- [x] Starter prompt written
- [x] PR #306 CI green
- [x] PR #306 merged
- [x] Real-signal fix (`specs.py:274`) — PR #307 merged 2026-05-13
- [x] AST string-region filter — PR #309 merged 2026-05-13
- [x] Whole-tree dogfood re-verified: queue = 0 on `src/attune`
