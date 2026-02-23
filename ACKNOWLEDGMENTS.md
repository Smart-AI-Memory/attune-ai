# Acknowledgments

## Attune AI Enhancement Contributors

### Hook System & Markdown Agent Format

The hook system and markdown-based agent definition patterns in this framework were **inspired by** the excellent work in [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by **Affaan Mustafa** (@affaan-m).

Affaan's repository represents 10+ months of battle-tested Claude Code configurations, and we learned valuable architectural patterns from studying his approach:

- **Event-driven hooks** (PreToolUse, PostToolUse, SessionStart, etc.)
- **Markdown agents with YAML frontmatter** for portable, human-readable definitions
- **Strategic context compaction** for managing token windows
- **Continuous learning patterns** for extracting reusable knowledge

#### What We Learned vs. What We Built

| Pattern Learned | Empathy Implementation |
|-----------------|------------------------|
| Hook event types | Python/Pydantic-based HookConfig with async execution |
| Markdown agent format | MarkdownAgentParser integrated with UnifiedAgentConfig |
| Markdown commands | CommandRegistry with YAML frontmatter parsing and alias resolution |
| Session persistence | Integration with Empathy's state management and trust levels |
| Context compaction | CompactionStateManager with SBAR handoff preservation |
| Continuous learning | SessionEvaluator and PatternExtractor for knowledge retention |

Our implementation is original Python code designed to integrate with Attune AI's existing architecture (LangGraph, Pydantic, multi-tier model routing), but the conceptual patterns we learned from Affaan's work were invaluable.

#### License

everything-claude-code is released under the MIT License, which permits derivative works with attribution. We provide this attribution in good faith and gratitude.

#### Links

- **everything-claude-code**: https://github.com/affaan-m/everything-claude-code
- **Affaan's Guides**:
  - [The Shorthand Guide](https://x.com/affaanmustafa/status/2012378465664745795)
  - [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352)
- **Affaan on X/Twitter**: [@affaanmustafa](https://x.com/affaanmustafa)

---

### Claude Code & Workflow Philosophy

**Boris Cherny** (@bcherny), the creator of
[Claude Code](https://github.com/anthropics/claude-code),
was also a significant inspiration for this project. His
candid posts about how he personally uses Claude Code
offered practical insights that shaped how Attune AI
approaches agentic workflows:

- **Plan Mode first** — Boris advocates using Plan Mode
  for every non-trivial task, iterating on the plan before
  switching to execution. This directly influenced Attune's
  Socratic discovery pattern and our emphasis on scoping
  before running.
- **Parallel sessions** — Running multiple Claude Code
  sessions concurrently (5+ in terminal, 5-10 on
  claude.ai/code) demonstrated that orchestrating many
  agents in parallel is not just possible but productive.
  This validated Attune's multi-agent architecture.
- **Verification loops** — Boris stresses giving Claude a
  way to verify its own work, noting it can 2-3x the
  quality of results. This principle is embedded in
  Attune's validation-first workflow design.
- **Shared CLAUDE.md** — His team checks CLAUDE.md into
  git and collaboratively maintains it as a living
  document. Attune adopted this pattern directly for
  project-level instructions.

In truth, many of these patterns were already part of
Attune's workflow before we encountered Boris's posts —
we had arrived at similar practices independently by
following
[Anthropic's own documentation](https://docs.anthropic.com)
and best-practice guides for building with Claude. When
Boris shared his workflow publicly, it served less as a
revelation and more as a validation: seeing the creator of
Claude Code converge on the same patterns we were already
using gave us confidence that we were on the right track.
His posts also offered refinements and practical details
that sharpened our implementation.

One of Attune AI's goals is to make these best practices
accessible to a wider audience. The patterns Boris
describes — and that Anthropic's documentation
recommends — (plan-then-execute, verification loops,
multi-agent orchestration, living project instructions)
are powerful but non-obvious, and without a framework to
codify them, each team would have to discover and implement
them independently. Attune packages these proven workflows
into reusable, structured tools so that any developer can
benefit from them out of the box.

#### Links

- **Boris on X/Twitter**:
  [@bcherny](https://x.com/bcherny)
- **Original thread**: [How I use Claude Code](https://x.com/bcherny/status/2007179832300581177)
- **Detailed writeup**: [How the Creator of Claude Code Uses Claude Code](https://howborisusesclaudecode.com/)

---

Thank you, Affaan and Boris, for sharing your knowledge
with the community.
