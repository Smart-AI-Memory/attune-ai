---
type: faq
name: background-processes-from-previous-sessions-persist-across
source: .claude/CLAUDE.md
---

# FAQ: What should I know about background processes from previous sessions persist across restarts?

## Answer

Long-running processes started by Claude (e.g. `npm run dev`) survive session end and keep running silently.

**How to fix:**
- Always `kill` them explicitly when removing a feature, and check `ps aux` if unexpected behavior is observed (Chrome tabs opening, ports already in use, etc.)

```
npm run dev
```

## Related Topics
- **Error**: Detailed error: Background processes from previous sessions persist across
  restarts
