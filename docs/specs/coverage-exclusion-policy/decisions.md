# Per-decision log — Coverage exclusion policy

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
