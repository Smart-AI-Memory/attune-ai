---
name: release
description: Release preparation and publishing
---
# release

Release preparation, validation, and publishing.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `prep` | Release readiness checks |
| `security` | Pre-release security audit |
| `health` | Code health check |
| `audit` | Release-audit stage — what class of defect could this release introduce? |
| `publish` | Version bump and publish |

## Usage

```bash
/release                # Ask what to do
/release prep           # Release prep checks
/release security       # Security audit
/release health         # Health check
/release audit          # Release-audit stage (packet + sitting)
/release publish        # Publish release
```

## Behavior

### prep

Run release preparation workflow:

```bash
uv run attune workflow run release-prep
```

This checks:

- Test suite passes
- No critical security issues
- Documentation is current
- Changelog is updated

### security

Run security audit focused on release readiness:

```bash
uv run attune workflow run security-audit --path src/
```

### health

Run code health checks:

- Test coverage
- Lint status
- Type check status
- Dependency audit

### audit

The release-audit stage (`docs/specs/release-audit-stage/`). The other
release surfaces check hygiene; this one asks what class of defect THIS
diff could have introduced. It sits every release (D2) — an empty
residual still sits, which is cheap by design.

```bash
python -m attune.classes.stage --repo <owner/name>
```

Six steps: baseline (merge-base vs the last release tag) -> reconcile
(CLOSED gates green in CI, bound to this head SHA) -> sweep (rules over
the changed `src/` surface, D10) -> residual packet -> sitting (three
seats, one round) -> chair rules.

Exit codes are the contract:

| Code | Meaning | What to do |
| ---- | ------- | ---------- |
| 0 | Ready for the chair | Rule each residual item |
| 1 | Aborted | Read `aborted_at` — a red reconcile means fix CI first; seats never sit on a broken baseline |
| 2 | Residual exceeds schema v1 | **Split the release.** The chair splits; the tool re-runs each partition. Never truncate. |

Then the chair rules every item exactly once
(`SHIP` / `HOLD` / `GATE-FIRST` / `DEFER`) and a manifest is written to
`.attune/release-manifests/<tag>.json`. A manifest is immutable; a
re-run writes a new one.

### publish

**Gate first — a tag needs a cleared audit manifest (R7):**

```bash
python -c "
from pathlib import Path
from attune.classes.manifest import require_manifest, ManifestError
try:
    m = require_manifest(Path('.'), '<tag>', '<full-40-char-head-sha>')
    print('audit manifest OK:', m.chair_receipt)
except ManifestError as e:
    raise SystemExit(f'REFUSED [{e.reason}] {e.detail}')
"
```

This refuses a tag with no manifest, a manifest recorded against a
DIFFERENT commit (a ruling on an earlier SHA does not authorize this
tag), or one whose chair left items at `HOLD`/`GATE-FIRST` — D4's teeth:
the stage may hold a release until a re-exposed class gets its gate.

Then use `AskUserQuestion` to confirm:

- Version bump type? (patch, minor, major)
- Changelog reviewed?
- All checks passing?

Then guide through:

1. Version bump in pyproject.toml
2. Update CHANGELOG.md
3. Create git tag
4. Push and publish
