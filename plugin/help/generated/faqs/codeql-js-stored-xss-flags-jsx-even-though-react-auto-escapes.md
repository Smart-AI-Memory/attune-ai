---
name: codeql-js-stored-xss-flags-jsx-even-though-react-auto-escapes
source: .claude/CLAUDE.md
summary: This template explains why CodeQL's `js/stored-xss` query flags potentially
  unsafe JSX expressions in React components despite React's automatic escaping, and
  recommends applying defense-in-depth sanitization practices to satisfy static analysis
  while securing against XSS vulnerabilities.
tags:
- testing
- git
type: faq
---

# FAQ: Why Does CodeQL Flag `js/stored-xss` in JSX When React Auto-Escapes?

## Answer

CodeQL's `js/stored-xss` query may flag JSX expressions such as `{tag}` rendered inside elements like `<h1>`, even though React automatically escapes text content. This happens because CodeQL performs static taint analysis and cannot always determine at analysis time that a given value will be safely escaped at runtime.

### Why the Flag Occurs

CodeQL tracks data flow from untrusted sources (such as user-supplied input retrieved from a database or URL) through to potentially dangerous sinks. When it detects that unsanitized data reaches a rendered JSX expression, it raises a `js/stored-xss` alert — regardless of whether React's runtime escaping would ultimately prevent exploitation.

### Recommended Fix

Apply a **defense-in-depth** approach by sanitizing data at both the input and output boundaries:

- **Decode input defensively** — use `decodeURIComponent` when reading user-supplied values.
- **Encode output explicitly** — use `encodeURIComponent` when constructing `href` or other attribute values.

This ensures that even if CodeQL's taint analysis follows the data through multiple transformations, the explicit sanitization calls serve as recognizable safe guards that the analyzer can reason about.

```jsx
// Before — may trigger js/stored-xss
const tag = getUserInput();
return <h1>{tag}</h1>;

// After — defense-in-depth sanitization
const raw = getUserInput();
const tag = decodeURIComponent(encodeURIComponent(raw)); // normalize input
const safeHref = encodeURIComponent(raw);               // encode for use in URLs
return (
  <h1>{tag}</h1>
);
```

> **Note:** If your code uses `dangerouslySetInnerHTML`, React's automatic escaping is bypassed entirely and the CodeQL alert is a genuine risk. Ensure such usage is explicitly reviewed and sanitized with a library such as [DOMPurify](https://github.com/cure53/DOMPurify).

---

## Related Topics

- **Error:** CodeQL `js/stored-xss` flags JSX even though React auto-escapes
