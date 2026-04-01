---
type: faq
name: is-private-is-a-superset-in-python-ipaddress
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about is_private is a superset in Python ipaddress?

## Answer

Loopback (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified (`0.0.0.0`) all have `is_private=True`. When checking IP safety, test specific attributes (`is_loopback`, `is_link_local`, etc.) before `is_private` so error messages are precise.

```
), link-local (
```

## Related Topics
- **Error**: Detailed error: `is_private` is a superset in Python `ipaddress`
