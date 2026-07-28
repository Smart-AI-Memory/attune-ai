---
type: faq
name: session-handoff-faq
feature: session-handoff
depth: faq
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
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
