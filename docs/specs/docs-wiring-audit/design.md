# Design: Documentation Wiring Audit
**Status:** shipped (2026-07-20, closed per q-briefing-triage-002 A1; approved 2026-05-31)
**Phase:** 2 — Design
**Predecessor:** [requirements.md](./requirements.md) (Phase 1
approved 2026-05-31, see [decisions.md](./decisions.md))
**Successor:** [tasks.md](./tasks.md) (Phase 3, authored; Phase 4
shipped)

---

## Phase 2: Design

### Approach

Five artifacts, each with a clear ship/no-ship gate, designed so
v1 ships incrementally rather than as a big-bang. The first three
artifacts (audit script, two cheap checks, allowlist) land
together as the minimum-viable wiring gate. The remaining two
(mkdocstrings, advisory See-Also) land in follow-up PRs since
they have more design surface area and aren't blockers for the
release-prep release.

1. **`scripts/audit_docs_wiring.py`** — single CLI entry point;
   subcommands per check; structured output (JSON for CI, markdown
   for humans).
2. **`.audit/orphans.yml`** — subtree-level allowlist file; the
   single source of "this is intentionally orphan."
3. **Three cheap checks** — anchor integrity, nav ↔ filesystem,
   `features.yaml` ↔ filesystem. Each ~50-100 LOC. Ship together
   in v1.
4. **mkdocstrings symbol resolution check** — needs Python import
   logic; ships in v1.1 to keep v1's scope tight.
5. **Reciprocal See-Also advisory check** — opinionated, low
   urgency; ships in v1.2 or deferred.

CI integration lands with v1 as a separate commit so the cheap
checks gate PRs from day one.

---

### Artifact 1 — `scripts/audit_docs_wiring.py`

**CLI shape:**

```bash
# Run all checks, exit non-zero on any failure
python scripts/audit_docs_wiring.py

# Run a specific check
python scripts/audit_docs_wiring.py --check anchor
python scripts/audit_docs_wiring.py --check nav
python scripts/audit_docs_wiring.py --check features-yaml
python scripts/audit_docs_wiring.py --check mkdocstrings  # v1.1
python scripts/audit_docs_wiring.py --check see-also      # v1.2; advisory only

# Output format
python scripts/audit_docs_wiring.py --format json    # default in CI
python scripts/audit_docs_wiring.py --format markdown  # default for humans

# Suppress findings covered by allowlist (default: on)
python scripts/audit_docs_wiring.py --no-allowlist  # surface everything for review
```

**Module layout:**

```text
scripts/audit_docs_wiring.py     # CLI entry; argument parsing; dispatch
scripts/audit_docs_wiring/
  __init__.py                    # __version__, public API
  cli.py                         # argparse wiring, output routing
  allowlist.py                   # load .audit/orphans.yml + match logic
  checks/
    __init__.py
    anchor.py                    # Artifact 3a — anchor integrity
    nav.py                       # Artifact 3b — nav ↔ filesystem
    features_yaml.py             # Artifact 3c — features.yaml ↔ fs
    mkdocstrings.py              # Artifact 4 — symbol resolution (v1.1)
    see_also.py                  # Artifact 5 — reciprocal links (v1.2)
  report.py                      # markdown + json formatters
```

**Why a `scripts/audit_docs_wiring/` package, not a single file?**
Each check has its own data structures, helpers, and tests. Keeping
them in one 800-line `.py` makes the file painful to maintain.
Package layout also means each check can be developed/tested
independently — important for the v1 / v1.1 / v1.2 staging.

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | All requested checks passed (zero findings after allowlist) |
| 1 | One or more findings remain after allowlist (CI fails) |
| 2 | Bad invocation (unknown check name, malformed allowlist, etc.) |

**Output contract:**

```python
# Each check returns a list of Finding dataclasses
@dataclass(frozen=True)
class Finding:
    check: str           # "anchor" | "nav" | "features-yaml" | ...
    severity: str        # "error" | "warning" | "info" | "advisory"
    file: str            # Path relative to repo root
    line: int | None     # 1-indexed, or None if file-level
    message: str         # Human-readable description
    fix: str | None      # One-line suggested fix
```

JSON output is `{"findings": [Finding.asdict(), ...]}`; markdown
output groups findings by check and renders each as a table row.

---

### Artifact 2 — `.audit/orphans.yml`

**Schema:**

```yaml
# Subtree-level allowlist for orphan / wiring checks.
# Per docs-wiring-audit/decisions.md Q2: subtree-level entries
# only (no per-file allowlisting).
#
# Format: list of paths relative to repo root. Trailing slash =
# directory (recursive). Exact match for top-level files.
#
# Each entry MUST have a "# reason:" comment on the line above.

orphan_subtrees:
  # reason: blog posts are dated artefacts; covered by
  # docs-completeness-audit's date-cutoff policy
  - docs/blog/

  # reason: top-level BLOG_*.md files have the same disposition
  # as docs/blog/; pattern match by glob
  - docs/BLOG_*.md

  # reason: archived docs are historical; not in nav by design
  - docs/archive/

  # reason: examples are reference snippets, intentionally not in nav
  - docs/examples/

  # reason: pitch deck assets, separate from product docs
  - docs/pitch/

  # reason: every spec dir has its own internal structure;
  # nav lists specs at the level above (index pages)
  - docs/specs/

  # reason: implementation notes for spec executors, not user docs
  - docs/implementation/

  # reason: cost-analysis is for maintainers, not end users
  - docs/cost-analysis/

  # reason: conversation captures; archival
  - docs/conversations/
```

**Why YAML, not JSON or TOML?**
YAML supports the per-entry comment convention without ceremony.
The audit script only needs to read the file, not write it.
Comments are the documentation; rejecting an entry without a
reason comment is a hard policy enforced by the loader.

**Loader contract:**

```python
# scripts/audit_docs_wiring/allowlist.py
@dataclass(frozen=True)
class Allowlist:
    orphan_subtrees: tuple[str, ...]  # normalised paths

    def is_orphan_exempt(self, path: str) -> bool:
        """True if `path` is under any allowlisted subtree."""
        ...

def load_allowlist(path: Path = Path(".audit/orphans.yml")) -> Allowlist:
    """Load + validate the orphan allowlist. Raises if any entry
    lacks a `# reason:` comment on the preceding line."""
    ...
```

**The reason-comment enforcement** matters: without it, the file
becomes a junk drawer of "we'll figure it out later" exemptions.

---

### Artifact 3 — Three cheap checks

#### 3a. Anchor integrity (`checks/anchor.py`)

**What it does:** for every internal markdown link of the form
`[text](file.md#anchor)`:

1. Resolve `file.md` to an absolute repo path.
2. Parse the target file's markdown headings.
3. Slugify each heading using the same algorithm mkdocs uses (PyMdown
   extensions' `toc.slugify`).
4. Assert the link's `#anchor` matches a slugified heading.

**Why slugify?** Markdown headings get auto-slugified for HTML
anchors. `## My Section` becomes `#my-section`. Authors write
links against the slug, not the original heading text. The audit
must use the same slugifier mkdocs does, else false negatives.

**Edge cases handled:**

- Intra-page anchors (`[text](#anchor)` with no file part) — check
  against the *current* file's headings.
- External links (`http://`, `https://`, `mailto:`) — skipped.
- Cross-repo anchors (e.g. `https://github.com/.../file.md#anchor`)
  — skipped in v1; flagged as v2 work in the design doc.
- Reference-style links (`[text][ref]` ... `[ref]: file.md#anchor`)
  — resolve the reference, then check normally.

**v1 scope:** intra-`docs/` links only. Links from `README.md`,
`CHANGELOG.md`, `CLAUDE.md`, etc. checked in v1.1.

**Output:**

```text
Finding(
  check="anchor",
  severity="error",
  file="docs/reference/API_REFERENCE.md",
  line=42,
  message="Link target '#chainexecutor' not found in docs/reference/API_REFERENCE.md (headings: 'overview', 'getting-started', 'workflows')",
  fix="Update link to match an existing heading, or rename the heading and update inbound links per decisions.md Q1",
)
```

#### 3b. Nav ↔ filesystem (`checks/nav.py`)

**What it does:**

1. Parse `mkdocs.yml`'s `nav:` section.
2. Walk every nav entry, collecting referenced file paths.
3. For each referenced path: assert the file exists on disk.
4. Walk `docs/**/*.md`; for each file: assert it is either in nav
   OR under an allowlisted orphan subtree.

**Two failure shapes:**

- **Dangling nav entry:** `mkdocs.yml` references `docs/old.md` but
  the file was deleted. Severity: `error`.
- **Unlisted doc:** `docs/new.md` exists but isn't in nav and
  isn't allowlisted. Severity: `error`.

**The orphan-subtree allowlist** (Artifact 2) exempts subtrees
listed in `.audit/orphans.yml` from the "unlisted doc" check. A
file under `docs/blog/` doesn't need to be in nav to pass.

**Output:**

```text
# Dangling nav entry
Finding(check="nav", severity="error", file="mkdocs.yml", line=147,
  message="nav references docs/old.md but file does not exist",
  fix="Remove the nav entry or restore the file")

# Unlisted doc (not allowlisted)
Finding(check="nav", severity="error", file="docs/new.md", line=None,
  message="File exists in docs/ but is not in nav and not in .audit/orphans.yml",
  fix="Add to nav in mkdocs.yml, or add the containing subtree to .audit/orphans.yml with a reason comment")
```

#### 3c. `features.yaml` ↔ filesystem (`checks/features_yaml.py`)

**What it does:**

1. Load `.help/features.yaml`.
2. For every `doc_paths` entry across every feature: assert the
   file exists on disk.
3. **Advisory check (warning, not error):** for every `docs/` file
   matching a known feature-doc pattern (`docs/reference/<name>.md`,
   `docs/how-to/<name>.md`), check if that feature has any
   `doc_paths` entry pointing at it. Surface mismatches as
   `severity="warning"` — surface but don't fail the build.

**Why advisory on the inverse direction?** features.yaml is
maintained by hand; "this doc should be tracked" is a judgement
call. The check is informational so authors notice the gap, not a
gate that blocks PRs.

**Output:**

```text
# Dangling doc_paths
Finding(check="features-yaml", severity="error",
  file=".help/features.yaml", line=88,
  message="Feature 'bug-predict' doc_paths references docs/reference/bug-predict.md but file does not exist",
  fix="Update doc_paths or restore/rename the file")

# Advisory: unlinked doc that looks like a feature doc
Finding(check="features-yaml", severity="warning",
  file="docs/reference/new-feature.md", line=None,
  message="Looks like a feature reference doc but no features.yaml entry points at it",
  fix="Add to .help/features.yaml's doc_paths if this is a tracked feature; ignore if it's something else")
```

---

### Artifact 4 — mkdocstrings symbol resolution (v1.1)

**Why ship in v1.1, not v1?** Requires importing Python at audit
time (slow, can fail due to dependency-injection issues, requires
careful PYTHONPATH setup in CI). The three cheap checks ship first
to get the gate established; mkdocstrings adds in follow-up.

**What it does:**

1. `grep -rn '^:::' docs/` — find every mkdocstrings directive
   anywhere in `docs/` (per decisions.md Q3 — whole-tree sweep).
2. Parse each `:::` line for the symbol path (e.g.
   `::: attune.coordination.ConflictResolver`).
3. Try to resolve each symbol via `importlib.import_module` +
   `getattr` chain.
4. Unresolved symbols → `severity="error"`.

**Subprocess isolation:** run the symbol resolution in a fresh
subprocess so import failures don't crash the audit. Use
`subprocess.run([sys.executable, "-c", "import attune.X; getattr(attune.X, 'Y')"])`
and check exit code.

**Why subprocess?** Some modules have import-time side effects
(env vars, network calls). Running each resolution in isolation
matches what mkdocstrings does at build time.

**Output:**

```text
Finding(check="mkdocstrings", severity="error",
  file="docs/reference/multi-agent.md", line=14,
  message="Directive '::: attune.coordination.ConflictResolver' fails to resolve (ModuleNotFoundError: No module named 'attune.coordination')",
  fix="The symbol was renamed/moved. Either restore at the expected path, or update the directive to the new path")
```

---

### Artifact 5 — Reciprocal See-Also advisory (v1.2 or deferred)

**What it does:** parse "See also" / "Related" sections. If A
links to B, check whether B's See-Also section links back to A.
Asymmetric pairs are flagged as `severity="advisory"`.

**Why advisory and likely deferred:** opinionated heuristic that
not every author wants enforced. Implementation depends on
detecting "See Also" sections reliably across varied markdown
styles. Worth designing now so the audit script's report format
supports it, but probably not shipping in this spec's
implementation window — punt to a future spec if it doesn't fit.

**Decision deferred to Phase 3 task review.**

---

### Artifact 6 — CI integration

Add a `wiring-audit` job to `.github/workflows/docs.yml`:

```yaml
jobs:
  wiring-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Run wiring audit
        run: uv run python scripts/audit_docs_wiring.py --format json
```

**Gating:** add `wiring-audit` to `required_status_checks` in
branch protection only after v1 is green on `main`. Avoid
launching with the check failing — that creates immediate red CI
on every PR and erodes the signal.

**Sequencing:**

1. Land v1 audit script + allowlist in a single PR. CI runs but
   advisory-only.
2. Iterate: each subsequent PR fixes one finding category until
   audit reports zero on `main`.
3. Promote to required status check.

---

### Implementation order (Phase 4)

| Step | Deliverable | Estimated effort |
|------|-------------|------------------|
| 1 | Skeleton: `scripts/audit_docs_wiring.py` CLI, allowlist loader, Finding dataclass, JSON + markdown formatters | 1-2 hr |
| 2 | Anchor check (Artifact 3a) + tests | 2-3 hr |
| 3 | Nav check (Artifact 3b) + tests | 1-2 hr |
| 4 | features.yaml check (Artifact 3c) + tests | 1 hr |
| 5 | Allowlist file (Artifact 2) with initial entries from spec | 30 min |
| 6 | First end-to-end run against current `docs/`; iterate on findings (fix or allowlist each) | 2-4 hr (depends on count) |
| 7 | CI integration (Artifact 6), advisory mode | 30 min |
| 8 | Land v1; iterate until `main` is green | (passive — open PRs over time) |
| 9 | Promote to required check | 5 min |
| 10 | v1.1: mkdocstrings symbol resolution (Artifact 4) | 2-3 hr |
| 11 | v1.2 or defer: reciprocal See-Also (Artifact 5) | 2-4 hr (if pursued) |

**Total v1 effort:** ~8-12 hours focused. Splittable across 2-3
sessions; minimum viable is steps 1-7 in one session.

---

## Phase 3: Tasks

**Status:** shipped (authored — see tasks.md)

---

## Phase 4: Implementation

**Status:** shipped (v1 #518/#523/#540; v1.1 2026-07-15 #1394;
Task 10 See-Also advisory deferred)

---

## Open questions for Phase 3 review

These aren't blockers for Phase 2 approval but should be resolved
before Phase 3 task authoring:

1. **`scripts/audit_docs_wiring/` package layout — pure stdlib or
   reuse existing utilities?** Some of the parsing (markdown
   headings, YAML loading) overlaps with `attune-author` and
   `attune-help`. Decision: pure stdlib + `pyyaml` for v1; revisit
   if we want to factor a shared `attune-docs` package later.
2. **Test framework — pytest in `tests/scripts/` or unittest?**
   The existing `scripts/` directory has minimal test coverage;
   adding tests requires picking a location. Recommended:
   `tests/unit/scripts/test_audit_docs_wiring/` under the existing
   pytest setup.
3. **Reciprocal See-Also advisory check — ship v1.2 or defer to
   a sibling spec?** Implementation complexity is real but the
   value is moderate. Could be a good "good first issue" for a
   contributor.
