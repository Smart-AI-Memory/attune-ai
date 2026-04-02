---
type: faq
name: multiple-pinentry-program-lines-in-gpg-agent-conf-first-wins
source: .claude/CLAUDE.md
---

# FAQ: What should I know about multiple pinentry-program lines in gpg-agent.conf — first wins?

## Answer

GPG uses the first `pinentry-program` directive it finds. Appending a new line doesn't override earlier ones.

**How to fix:**
- Always replace, don't append

```
pinentry-program
```

## Related Topics
- **Error**: Detailed error: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins
