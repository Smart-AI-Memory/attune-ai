---
type: faq
name: sbin-is-a-symlink-to-usr-sbin-on-modern-ubuntu
tags: [ci, testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu?

## Answer

`Path("/sbin/init").resolve()` does NOT follow the `/sbin` symlink when the target file doesn't exist (Python 3.10+ `strict=False`). Tests asserting that `/sbin/...` is blocked by path validation fail on Ubuntu CI because the resolved path stays as `/sbin/init` which doesn't match the `/usr/sbin` entry in the blocklist.


**Fix:**

- Use `/usr/sbin/...` directly in tests

```
Path("/sbin/init").resolve()
```

## Related Topics
- **Error**: Detailed error: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu
