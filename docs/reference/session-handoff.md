# Session Handoff

## Reference

### Python API (`attune.handoff`)

| Function | Signature (keyword-only after `repo_root`) | Returns |
| --- | --- | --- |
| `handoff_create` | `repo_root=\".\"`, `goal`, `acceptance_criteria`, `scope_assumptions`, `current_state`, `next_action`, `verification`, `provider`, `base_ref=\"origin/main\"` | `{ok, path, slug, packet, memory}` or `{ok: False, reason}` |
| `handoff_resume` | `repo_root=\".\"`, `slug=None` (defaults to current branch) | `{ok, slug, path, verified, warnings, asserted, memory}` or `{ok: False, reason}` |

### MCP tools

| Tool | Required args | Notes |
| --- | --- | --- |
| `handoff_create` | `goal` | Optional: `acceptance_criteria`, `scope_assumptions`, `current_state`, `next_action`, `verification` rows, `provider` |
| `handoff_resume` | none | Optional `slug`; defaults to the current branch |

### Constants

| Constant | Value | Meaning |
| --- | --- | --- |
| `attune.handoff.packet.PACKET_CAP_BYTES` | 8192 | Max rendered packet size |
| `attune.handoff.packet.FIELD_CAP_BYTES` | 2048 | Max per-field size |
| `attune.handoff.verify.STALE_AFTER_DAYS` | 7 | Age before `packet_stale_days` fires |

### Failure reasons

| Reason | Surface | Meaning |
| --- | --- | --- |
| `field_over_cap` | create | A prose field exceeded 2048 bytes |
| `git_read_failed` | both | Git state could not be read |
| `packet_not_found` | resume | No packet exists for the slug |
| `invalid_slug` | resume | Slug failed path validation |
| `packet_unreadable` | resume | File unreadable or malformed |

<!-- attune-generated: source_hash=963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66 feature=session-handoff kind=reference generated_at=2026-07-28 -->
