# attune-help — moved

The `attune-help` Python package has its own dedicated repo now:

- **GitHub:** https://github.com/Smart-AI-Memory/attune-help
- **PyPI:** https://pypi.org/project/attune-help/
- **Claude Code plugin:** `claude plugin install attune-help@attune-ai`
  (from the [Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
  marketplace)

Install from PyPI:

```bash
pip install 'attune-help'              # library only
pip install 'attune-help[plugin]'      # library + MCP server runtime
```

For local editable development from this monorepo, the
sibling-clone layout is configured in this repo's
`pyproject.toml` under `[tool.uv.sources]`:

```toml
[tool.uv.sources]
attune-help = { path = "../attune-help", editable = true }
```

Clone the package repo as a sibling of `attune-ai` to
enable editable cross-repo development:

```bash
cd /path/to/parent-of-attune-ai
git clone https://github.com/Smart-AI-Memory/attune-help.git
```
