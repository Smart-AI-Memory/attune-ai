---
type: faq
name: new-security-features-need-dedicated-tests-before-release
tags: [testing, security, imports, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about new security features need dedicated tests before release?

## Answer

v5.0.1 shipped with 4 new security controls (rate limiter, ownership checks, module prefix restriction, workspace isolation) — all with zero effective test coverage despite 15,555 tests passing. The deep review caught this after publishing to PyPI.

**How to fix:**
- Run `/deep-review` on changed files BEFORE `/release prep`, not after

```
/deep-review
```

## Related Topics
- **Error**: Detailed error: New security features need dedicated tests before release
