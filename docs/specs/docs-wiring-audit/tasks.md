# Tasks: Documentation Wiring Audit

**Status:** parked (2026-07-13) — v1 shipped (#518/#523 anchor check via `scripts/audit_docs_wiring.py`; #540 CI job, since promoted to a required check on main); remaining: nav/features.yaml/mkdocstrings checks (Tasks 3, 4, 9) + See-Also advisory (Task 10, deferred).
**Phase:** 3 — Tasks
**Predecessor:** [design.md](./design.md) (Phase 2 authored
2026-05-31)
**Successor:** Phase 4 implementation (not started)

---

## Phase 3: Tasks

This phase decomposes [design.md's implementation order](./design.md#implementation-order-phase-4)
into reviewable task entries with explicit acceptance criteria,
file paths, and dependencies. Tasks 1-7 ship in v1; tasks 8-9 ship
in v1.1 and v1.2 respectively.

**Task numbering matches the design's implementation order
table** so a reviewer can cross-reference one-to-one.

---

### Task 1 — Audit script skeleton

**Goal:** establish the CLI, allowlist loader, `Finding`
dataclass, and output formatters with zero checks wired in.
Running `python scripts/audit_docs_wiring.py` prints "no checks
registered" and exits 0.

**Files to create:**

- `scripts/audit_docs_wiring.py` (CLI entry, ~30 LOC)
- `scripts/audit_docs_wiring/__init__.py` (`__version__`)
- `scripts/audit_docs_wiring/cli.py` (argparse + dispatch)
- `scripts/audit_docs_wiring/allowlist.py` (`Allowlist` dataclass,
  `load_allowlist()`, reason-comment enforcement)
- `scripts/audit_docs_wiring/report.py` (markdown + JSON
  formatters)
- `scripts/audit_docs_wiring/checks/__init__.py` (empty)
- `tests/unit/scripts/test_audit_docs_wiring/__init__.py`
- `tests/unit/scripts/test_audit_docs_wiring/test_allowlist.py`
- `tests/unit/scripts/test_audit_docs_wiring/test_report.py`

**Acceptance criteria:**

- [ ] `python scripts/audit_docs_wiring.py --help` prints CLI
  usage with all subcommands listed (even though they're empty
  stubs).
- [ ] `python scripts/audit_docs_wiring.py --check anchor` exits
  0 with `"No findings."` markdown output.
- [ ] `python scripts/audit_docs_wiring.py --format json` outputs
  valid JSON `{"findings": []}`.
- [ ] `Allowlist.load_allowlist()` raises `ValueError` if any
  entry in `.audit/orphans.yml` lacks a `# reason:` comment on
  the preceding line.
- [ ] `Finding` dataclass is frozen (immutable).
- [ ] Tests cover: empty allowlist, well-formed allowlist,
  missing-reason allowlist, all three formatter outputs.

**Effort:** 1-2 hours.

**Out of scope for this task:** any actual check logic. The
goal is the scaffolding only.

---

### Task 2 — Anchor integrity check

**Goal:** `scripts/audit_docs_wiring/checks/anchor.py`
implements the anchor check per [design.md §3a](./design.md#3a-anchor-integrity-checksanchorpy).

**Files to create:**

- `scripts/audit_docs_wiring/checks/anchor.py` (~150 LOC)
- `tests/unit/scripts/test_audit_docs_wiring/test_anchor.py`
  (~100 LOC)

**Acceptance criteria:**

- [ ] Walks every `[text](file.md#anchor)` and `[text](#anchor)`
  link in `docs/**/*.md`.
- [ ] Uses the same slugifier mkdocs uses (PyMdown extensions'
  `toc.slugify`); confirms via test against a known
  heading→anchor pair (e.g. `## My Section ✨` → `#my-section`).
- [ ] Skips external links (`http://`, `https://`, `mailto:`).
- [ ] Skips cross-repo anchors (links with `github.com` host) —
  flagged as v2 work in comment.
- [ ] Resolves reference-style links before checking.
- [ ] Returns a `Finding` per broken anchor with `severity="error"`,
  `file`, `line`, descriptive `message`, and `fix` suggestion.
- [ ] Test covers: valid anchor, invalid anchor, intra-page
  anchor, reference-style link, external link skipped, slugifier
  matches mkdocs.

**Effort:** 2-3 hours.

**Dependencies:** Task 1 (skeleton must exist).

---

### Task 3 — Nav ↔ filesystem check

**Goal:**
`scripts/audit_docs_wiring/checks/nav.py` implements the
nav-vs-filesystem check per [design.md §3b](./design.md#3b-nav-filesystem-checksnavpy).

**Files to create:**

- `scripts/audit_docs_wiring/checks/nav.py` (~100 LOC)
- `tests/unit/scripts/test_audit_docs_wiring/test_nav.py`
  (~80 LOC)

**Acceptance criteria:**

- [ ] Parses `mkdocs.yml`'s `nav:` section recursively (nav can
  be deeply nested).
- [ ] For every nav entry pointing at a file: assert the file
  exists. Surface dangling entries as
  `severity="error"`.
- [ ] For every `docs/**/*.md` not in nav: check the allowlist.
  If not allowlisted, surface as `severity="error"`.
- [ ] Allowlist matching handles trailing-slash directory
  prefixes AND glob patterns (`docs/BLOG_*.md`).
- [ ] Test covers: well-formed nav, dangling nav entry, unlisted
  doc not allowlisted, unlisted doc that IS allowlisted, nested
  nav structure, glob pattern matching.

**Effort:** 1-2 hours.

**Dependencies:** Task 1 (skeleton + allowlist loader).

---

### Task 4 — `features.yaml` ↔ filesystem check

**Goal:**
`scripts/audit_docs_wiring/checks/features_yaml.py` implements
the features.yaml check per [design.md §3c](./design.md#3c-featuresyaml-filesystem-checksfeatures_yamlpy).

**Files to create:**

- `scripts/audit_docs_wiring/checks/features_yaml.py` (~80 LOC)
- `tests/unit/scripts/test_audit_docs_wiring/test_features_yaml.py`
  (~60 LOC)

**Acceptance criteria:**

- [ ] Loads `.help/features.yaml`.
- [ ] For every `doc_paths` entry across every feature: assert
  file exists. Dangling → `severity="error"`.
- [ ] Walks `docs/reference/*.md` and `docs/how-to/*.md`; for
  each: check whether any feature lists it in `doc_paths`.
  Unlinked files matching the pattern surface as
  `severity="warning"` (advisory).
- [ ] Test covers: valid features.yaml, dangling doc_paths,
  unlinked feature-shaped doc, doc that's correctly listed.

**Effort:** ~1 hour.

**Dependencies:** Task 1.

---

### Task 5 — Initial `.audit/orphans.yml`

**Goal:** create the allowlist file with the initial subtree
entries enumerated in [design.md §2](./design.md#artifact-2-auditorphansyml).

**Files to create:**

- `.audit/orphans.yml` (~30 LOC with reason comments)
- `.audit/README.md` (brief explanation: what `.audit/` is for,
  how to add entries, who reviews changes)

**Acceptance criteria:**

- [ ] Every entry has a `# reason:` comment on the preceding
  line.
- [ ] Loads cleanly via `Allowlist.load_allowlist()` (verifies
  Task 1's enforcement works).
- [ ] Initial entries: `docs/blog/`, `docs/BLOG_*.md`,
  `docs/archive/`, `docs/examples/`, `docs/pitch/`,
  `docs/specs/`, `docs/implementation/`, `docs/cost-analysis/`,
  `docs/conversations/`.

**Effort:** 30 min.

**Dependencies:** Task 1 (for the loader's reason-comment
enforcement; Task 5 stress-tests it).

---

### Task 6 — First end-to-end run + iterate fixes

**Goal:** run the v1 audit (Tasks 2-4) against current `docs/`
and bring the finding count to zero by either fixing the issue
or adding to the allowlist with reason.

**Process:**

1. Run `python scripts/audit_docs_wiring.py --format markdown >
   /tmp/audit-baseline.md`.
2. Triage every finding: real-bug → fix it; intentional → add
   to allowlist with reason.
3. Re-run audit; iterate until count is zero.
4. Commit the fixes + allowlist updates as separate commits per
   logical group (e.g. "fix(docs): repair 9 broken anchors in
   API_REFERENCE.md", "chore(audit): allowlist docs/archive/").

**Acceptance criteria:**

- [ ] `python scripts/audit_docs_wiring.py` exits 0 against
  current `main`.
- [ ] No allowlist entries lack a reason comment.
- [ ] Each fix commit is scoped (one finding category per
  commit) for clean review.

**Effort:** 2-4 hours depending on actual finding count. The
spec estimates ~9 anchor warnings + ~10 excluded-link warnings +
~35 orphan-page warnings as the baseline; allowlisting handles
most orphans, fixes handle the anchor breakage.

**Dependencies:** Tasks 1-5 must all be merged or co-located on
the same branch.

---

### Task 7 — CI integration (advisory mode) — **done 2026-06-01**

**Goal:** add the `wiring-audit` job to
`.github/workflows/docs.yml` per [design.md §6](./design.md#artifact-6-ci-integration).
Job runs on every PR but is NOT yet a required status check.

**Files to modify:**

- `.github/workflows/docs.yml` (~10 LOC added)

**Acceptance criteria:**

- [ ] `wiring-audit` job appears on PRs.
- [ ] Job runs `uv run python scripts/audit_docs_wiring.py
  --format json` and exits with the script's exit code.
- [ ] Job is NOT added to branch protection's
  `required_status_checks` yet (advisory only).
- [ ] README or CONTRIBUTING note added explaining the audit
  job exists and how to interpret findings.

**Effort:** 30 min.

**Dependencies:** Task 6 (audit must be exit-0 on main before
CI integration, else every PR is red from day one).

---

### Task 8 — Promote to required check

**Goal:** once `main` has held green on wiring-audit for ≥3
consecutive PRs, add it to branch protection as a required
status check.

**Process:**

1. Verify last 3 merges to main have green `wiring-audit` job.
2. Update branch protection via `gh api`:
   `gh api repos/Smart-AI-Memory/attune-ai/branches/main/protection/required_status_checks/contexts -X POST -F 'contexts[]=wiring-audit'`
3. Verify the check now appears as required on a new PR.

**Acceptance criteria:**

- [ ] New PRs cannot merge without `wiring-audit` passing.
- [ ] Decision recorded in [`decisions.md`](./decisions.md) with
  the date promoted.

**Effort:** 5 min (3-PR baking window is passive).

**Dependencies:** Task 7 merged; 3 successful green runs on main.

---

### Task 9 — mkdocstrings symbol resolution (v1.1)

**Goal:**
`scripts/audit_docs_wiring/checks/mkdocstrings.py` implements
the symbol-resolution check per [design.md §4](./design.md#artifact-4-mkdocstrings-symbol-resolution-v11).

**Files to create:**

- `scripts/audit_docs_wiring/checks/mkdocstrings.py` (~120 LOC)
- `tests/unit/scripts/test_audit_docs_wiring/test_mkdocstrings.py`
  (~80 LOC)

**Acceptance criteria:**

- [ ] `grep -rn '^:::' docs/` finds every directive across the
  whole tree (not just the 5 known files).
- [ ] Each directive's symbol is resolved via subprocess
  isolation (`subprocess.run([sys.executable, "-c", "import X;
  getattr(X, 'Y')"])`).
- [ ] Subprocess failures surface as `severity="error"` with
  the underlying error message.
- [ ] Test covers: valid resolution, missing module, missing
  attribute, malformed directive.

**Effort:** 2-3 hours.

**Dependencies:** Tasks 1-7 complete; new release ships v1
before v1.1 starts.

---

### Task 10 — Reciprocal See-Also advisory (v1.2 or defer)

**Decision deferred to post-v1 review.** If the v1 audit script
proves valuable and the See-Also gap surfaces concrete pain, this
task gets scheduled. Otherwise, the design is on file and the
task can sit indefinitely.

**Acceptance criteria (if pursued):**

- [ ] `scripts/audit_docs_wiring/checks/see_also.py` implemented
  per [design.md §5](./design.md#artifact-5-reciprocal-see-also-advisory-v12-or-deferred).
- [ ] `severity="advisory"` — surfaces in reports but does NOT
  fail CI.

**Effort:** 2-4 hours (if pursued).

---

## Task ordering summary

| Task | Effort | Phase | Blocks |
|------|--------|-------|--------|
| 1 — Skeleton | 1-2 hr | v1 | All others |
| 2 — Anchor check | 2-3 hr | v1 | Task 6 |
| 3 — Nav check | 1-2 hr | v1 | Task 6 |
| 4 — features.yaml check | 1 hr | v1 | Task 6 |
| 5 — Allowlist file | 30 min | v1 | Task 6 |
| 6 — End-to-end run + fixes | 2-4 hr | v1 | Task 7 |
| 7 — CI advisory mode | 30 min | v1 | Task 8 |
| 8 — Promote to required | 5 min | v1 | (release-prep dep) |
| 9 — mkdocstrings | 2-3 hr | v1.1 | (independent) |
| 10 — See-Also | 2-4 hr | v1.2 | (independent, deferred) |

**v1 total:** ~8-12 hours focused, splittable across 2-3 sessions.
**Minimum-viable session:** Tasks 1-7 in one focused session
(7-10 hours).
**Faster split:** Tasks 1+2 in session 1 (3-5 hr); Tasks 3-5
in session 2 (2-3 hr); Tasks 6-7 in session 3 (2-4 hr).

---

## Phase 4: Implementation

**Status:** not started

_To be executed after Phase 3 approval. Tasks above are the
playbook; each task corresponds to a PR or a single commit
within a PR, with the acceptance criteria as the test gate._
