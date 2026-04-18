# attune-rag — lives in its own repo

The `attune-rag` Python package has its own dedicated repo:

- **GitHub:** https://github.com/Smart-AI-Memory/attune-rag
- **PyPI:** https://pypi.org/project/attune-rag/

Install from PyPI:

```bash
pip install 'attune-rag'                   # core (no LLM SDK)
pip install 'attune-rag[attune-help]'      # + bundled help corpus
pip install 'attune-rag[claude]'           # + Claude adapter
pip install 'attune-rag[openai]'           # + OpenAI adapter
pip install 'attune-rag[gemini]'           # + Gemini adapter
pip install 'attune-rag[all]'              # everything
```

For local editable development from this monorepo, the
sibling-clone layout is configured in this repo's
`pyproject.toml` under `[tool.uv.sources]`:

```toml
[tool.uv.sources]
attune-rag = { path = "../attune-rag", editable = true }
```

Clone the package repo as a sibling of `attune-ai` to
enable editable cross-repo development:

```bash
cd /path/to/parent-of-attune-ai
git clone https://github.com/Smart-AI-Memory/attune-rag.git
```
