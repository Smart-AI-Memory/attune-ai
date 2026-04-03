---
type: error
name: multiple-pinentry-program-lines-in-gpg-agent-conf-first-wins
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins

## Signature

Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins

## Root Cause

GPG uses the first `pinentry-program` directive it finds. Appending a new line doesn't override earlier ones. Always replace, don't append.

## Resolution

1. Always replace, don't append

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins
- Tip: Best practice: Multiple `pinentry-program` lines in gpg-agent.conf — first
  wins
