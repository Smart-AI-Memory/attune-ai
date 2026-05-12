# Per-module decisions — Test Quality Program

Append-only log. One section per module as it's worked. See
`requirements.md`, `design.md`, `tasks.md` for the framework.

Format per entry:

```text
## <module path>

**Date:** YYYY-MM-DD
**Rubric score at pick time:** <score> (weight × gap × risk)
**Picked because:** <one-line reasoning>
**Outcome:** <one-line summary — modules touched, bug classes, tests added/removed>
**PR:** <link>
**Bug log entry:** <link to COVERAGE_BUG_LOG.md section>

[Body: what stays, what got rewritten, what got deleted, and
why. Any surfaced production change deferred to a sibling PR.]
```

---

<!-- First entry lands here when task #8 ships. -->
