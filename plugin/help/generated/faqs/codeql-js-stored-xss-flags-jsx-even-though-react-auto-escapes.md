---
type: faq
name: codeql-js-stored-xss-flags-jsx-even-though-react-auto-escapes
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about codeQL js/stored-xss flags JSX even though React auto-escapes?

## Answer

CodeQL flagged `{tag}` rendered in `<h1>` as stored XSS despite React's automatic text escaping. Defense-in-depth fix: `decodeURIComponent` on input + `encodeURIComponent` on `href` values.

```
 rendered in
```

## Related Topics
- **Error**: Detailed error: CodeQL `js/stored-xss` flags JSX even though React auto-escapes
