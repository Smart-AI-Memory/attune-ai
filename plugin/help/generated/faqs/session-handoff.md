---
name: session-handoff
source: content/features/session-handoff.md
tags:
- handoff
- collaboration
- multi-llm
- memory
type: faq
---

# Session Handoff FAQ

## Does resume switch me to the packet's branch?

No. Resume performs no side effects — no checkout, no
writes, no test runs. It reports; you act.

## Can I hand off between different AI providers?

Yes — that is the point. Any client of the attune MCP
server can create or resume: Claude Code, Codex, and Antigravity
all reach the same tools, and the packet's `provider` field
records who authored it.

## What happens if I create a packet twice on one branch?

The second create overwrites in place, and the first
packet's `created_at` is preserved as `superseded_at` in the
frontmatter.

## Is there a CLI command?

Not yet, deliberately — the surface is MCP-only until real
usage justifies a wrapper.
