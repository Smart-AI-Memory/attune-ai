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
| `publish` | Version bump and publish |

## Usage

```bash
/release                # Ask what to do
/release prep           # Release prep checks
/release security       # Security audit
/release health         # Health check
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

### publish

Use `AskUserQuestion` to confirm:

- Version bump type? (patch, minor, major)
- Changelog reviewed?
- All checks passing?

Then guide through:

1. Version bump in pyproject.toml
2. Update CHANGELOG.md
3. Create git tag
4. Push and publish
