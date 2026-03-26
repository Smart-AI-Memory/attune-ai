# /spec: Spec-Driven Development for Claude Code

*Attune AI v5.3.0 — March 2026*

---

## What Is /spec?

`/spec` is a new command that brings structured
development workflows to Claude Code. Instead of
describing a feature and hoping the AI gets it right,
`/spec` walks you through a four-stage lifecycle:

1. **Brainstorm** — Scope the problem with guided
   questions
2. **Plan** — Decompose into tasks with files,
   validation, and risks
3. **Review** — Approve the plan before any code is
   written
4. **Execute** — Implement task-by-task with quality
   gates and approval

## Getting Started

```bash
pip install 'attune-ai[developer]'
attune setup
```

In Claude Code:

```
/spec add user authentication with JWT tokens
```

Or start without arguments for the full menu:

```
/spec
```

This offers four options:

- **Start a new spec** — brainstorm from scratch
- **Resume an in-progress spec** — pick up where you
  left off
- **Import a spec file** — load from another project
- **Execute a spec** — review and run an existing plan

---

## Brainstorm Stage

`/spec` uses Socratic discovery — it asks before it acts.
The brainstorm captures four things:

| Element | Question |
|---------|----------|
| **Context** | What's the current state of the system? |
| **Problem** | What problem are you solving? |
| **Goals** | What are the specific deliverables? |
| **End State** | What does success look like? |

This produces a structured brief that feeds directly into
the plan stage.

---

## Plan Stage

From the brainstorm, `/spec` generates a plan file saved
to `.claude/plans/`. Each task is an XML block:

```xml
<task id="1" name="jwt-auth-core">
  <objective>
    Create JWT token generation and validation with
    configurable expiry and refresh support
  </objective>

  <files-to-create>
    <file path="src/auth/jwt.py">
      JWTManager class with create_token(),
      validate_token(), and refresh_token()
    </file>
    <file path="tests/auth/test_jwt.py">
      Tests for token creation, validation, expiry,
      and refresh flows
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/auth/__init__.py">
      <change location="exports">
        Add JWTManager to public exports
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Token round-trips through create/validate</check>
    <check>Expired tokens are rejected</check>
    <check>Refresh tokens generate new access tokens</check>
  </validation>

  <risks>
    <risk severity="medium">
      Secret key rotation requires invalidating all
      existing tokens
    </risk>
  </risks>
</task>
```

Each task is self-contained — it has everything needed
to implement and verify the work. No ambiguity about
which files to touch or how to check correctness.

---

## Review Stage

Before any code is written, you see the full plan as a
table:

```
| Status | ID | Name           | Objective                    |
|--------|----|----------------|------------------------------|
| ...    | 1  | jwt-auth-core  | Token generation & validation|
| ...    | 2  | middleware     | FastAPI auth middleware       |
| ...    | 3  | user-model     | User model with hashed pass  |
| ...    | 4  | login-endpoint | POST /auth/login endpoint    |
| ...    | 5  | protected-route| Decorator for auth-required  |

Approve this plan?
```

For each task you can:

- **Approve** — proceed as planned
- **Edit** — modify scope, files, or validation
- **Reject** — remove from the plan

You can also drill into any task for the full detail view
showing files, validation checks, and risks.

---

## Execute Stage

Execution proceeds one task at a time. After each task:

1. Code is implemented (files created/modified)
2. Quality gates run automatically:
   - Linting (ruff)
   - Security scan (bandit)
   - Tests (pytest on affected files)
3. You see the result with a severity score

### Severity-Gated Approval

The approval step adapts to the quality gate result:

**HIGH severity (score < 50):**

- Fix and retry
- Acknowledge risk (explicit opt-in)

Auto-run is NOT available for high-severity findings.

**MEDIUM/LOW severity (score >= 50):**

- Approve
- Redo
- Auto-run remaining (skip approval for rest)

This means you can trust auto-run — it will still stop
on anything serious.

### Progress Tracking

```
[=========>          ] 2/5 tasks

Task 3/5: user-model [>>>]

Quality gate: 92/100
  Tests: 6/6 passing
  Lint: clean
  Security: no findings

[Approve] [Redo] [Auto-run remaining]
```

---

## Resume Support

Close Claude Code mid-spec? No problem. State is
persisted inside the plan file as an HTML comment:

```html
<!-- spec-state: {"completed":["1","2"],"current":"3"} -->
```

Next time you open Claude Code:

```
/spec resume
```

Or just `/spec` — it detects incomplete plans and offers
to resume automatically.

The state comment is invisible in rendered markdown,
ignored by the task parser, and tracked by git. No
external database, no session state to lose.

---

## Importing Specs

Have a plan from another project or tool? Import it:

```
/spec import path/to/plan.md
```

The file is copied to `.claude/plans/` and parsed for
`<task>` blocks. If tasks are found, you go straight to
the review stage.

This also works for specs shared between team members —
one person writes the plan, others execute it.

---

## Tips

**Start small.** Your first spec should be 3-5 tasks.
Get comfortable with the lifecycle before tackling 15-task
refactors.

**Use the validation checks.** The `<validation>` section
isn't just documentation — quality gates run these checks.
Specific, testable checks produce better results.

**Tag your risks.** The `<risks>` section with severity
tags (`low`, `medium`, `high`) helps the quality gate
calibrate. A task with a `high` risk gets stricter review.

**Let it resume.** Don't try to finish a spec in one
session. The resume support is designed for multi-session
work — start a refactor today, finish it tomorrow.

---

## What's Next

`/spec` is the foundation for several planned features:

- **Spec templates** — pre-built specs for common tasks
  (API endpoint, React component, database migration)
- **Team specs** — shared specs with role-based task
  assignment
- **CI integration** — run specs in CI for automated
  refactoring and migration

---

## Install

```bash
pip install 'attune-ai[developer]'
attune setup
```

Then type `/spec` in Claude Code.

[Full documentation](https://smartaimemory.com/framework-docs/) |
[GitHub](https://github.com/Smart-AI-Memory/attune-ai) |
[PyPI](https://pypi.org/project/attune-ai/)
