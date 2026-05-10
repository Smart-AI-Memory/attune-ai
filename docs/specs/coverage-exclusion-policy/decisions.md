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
