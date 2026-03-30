---
type: faq
name: multiple-pinentry-program-lines-in-gpg-agent-conf-first-wins
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins?

## Answer

GPG uses the first `pinentry-program` directive it finds. Appending a new line doesn't override earlier ones.


**Fix:**

- Always replace, don't append

```
pinentry-program
```

## Related Topics
- **Error**: Detailed error: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins
