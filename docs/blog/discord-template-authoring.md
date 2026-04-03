# Discord Post: 11 Template Types That Turn Code Into Help

**Part 3: How 557 templates organize developer
assistance**

In Part 2 I showed that code conventions (docstrings,
type hints, frontmatter) are already your documentation
source. This post covers what you turn them into.

Attune AI uses 11 template types, each for a different
moment in a developer's workflow:

| Type | Count | When it fires |
|------|-------|---------------|
| Errors | 149 | Known error or precursor detected |
| Tips | 95 | Contextual advice during lookups |
| FAQs | 85 | Tag search or cross-links |
| References | 84 | "Tell me more" (third ask) |
| Warnings | 82 | Pattern that leads to problems |
| Comparisons | 71 | "Difference between X and Y?" |
| Tasks | 51 | "Tell me more" (second ask) |
| Concepts | 50 | First ask ("what is X?") |
| Troubleshooting | 41 | Problem-solving, multi-cause |
| Quickstarts | 32 | First interaction with a tool |
| Notes | 17 | Background context, design decisions |

Every template is markdown with YAML frontmatter:

```yaml
---
type: concept
name: audience-adaptation
tags: [help-system, architecture]
source: src/attune/help/transformers.py
---
```

The `source` field is key — when that file changes, the
maintenance pipeline knows the template is stale.

Templates connect via cross-links. A concept links to
its task, which links to its reference. That's what
powers progressive depth:

```
"what is security audit?"  ->  concept
"tell me more"             ->  task (cross-linked)
"tell me more"             ->  reference (cross-linked)
```

The engine follows cross-links to a *different template
type*, not just a longer version of the same content.

Try it:

```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Runs on your Claude subscription — no API key required.

Part 3 of a series on building knowledge bases and
context-aware docs with Claude Code. Star the repo if
you find it useful:
https://github.com/Smart-AI-Memory/attune-ai
