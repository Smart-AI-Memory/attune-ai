# LinkedIn Post — Attune AI v5.2.0

*Copy below. ~300 words, optimized for LinkedIn feed.*

---

We just completed a three-release migration to full Anthropic best-practices alignment for attune-ai.

The result: 18 production-ready multi-agent workflows — code review, security audit, test generation, release prep — all built on the Claude Agent SDK and running as native Claude Code plugin tools.

What "Anthropic best practices" means in practice:

System prompt separation — each workflow splits persona from task instructions, exactly as Anthropic recommends for the Agent SDK.

Per-agent model routing — Opus for security (where missing a vulnerability is expensive), Sonnet for analysis, Haiku for high-volume scanning. Three models in one workflow, matched to the task.

Budget safety nets — $0.50 quick / $2.00 standard / $5.00 deep. No surprise costs.

Structured output — typed JSON with confidence scores and severity levels, not just prose.

Every workflow is exposed as one of 31 MCP tools, triggered automatically by 10 auto-invoking skills. Say "check this for security issues" and Claude calls the right tool.

For v5.2.0, we also added a unified voice layer so all 18 workflows return results in a consistent tone — and we dogfooded our own bug-predict workflow, which found 5 real path traversal vulnerabilities (CWE-22) in our own 15,591-test codebase.

If your security tools can't find bugs in your own code, they won't find them in your users' code either.

--- CODE START ---
pip install 'attune-ai[developer]'
python -m attune.models.auth_cli setup
--- CODE END ---

Two commands: install, then configure your API key and model routing. Type /attune in Claude Code and go.

GitHub: github.com/Smart-AI-Memory/attune-ai
PyPI: pypi.org/project/attune-ai/

#ClaudeAgentSDK #ClaudeCode #AI #DevTools #Security #OpenSource #Python #AIAgents #Anthropic

---

*Notes: Use ASCII code block markers (not backticks)
to avoid LinkedIn formatting issues. See lessons
learned in CLAUDE.md.*
