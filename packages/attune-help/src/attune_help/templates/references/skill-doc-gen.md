---
type: reference
subtype: procedural
name: skill-doc-gen
category: skill
tags: [documentation, skill, plugin, reference]
source: plugin/skills/doc-gen/SKILL.md
---

# Doc Generation Reference

Complete reference for the doc-gen skill -- every doc
type it produces, format options, and how to control
the output.

## Invocation

```
/doc-gen <path>
```

Or natural language:

```
document src/models/
add docstrings to auth.py
generate a README for the cli module
create API docs for the entire project
```

## Doc types

The skill runs on your Claude subscription -- no API key
or additional cost. You choose what kind of documentation
to generate:

| Doc type | What it generates | Best for |
|----------|-------------------|----------|
| **Docstrings** | Google-style per function/class/method | Keeping code self-documenting |
| **README** | Feature list, usage examples, install instructions | Module or project overviews |
| **API reference** | Full signatures with types and descriptions | Library consumers |
| **Module overview** | Architecture summary, dependency map | Onboarding and navigation |
| **Full pipeline** | Audit gaps, generate docs, review coverage | Pre-release documentation sweep |

Set the type with natural language:

```
add docstrings to src/auth/
generate a README for the models package
full documentation audit on src/
```

## Scoping

Before generating, the skill asks:

1. **Target**: "Which file or module needs documentation?"
2. **Format**: "What kind of docs -- docstrings, README,
   API reference, or a full audit?"

## Google-style docstring spec

All generated docstrings follow Google style with these
sections (each included only when applicable):

| Section | When included | Format |
|---------|---------------|--------|
| **Summary** | Always | One-line imperative sentence |
| **Args** | Function has parameters | `name: Description.` per line |
| **Returns** | Function returns a value | Description of return value |
| **Yields** | Generator function | Description of yielded values |
| **Raises** | Function raises exceptions | `ExceptionType: When it happens.` |
| **Example** | Public API functions | `>>> call()` with expected output |
| **Note** | Important caveats exist | Free-form paragraph |

Example of a complete generated docstring:

```python
def create_session(
    user_id: str,
    ttl: int = 3600,
) -> Session:
    """Create an authenticated session for a user.

    Args:
        user_id: Unique identifier for the user.
        ttl: Session lifetime in seconds. Defaults
            to 3600 (one hour).

    Returns:
        A new Session object with a generated token.

    Raises:
        ValueError: If user_id is empty.
        AuthError: If the user account is locked.

    Example:
        >>> session = create_session("user-42")
        >>> session.is_valid()
        True
    """
```

## README generation

When generating a README section for a module, doc-gen
produces:

| Section | Content |
|---------|---------|
| **Module name** | Heading with one-line description |
| **Overview** | What the module does and why it exists |
| **Quick start** | Minimal usage example with imports |
| **Public API** | Table of exported functions/classes |
| **Configuration** | Environment variables or config options |
| **Dependencies** | Required packages and optional extras |

## Output format

Results are presented as a documentation report:

```markdown
## Documentation Report

**Files:** 12 | **Functions Documented:** 34 | **Gaps:** 3

### Generated Docstrings

| File | Function | Status |
|------|----------|--------|
| [session.py:15](src/auth/session.py#L15) | create_session | Added |
| [session.py:42](src/auth/session.py#L42) | validate_token | Updated |
| [session.py:78](src/auth/session.py#L78) | revoke_session | Added |

### Gaps Remaining

| File | Missing |
|------|---------|
| [middleware.py](src/auth/middleware.py) | 2 private helpers |
| [utils.py](src/auth/utils.py) | 1 module docstring |
```

## Source analysis

Doc-gen reads these elements from your code to produce
accurate documentation:

| Source | What it extracts |
|--------|-----------------|
| Function signatures | Parameter names, types, defaults |
| Type hints | Return types, generic parameters |
| Class hierarchies | Inheritance chain, abstract methods |
| Module `__all__` | Public API surface |
| Existing docstrings | Preserves manual docs, fills gaps |
| Decorator metadata | `@property`, `@staticmethod`, etc. |
| Exception handlers | Which exceptions a function raises |

## After generating

| Goal | What to say |
|------|-------------|
| Apply docstrings to files | "apply these to the files" |
| Audit the rest of the project | "audit the whole project for gaps" |
| Generate a README next | "generate a README for this module" |
| Generate API reference | "create API docs for this package" |
| Export as markdown | "export the docs as a markdown file" |

## Want to learn more?

- Say **"what is doc-gen?"** to go back to the overview
- Say **"how do I generate docs?"** for the step-by-step
- Say **"review my code"** for a broader code quality review
- Say **"what is smart-test?"** to generate tests alongside
