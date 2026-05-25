# Per-decision log — Coverage exclusion policy
**Status:** complete
Append-only log. Phase 3A audit findings + per-entry resolution as
Phase 3B commits land.

---

## Phase 3A audit (2026-05-10)

### Method

`grep -E "^\s*\""` across the `[tool.coverage.run] omit = [...]`
block in `pyproject.toml`, then filter for lines without an inline
`#` comment.

### Findings

- **64 total `omit` entries**.
- **4 meta-excludes** (no comment needed per Phase 1 G2):
  - `*/tests/*`
  - `*/test_*.py`
  - `*/__pycache__/*`
  - `*/site-packages/*`
- **57 documented production-code entries** with inline `#`
  reasons. Spot-check shows reasons fit the categories named in
  requirements.md (interactive CLI, infrastructure server, live
  service required, deprecated, optional adapter, standalone
  script, example/demo).
- **3 production-code entries undocumented** (require Phase 3B
  resolution):
  - `*/hooks/scripts/help_freshness_nudge.py`
  - `*/meta_workflows/cli_commands/agent_commands.py`
  - `*/attune/config.py`

### Compliance rate

- 57 documented / 60 production-code entries = **95% compliance**
  before this spec lands.
- Target after Phase 3B: 100%.

### Observations worth recording

The 95% pre-spec compliance rate suggests the *informal*
convention was already strong — most contributors were already
adding `#` comments without being asked. This spec mostly
formalizes existing practice and catches the 5% gap.

The interesting question isn't "why were 3 entries undocumented"
(probably just oversight) but "are any of those 3 *wrongly*
excluded?" That's the audit's actual value — particularly for
`attune/config.py`, which is a suspicious path for an
undocumented exclusion. See task #6.

---

(per-entry resolutions appended below as commits land)

---

## Phase 3B resolution (2026-05-12)

### Outcome

All three undocumented entries were documented in-flight via PR #212
(`68b4bb1c`, "CI stabilization") between the 2026-05-10 audit and
its squash-merge to main on 2026-05-11. No new code change required
by this spec; the verification step confirmed accuracy.

### Per-entry verification

| Entry | Comment as landed | Category | Verified by |
|-------|-------------------|----------|-------------|
| `*/hooks/scripts/help_freshness_nudge.py` | "Standalone hook script (not importable via pytest)" | 6 — standalone script | File has `#!/usr/bin/env python3` shebang and SessionStart-hook docstring. Sibling entries (`evaluate_session.py`, `session_start.py`, etc.) use the same wording. |
| `*/meta_workflows/cli_commands/agent_commands.py` | "Interactive agent CLI (requires live Claude agent loop)" | 1 — interactive CLI | File uses `typer` + `rich`, `@meta_workflow_app.command("create-agent")`. Sibling files in same dir use "Interactive analytics / templates / config / memory" wording. |
| `*/attune/config.py` | "Shadowed by attune/config/ package — unreachable import" | 8 — justified-other | Confirmed empirically: `import attune.config` resolves to `src/attune/config/__init__.py` (the package), not the .py file. `attune.config.__file__` ends in `/config/__init__.py`. The standalone module is dead code at the import layer. |

### Compliance

- 60/60 production-code `omit` entries documented = **100% compliance**.
- Phase 3D's "all undocumented entries resolved" gate is met by inspection.

### Out-of-scope follow-up

`src/attune/config.py` is dead code at the import layer — Python's
import machinery always selects the `config/` package over the
sibling module file. The exclusion is technically correct (the file
*can't* be reached via `import attune.config`), but the cleaner fix
would be to delete the file entirely rather than carry a permanent
exclusion. Flagging for a separate retirement task; not in scope
here since this spec is about documenting exclusions, not removing
dead code. The decisions.md from `docs/specs/deprecated-module-retirement/`
is the natural home if it picks up this candidate.

Risk to verify before deletion: grep for any module that might
sidestep the shadowing via `importlib.import_module("attune.config")`
plus a `__file__` lookup, or via `pkgutil.iter_modules` discovery.
None found in a quick sweep, but worth confirming under a real
retirement spec.

---

## Phase 3C resolution (2026-05-12)

### Outcome

Shipped `scripts/check_coverage_omits.py` plus a pre-commit hook
entry. Spec status flipped to `complete` in all four .md files.

### What the script enforces

- Locates the `[tool.coverage.run] omit = [...]` block in
  `pyproject.toml` via line scan (resilient to comments and
  whitespace between the section header and the `omit =` line).
- For each quoted pattern inside the block, requires an inline
  `#` comment on the same line *unless* the pattern is one of
  the four meta-excludes: `*/tests/*`, `*/test_*.py`,
  `*/__pycache__/*`, `*/site-packages/*`.
- Exits 0 (clean), 1 (offenders listed to stderr with file:line
  references), or 2 (block not locatable).

### Side-effect of writing the enforcement: convention normalization

PR #212 added the three previously-undocumented entries with their
reasons on the *preceding* line rather than inline. That's a valid
form of documentation but doesn't match the dominant convention
in the file (57 of 60 production-code entries used inline) or the
mandate in `design.md` ("inline `#` comment"). To make the
enforcement script crisp, the three entries were normalized to
inline form in this commit. No semantic change; identical reason
text, just rearranged onto the same line as the pattern.

### Pre-commit hook integration (D3)

Added a local hook `check-coverage-omits` to
`.pre-commit-config.yaml`. Scoped to changes in `pyproject.toml`
only (no overhead on unrelated commits). Stage: `pre-commit` (runs
on every commit by default, matching the surrounding hooks'
behavior). Verified by running
`uv run --with pre-commit pre-commit run check-coverage-omits
--files pyproject.toml` — passes on the clean tree.

### Task #9 verification

Stripped the inline comment from `*/attune/config.py` as a
deliberate violation. Script output:
```
Undocumented coverage-omit entries (each must have an inline
`# reason` comment):
  pyproject.toml:711: */attune/config.py

See docs/specs/coverage-exclusion-policy/requirements.md for the
reason-category taxonomy.
```
Exit 1 as expected. Comment restored; clean tree exits 0.
