---
type: task
name: use-doc-gen
tags: [documentation, skill, task]
source: plugin/skills/doc-gen/SKILL.md
---

# How to Generate Documentation

## Quick start

The fastest way: just say what you want documented.

```
document src/auth/
```

Or use the skill directly:

```
/doc-gen src/auth/
```

You'll get generated documentation shown inline. Nothing
is written to files until you approve it.

## Choosing what to document

You can document a single file, a directory, or your
entire project:

| Command | What it documents |
|---------|-------------------|
| `/doc-gen src/auth.py` | One file -- adds missing docstrings |
| `/doc-gen src/models/` | A directory tree |
| `/doc-gen .` | The whole project |

If you don't specify a path, the skill asks:

> "Which file or module needs documentation?"

## Choosing the doc type

By default, doc-gen generates Google-style docstrings. If
you want something different, say so:

- "add docstrings to src/auth.py" -- docstrings only
- "generate a README for the auth module" -- README section
- "create API docs for src/models/" -- full API reference
- "document everything in src/" -- audit gaps, then generate

Or the skill asks:

> "What kind of docs? Docstrings, README, API reference,
> or a full documentation audit?"

## The guided flow

When you invoke doc-gen, it walks you through:

1. **Target** -- which file or module to document
2. **Format** -- docstrings, README, API reference, or all
3. **Generation** -- reads source, generates docs, shows preview
4. **Review** -- shows the output before writing anything
5. **Apply** -- writes changes only after you approve

## Reviewing the output

Doc-gen shows you everything before changing files. For
docstrings, you'll see the generated content inline:

```
Generated Docstrings (3 functions)

  src/auth/session.py
    create_session()  -- Added Args, Returns, Raises
    validate_token()  -- Added Args, Returns
    revoke_session()  -- Added Args, Raises

Apply these docstrings to the files? [y/n]
```

## What to do next

After reviewing the results:

- **Apply the docs** -- say "yes, apply them" to write
  changes to files
- **Audit the rest** -- say "audit the rest of the project
  for missing docs"
- **Generate a README** -- say "now generate a README for
  this module"
- **Get the full reference** -- say "tell me more" for
  every doc type and format option

## Want to learn more?

- Say **"tell me more"** for the complete reference
- Say **"what is doc-gen?"** to go back to the overview
- Say **"review my code"** to run a code quality review
