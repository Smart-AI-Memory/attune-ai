---
type: task
name: task-precursor-warning-design
tags: [precursor, warnings, help-system, patterns]
source: developer-guidance
---

# How to Add a Precursor Warning

Add a proactive warning that surfaces when a developer
edits a file, before they make a common mistake. This
guide walks through the full process using a concrete
example: warning about `.env` files and secrets in
source control.

## Prerequisites

- Familiarity with the help template format (YAML
  frontmatter + markdown body)
- A common mistake you have seen developers make
  (ideally from Lessons Learned or repeated support
  requests)

## Steps

### 1. Identify the mistake and its trigger

Start from the mistake, then work backward to the file
that was being edited when it happened.

| Question | Example answer |
|----------|---------------|
| What goes wrong? | Secrets committed to git |
| What file were they editing? | `.env` |
| What extension is that? | `.env` (no standard extension) |
| What filename is it? | `.env`, `.env.local`, `.env.example` |
| Is there an existing tag? | `secrets`, `config` |

The trigger is the file; the tags are the bridge to
your template.

### 2. Check the existing maps

Look at `engine.py:precursor_warnings()` to see if the
extension or filename already has tags:

```python
# Extension map (engine.py)
ext_map = {
    ".env": ["config", "secrets"],
    # ...
}

# Filename map (engine.py)
name_map = {
    ".env": ["config", "secrets"],
    ".env.example": ["config", "secrets"],
    # ...
}
```

If `.env` already maps to `["config", "secrets"]`, you
do not need to modify the maps. If your trigger file is
not in either map, add it (see step 6).

### 3. Write the warning template

Create a new file in the appropriate template directory.
For a warning, use the `warnings/` directory:

```
templates/warnings/env-secrets-in-source-control.md
```

Use standard frontmatter:

```yaml
---
type: warning
name: env-secrets-in-source-control
tags: [config, secrets, git]
source: developer-guidance
---
```

Write the body in a direct, advisory tone:

```markdown
# Warning: Secrets in source control

`.env` files contain secrets (API keys, database
passwords, tokens). If committed to git, those secrets
are in the repository history permanently -- even after
the file is deleted.

## Before you edit this file

- Verify `.env` is in `.gitignore`
- Never put production secrets in `.env.example`
- Use placeholder values in examples:
  `SECRET_KEY=change-me-in-production`

## If you already committed secrets

1. Rotate the exposed credentials immediately
2. Add `.env` to `.gitignore`
3. Remove from git tracking:
   `git rm --cached .env`
```

### 4. Wire the tags

Your template's `tags` must overlap with the tags
assigned by the extension or filename map. The
`tag_index` in `cross_links.json` connects them.

For the `.env` example:

- Extension map assigns: `config`, `secrets`
- Your template has tags: `config`, `secrets`, `git`
- Overlap: `config` and `secrets` (2 matches = score 2)

The more tags overlap, the higher the template scores
and the more likely it surfaces.

### 5. Test that your warning surfaces

Use the `HelpEngine.precursor_warnings()` method
directly:

```python
from attune_help import HelpEngine

engine = HelpEngine()
warnings = engine.precursor_warnings(".env")
for w in warnings:
    print(w)
    print("---")
```

Verify your warning appears in the output. If it does
not:

- Check that your template tags match at least one tag
  in the extension or filename map
- Check that your template file is in the correct
  directory
- Check that `cross_links.json` includes your template
  in the `tag_index` (it may need regeneration)

### 6. Add new file mappings (if needed)

If your trigger file uses an extension or filename not
already in the maps, add it to `engine.py`:

```python
# In precursor_warnings(), ext_map:
ext_map = {
    # ... existing entries ...
    ".tf": ["infrastructure", "terraform"],
}

# Or in name_map:
name_map = {
    # ... existing entries ...
    "terraform.tfvars": ["infrastructure", "secrets"],
}
```

Choose tags that are specific enough to avoid noise but
general enough to match multiple related templates.

### 7. Consider task-category templates

If your warning covers a broader topic (not just "don't
do X" but "here's how to do it right"), create a full
task-category set:

| File | Purpose |
|------|---------|
| `concepts/task-your-topic.md` | Why this matters |
| `tasks/task-your-topic.md` | How to do it step-by-step |
| `references/task-your-topic.md` | All patterns and rules |
| `quickstarts/task-your-topic.md` | 5-step minimal guide |

Task-category templates get a +10 scoring boost over
plain warnings, so they surface first when tags match.

## Verification

After adding your warning:

- [ ] Template has correct frontmatter (`type`, `name`,
      `tags`, `source`)
- [ ] Tags overlap with at least one extension or
      filename map entry
- [ ] `precursor_warnings()` returns your template for
      the target file
- [ ] Warning text is advisory (not diagnostic) -- it
      assumes the user has not made the mistake yet
- [ ] Body includes both prevention steps and recovery
      steps

## Want to learn more?

- Say **"what are precursor warnings?"** for the design
  principles and trigger chain
- Say **"show me all the mappings"** for the complete
  file-to-tag and scoring reference
- Say **"I need to add a proactive warning"** for a
  5-step quickstart

## Related Topics

- **Concept**: Precursor warning design -- why proactive
  warnings beat reactive errors
- **Reference**: Precursor warning design -- all file
  mappings, tag conventions, template prefixes, and
  scoring rules
- **Quickstart**: Precursor warning design -- 5-step
  guide to add a proactive warning
