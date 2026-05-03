---
name: use-coach
source: plugin/skills/coach/SKILL.md
summary: This developer help template covers a progressive coaching skill that advances
  users through three levels of depth (concept, procedural, reference) on topics like
  security audits, code reviews, and testing, triggered by specific keywords and invoked
  via the `/coach` command with automatic progression on repeat requests.
tags:
- skill
- task
type: task
---

# Use the Coach Skill

Progressive help for any topic. Each time you invoke the coach, it advances one level deeper: **concept → procedural → reference**. Repeat to go deeper.

**Triggers:** `coach`, `explain`, `tell me more`, `how does`, `what is`, `help with`, `deeper`

**Invoke with:** `/coach <topic>`

---

## Steps

### 1. User provides a topic

Call `help_lookup` with the matching topic slug. The engine resolves the correct template type at each level automatically.

```
help_lookup(topic="<topic>", mode="progressive")
```

**Topic slug reference:**

| User says | Topic slug |
|---|---|
| security audit | `security-audit` |
| code review | `code-review` |
| code quality | `code-quality` |
| bug predict | `bug-predict` |
| test gen | `test-generation` |
| release | `release-prep` |
| refactor | `refactor-plan` |
| doc gen | `doc-gen` |

---

### 2. User says "tell me more" or "go deeper"

No new topic needed. Call `help_lookup` with the **same topic** — it auto-advances to the next level.

```
help_lookup(topic="<topic>", mode="progressive")
```

---

### 3. User says "start from the beginning" or "reset"

Restart the progression from the concept level.

```
help_lookup(topic="<topic>", mode="progressive", reset=true)
```

---

### 4. User just finished a workflow

Skip the concept level and start at procedural.

```
help_lookup(
  topic="<topic>",
  mode="progressive",
  last_workflow="<workflow-name>"
)
```

---

### 5. User has file-based warnings

Look up help scoped to a specific file.

```
help_lookup(
  topic="warnings",
  mode="precursor",
  file_path="<path-to-file>"
)
```

---

## Related Topics

- **Reference:** Skill: coach — full reference
