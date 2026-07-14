---
name: security-audit
source: content/features/security-audit.md
tags:
- security
- audit
- owasp
- scanning
- cve
type: faq
---

# Security Audit FAQ

## Does security-audit fix the vulnerabilities it finds?

No. It finds and prioritizes them and proposes a
remediation plan; applying fixes is a separate step you take.

## Is there an `attune security-audit` command?

No dedicated subcommand — run it as
`attune workflow run security-audit`, or use the
`/security-audit` skill or the `security_audit` MCP tool.

## Which calls are async?

`execute` is the only public method and it is a
coroutine — `await` it or use `asyncio.run`.

## What does `depth` change?

The agent-turn budget (quick 10, standard 20, deep 40)
and the cost cap; `deep` additionally turns on extended thinking
for richer remediation reasoning.

## Does a clean report mean my code is secure?

No. Findings are LLM predictions, not proofs, and a clean
pass is not a guarantee — use the audit as one input, not a
certification.
