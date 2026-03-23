# Discord Post — Attune AI v5.2.0

*Under 2,000 characters. Discord-friendly markdown
(no tables, no images).*

---

## Building 18 Production Workflows on the Claude Agent SDK

We just shipped **attune-ai v5.2.0**, completing a three-release migration to full Anthropic best-practices alignment. Every workflow now runs on the Claude Agent SDK.

**What each workflow gets from the SDK:**

- **System prompt separation** — persona split from task instructions, per Anthropic's recommendations
- **Per-agent model routing** — Opus for security, Sonnet for analysis, Haiku for scanning. Three models in one workflow, matched to the task
- **Budget caps** — $0.50 quick / $2.00 standard / $5.00 deep. No surprise costs
- **Structured output** — typed JSON with confidence scores, not just prose

**Claude Code plugin integration:**
All 18 workflows exposed as 31 MCP tools, triggered by 10 auto-invoking skills. Say "check this for security issues" and Claude calls the right tool. Security hooks block eval/exec and validate file paths automatically.

**New in v5.2.0:**
- Unified voice layer — consistent output across all workflows
- Dogfooded our bug-predict workflow and found 5 real CWE-22 path traversal gaps in our own 15,591-test codebase

```
pip install 'attune-ai[developer]'
python -m attune.models.auth_cli setup
```

Type `/attune` in Claude Code and go.

GitHub: <https://github.com/Smart-AI-Memory/attune-ai>
PyPI: <https://pypi.org/project/attune-ai/>
