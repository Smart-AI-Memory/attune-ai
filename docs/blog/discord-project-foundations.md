# Discord Post: Your Code Is Already the Documentation

**Part 2: The five source types that make living docs
possible**

If you follow standard coding conventions, your code
already contains the documentation. You just need to
treat it that way.

Five source types that serve double duty — runtime
behavior AND help system input:

1. **Google-style docstrings** — Args, Returns, Raises
   sections are machine-parseable. A generator walks the
   structure and produces parameter docs, return
   descriptions, and troubleshooting entries.

2. **Type hints** — `input_tokens: int` is documentation
   you can't lie about. Generators get the "what" for
   free; docstrings provide the "why."

3. **YAML frontmatter** — Skills and templates carry
   structured metadata (name, description, triggers) that
   parsers read without touching the content body.

4. **Class attributes** — Workflow metadata as literal
   class values (`name = "security-audit"`) is
   inspectable at import time. Change the attribute,
   the docs update.

5. **CLI help strings** — argparse/typer help text
   already appears in `--help` output. Same sentence
   works in a reference template.

The principle: metadata embedded in code structure means
no sync step, no "update the docs" ticket, no drift.

Attune AI uses all five to generate 557 help templates
for itself. Install the plugin and say "tell me more"
to see the result:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Runs on your Claude subscription — no API key required.

This is part 2 of a series on building knowledge bases,
help systems, and context-aware docs with Claude Code.
If you find it useful, a star on the repo goes a long
way: https://github.com/Smart-AI-Memory/attune-ai
