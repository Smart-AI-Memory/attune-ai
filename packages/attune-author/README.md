# attune-author — moved

The `attune-author` Python package has its own dedicated repo now:

- **GitHub:** https://github.com/Smart-AI-Memory/attune-author
- **PyPI:** https://pypi.org/project/attune-author/
- **Claude Code plugin:** `claude plugin install attune-author@attune-ai`
  (from the [Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
  marketplace)

Install from PyPI:

```bash
pip install 'attune-author'            # library only
pip install 'attune-author[plugin]'    # library + MCP server runtime
pip install 'attune-author[ai]'        # library + AI polish features (anthropic SDK)
```

For local editable development from this monorepo, the
sibling-clone layout is configured in this repo's
`pyproject.toml` under `[tool.uv.sources]`:

```toml
[tool.uv.sources]
attune-author = { path = "../attune-author", editable = true }
```

Clone the package repo as a sibling of `attune-ai` to
enable editable cross-repo development:

```bash
cd /path/to/parent-of-attune-ai
git clone https://github.com/Smart-AI-Memory/attune-author.git
```
