---
type: warning
name: multiple-pinentry-program-lines-in-gpg-agent-conf-first-wins
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins

## Condition

GPG uses the first `pinentry-program` directive it finds

## Risk

Ignoring this guidance may cause: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins

## Mitigation

1. Always replace, don't append

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins
