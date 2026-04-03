---
type: concept
name: tool-doc-gen
tags: [documentation, docstrings, readme]
source: plugin/skills/doc-gen/SKILL.md
---

# Doc Generation

Doc-gen reads your actual source code -- function signatures,
type hints, class hierarchies, module structure -- and generates
documentation from it. Instead of writing docstrings by hand
or letting them drift from the code, you get accurate docs that
reflect the current API.

## What it generates

| Doc type | What you get | Source |
|----------|-------------|--------|
| **Docstrings** | Google-style with Args, Returns, Raises, Examples | Function signatures and type hints |
| **README sections** | Feature lists, usage examples, install instructions | Module exports and public API |
| **API reference** | Full function/class signatures with descriptions | All public symbols in a module |
| **Module overview** | Architecture summary, dependency map, entry points | Package structure and imports |

## When you'd use it

Run doc-gen after creating new public APIs, before a release
to refresh stale docs, when onboarding contributors who need
to understand a module, or when you inherit a codebase with
missing docstrings. It reads the source of truth so the docs
never contradict the code.

## How it works

Doc-gen is a Socratic skill. It asks you two questions before
generating anything:

1. **What to document** -- a single file, a module, or a
   directory tree
2. **What format** -- docstrings, README, API reference, or
   a full pipeline that audits gaps and generates docs for
   all of them

Then it reads the source, generates the documentation, and
shows you the result before applying changes.

## Example output

A generated Google-style docstring looks like this:

```python
def validate_email(email: str) -> bool:
    """Validate email format using regex.

    Args:
        email: Email address to validate.

    Returns:
        True if email matches a valid format,
        False otherwise.

    Raises:
        TypeError: If email is not a string.

    Example:
        >>> validate_email("user@example.com")
        True
    """
```

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is code quality?"** for a broader code review
- Say **"what is smart-test?"** to generate tests alongside docs
