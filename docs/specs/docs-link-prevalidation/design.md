# Design — Docs Link Prevalidation

**Status:** complete (Phase 4 shipped 2026-06-05; warn mode)
**Phase 1:** [requirements.md](./requirements.md) — locked 2026-06-02 (merged via #566)

Translates Phase 1's locked decisions into the concrete audit-block
parser, the override comment format, the pre-commit hook config,
and the CI job YAML. No new user-facing decisions; this file is
the implementation contract for Phase 4.

---

## Phase 1 recap (resolved)

| DECIDE | Resolution | Where it lands here |
|---|---|---|
| D1 (block vs warn) | Warn for one release cycle | Hook exits 0 with annotation on findings; promote to exit-non-zero after evidence |
| D2 (override mechanism) | Inline HTML comment | See "Override format" below |
| D3 (hook vs CI) | Both | See "Pre-commit hook YAML" + "CI job YAML" below |

Plus the locked-mechanism choice from the spec body:

- **Primary:** audit-block reader (consumer-side) — pre-commit hook
- **Safety net:** mkdocs `--strict` CI pre-flight job
- **Generate-time wrapper:** deferred (revisit if (1)+(2) prove insufficient)

---

## Files touched

| Phase 4 file | Purpose |
|---|---|
| `scripts/check_doc_audit_blocks.py` | stdlib-only audit-block reader |
| `tests/unit/scripts/test_check_doc_audit_blocks.py` | regression-guard tests for the reader |
| `.pre-commit-config.yaml` | new local hook on `docs/**/*.md` glob |
| `.github/workflows/build.yml` (or new `docs-strict.yml`) | mkdocs `--strict` pre-flight job |

No new top-level directories. No new packages.

---

## Audit-block parser

### Block recognition

attune-author writes the audit block as a Markdown heading
followed by a table. Recognition regex:

```python
_AUDIT_HEADING = re.compile(
    r"^##\s+Unresolved\s+references\s*$",
    re.IGNORECASE | re.MULTILINE,
)
```

The block extends from the heading to the next `^## ` heading or
EOF. Same pattern as the `_CHECKLIST_HEADING` extraction in
`spec-status-self-truthing` — consistent with the project's regex
conventions.

### Row parser

Audit rows look like:

```
| Line 96 | error | `[Release Prep concept overview](../concepts/tool-release-prep.md)` — target does not exist |
```

Row regex (within the extracted block):

```python
_AUDIT_ROW = re.compile(
    r"^\|\s*Line\s+(\d+)\s*\|\s*(error|warning|info)\s*\|"
    r"\s*`?(.*?)`?\s*(?:—\s*(.*?))?\s*\|",
    re.IGNORECASE | re.MULTILINE,
)
```

Captures: `(line_number, severity, issue_text, description)`.

### Broken-link classification

A row is a "broken link" when:

- severity == `error`
- AND (issue contains `target does not exist`
       OR issue contains `not found among documentation files`)

Anything else (broken imports, undefined names in code fences,
type-check errors) is OUT OF SCOPE for v1 — these are different
hallucination shapes. The reader still parses them but reports
only the broken-link rows.

### Pseudocode

```python
def find_broken_links(text: str) -> list[BrokenLink]:
    heading = _AUDIT_HEADING.search(text)
    if heading is None:
        return []
    next_h2 = _NEXT_H2.search(text, heading.end())
    end = next_h2.start() if next_h2 else len(text)
    block = text[heading.end():end]

    results = []
    for row in _AUDIT_ROW.finditer(block):
        line_no, severity, issue, _ = row.group(1, 2, 3, 4)
        if severity.lower() != "error":
            continue
        if "target does not exist" not in issue.lower() \
                and "not found among documentation files" not in issue.lower():
            continue
        results.append(BrokenLink(
            line=int(line_no),
            issue=issue.strip(),
        ))
    return results
```

---

## Override format

Per DECIDE-2, an inline HTML comment near the audit block (or
anywhere in the file) skips that file's check entirely:

```html
<!-- attune-skip-link-check: <reason> -->
```

The reason is required (non-empty after trim). Recognition regex:

```python
_OVERRIDE = re.compile(
    r"<!--\s*attune-skip-link-check\s*:\s*(.+?)\s*-->",
    re.IGNORECASE | re.DOTALL,
)
```

If a file has a match with non-empty reason, the reader emits an
INFO-level note ("skipped per override: <reason>") and otherwise
reports no findings for that file.

### Override scope choice

**File-level only for v1.** A row-level override (skip a single
broken link in a file while still checking the rest) adds
parser complexity for minimal benefit at the current usage
scale. Promote to row-level if evidence shows it's needed.

---

## Pre-commit hook config

```yaml
# .pre-commit-config.yaml (append to existing hooks list)
  - repo: local
    hooks:
      - id: check-doc-audit-blocks
        name: Check docs/**/*.md for unresolved audit-block findings
        entry: python scripts/check_doc_audit_blocks.py
        language: system
        files: ^docs/.*\.md$
        pass_filenames: true
        # v1: warn-mode (exits 0 with annotated output)
        # Promote to default-block by removing this in v2:
        verbose: true
```

The script reads each passed filename, runs the reader, prints any
findings to stdout (so they show up in the pre-commit output),
and exits 0 in v1 (warn mode per D1).

### Hook output format (warn mode)

```
docs/how-to/release-prep.md:
  Line 96: error — `[Release Prep concept overview](../concepts/tool-release-prep.md)` — target does not exist
  Line 97: error — `[Release Prep quickstart](../quickstarts/skill-release-prep.md)` — target does not exist
  Suggested fixes:
    - Remove the bullet/sentence containing the bad link
    - Replace with a working link if one exists
    - Add `<!-- attune-skip-link-check: <reason> -->` to override
```

Quiet on files with no findings.

---

## CI job YAML

A new step in the existing `build` workflow (or a standalone
`docs-strict.yml`) runs `mkdocs build --strict`. Cheap (~15s) and
fails fast on a broken link mkdocs catches that the pre-commit
hook didn't (e.g., contributor without local hooks).

```yaml
# .github/workflows/build.yml (existing job, add a step)
      - name: mkdocs strict pre-flight
        run: |
          uv run mkdocs build --strict 2>&1 | tee mkdocs-strict.log
        # v1: keep this as a separate fast step; if it fails, the
        # full job fails the same as before — no behavior change
        # for users, just earlier feedback
```

If a standalone workflow is preferred (for clarity):

```yaml
# .github/workflows/docs-strict.yml
name: Docs strict build
on:
  pull_request:
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
      - '.help/**'

jobs:
  docs-strict:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra docs
      - run: uv run mkdocs build --strict
```

**Pick the standalone workflow path** — it's path-filtered so
docs-only PRs run only this (cheap), and code-only PRs skip it
entirely. The existing `build` job currently does mkdocs work
elsewhere too; clean separation simplifies the CI graph.

---

## Promotion path (warn → block)

Per D1, v1 ships warn-mode for one release cycle. Promotion to
block-mode is mechanical:

1. Add `exit(1)` after the broken-link print loop in
   `check_doc_audit_blocks.py` when findings exist.
2. Update the spec's `decisions.md` with the date and observed
   false-positive rate from the warn-mode period.

No spec-level re-approval needed for the promotion (D1 already
ratified the path).

---

## Performance budget

- Pre-commit hook: O(N files × M lines per file) — single regex
  scan per file. ~50ms for the full `docs/` tree.
- CI mkdocs job: ~15s build time, runs only on `docs/` PRs per
  path filter.
- No new runtime dependencies.

---

## Rollback strategy

- Remove the pre-commit hook block from `.pre-commit-config.yaml`
- Remove the `docs-strict.yml` workflow file
- Delete `scripts/check_doc_audit_blocks.py` and its test

No persisted state, no migration. Existing mkdocs builds keep
working unchanged.

---

## Testing strategy

Unit tests in `tests/unit/scripts/test_check_doc_audit_blocks.py`:

1. **Empty file** → no findings, no error
2. **File with audit block, no broken-link rows** → no findings
3. **File with one broken-link row** → 1 finding with correct
   line number
4. **File with multiple broken-link rows AND non-link rows
   (broken imports, etc.)** → only the broken-link rows reported
5. **Malformed audit table (corrupt row syntax)** → graceful
   fallback, no exception
6. **File with `<!-- attune-skip-link-check: reason -->`** → no
   findings (override engaged)
7. **File with override but no reason** → override NOT engaged
   (rejected as malformed)
8. **Fixture file:** `docs/architecture/deep-review.md` from
   PR #564 — currently has a broken link in its audit block —
   asserts the reader catches it correctly (regression guard
   against silent break)

Integration test via pre-commit:

- Run `pre-commit run check-doc-audit-blocks --all-files` and
  assert output matches expected format.

---

## Phase 3: Tasks — *(not started; will be authored after this design's approval)*

---

## Phase 4 — Implementation (complete, 2026-06-05)

Shipped:
- `scripts/check_doc_audit_blocks.py` — stdlib audit-block reader
  (warn mode, exit 0 per D1). Parser refined vs the design example:
  the Location cell can carry a suffix (`Line 7 (code fence)`), so the
  row regex allows non-pipe text after the digits. Verified against the
  real `docs/how-to/release-prep.md` block — flags the 2 broken links
  ("target does not exist"), ignores the broken import
  ("module not importable", out of scope).
- `tests/unit/scripts/test_check_doc_audit_blocks.py` — 11 tests.
- `.pre-commit-config.yaml` — `check-doc-audit-blocks` local hook on
  `^docs/.*\.md$`, verbose, warn mode.

**Deviation from the design's CI section (premise-check):** the design
proposed a standalone `docs-strict.yml` running `mkdocs build --strict`.
But `.github/workflows/docs.yml` **already** runs `mkdocs build --strict`
on PRs path-filtered to `docs/**`/`mkdocs.yml`/`src/**` — the safety net
exists. Creating `docs-strict.yml` would duplicate it. Instead, added
`.help/**` to `docs.yml`'s PR path filter so regen PRs also hit the
strict pre-flight (the one gap vs the design's intended filter). No new
workflow.

**Promotion path (warn -> block) unchanged:** add `return 1` in the
script when findings exist, after a warn-mode release cycle (D1).
