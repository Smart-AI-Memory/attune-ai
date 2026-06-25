# Sibling Pre-commit — session starter prompts

One self-contained starter prompt per sibling repo. Open a fresh
Claude Code session **in that repo's directory**, then paste the
matching prompt. Each is independent and produces one mergeable PR.

| Phase | Repo | Starter | Notes |
|-------|------|---------|-------|
| 1 | attune-rag | [attune-rag.md](attune-rag.md) | First — golden fixtures are the load-bearing exclusion |
| 2 | attune-author | [attune-author.md](attune-author.md) | Watch long prompt-string ruff trips (`# noqa`) |
| 3 | attune-help | [attune-help.md](attune-help.md) | Template `.md`/`.json` exclusion is critical |
| 4 | attune-gui | [attune-gui.md](attune-gui.md) | Hybrid repo; `editor-frontend/` out of scope |

Source of truth for the baseline + exclusions:
[../decisions.md](../decisions.md) (D1, D2, D3). If a starter and
decisions.md disagree, decisions.md wins — update the starter.

Each prompt is keyless (zero API cost). After all four land, mark the
spec status complete in [../tasks.md](../tasks.md) Phase 5.
