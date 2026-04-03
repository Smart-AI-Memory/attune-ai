---
type: task
name: use-planning
tags: [skill, task]
source: plugin/skills/planning/SKILL.md
---

# How to Plan Before You Code

## Quick start

Say what you want to plan:

```
plan a user authentication feature
```

Or use the skill directly:

```
/planning authentication feature with OAuth support
```

You'll get a structured plan with tasks, acceptance
criteria, and risk flags before writing any code.

## The guided flow

When you ask for planning, you'll be guided through
two quick questions before anything runs:

| Step | What you're asked | Why |
|------|-------------------|-----|
| 1. Subject | "What are you planning?" | Names the feature, system, or behavior to plan around |
| 2. Mode | "Feature spec, TDD approach, or architecture review?" | Each mode produces different output and depth |

If you provide both upfront ("plan TDD for the payment
module") the questions are skipped and it runs
immediately.

## Choosing a planning mode

| Mode | What you get | Time | When to use |
|------|-------------|------|-------------|
| **Feature spec** | Goals, scope, tasks, acceptance criteria, risks | ~2-3 min | Starting a new feature or epic |
| **TDD scaffold** | Test-first skeleton with red/green/refactor steps | ~1-2 min | Complex logic that needs tests from day one |
| **Architecture review** | Component analysis, coupling, dependency map | ~2-3 min | Evaluating design before committing |

Natural language works:

- "plan the new billing feature" — feature spec
- "plan TDD for src/auth/" — TDD scaffold
- "review the architecture of the plugin system" —
  architecture review

## Reading the plan

### Feature spec output

```
Feature Plan: User Authentication

Goal
  Allow users to log in with email/password or OAuth.

Scope
  - Email/password login and registration
  - Google and GitHub OAuth providers
  - Session management with JWT tokens

Non-goals
  - Multi-factor authentication (Phase 2)
  - Social login beyond Google/GitHub

Tasks
  1. [2h] Set up auth module structure
     Acceptance: auth/ directory with __init__.py,
     models.py, routes.py
  2. [4h] Implement email/password registration
     Acceptance: POST /register returns 201 with JWT
     Depends on: Task 1
  3. [3h] Implement login endpoint
     Acceptance: POST /login returns JWT for valid creds
     Depends on: Task 2
  4. [4h] Add Google OAuth flow
     Acceptance: GET /auth/google redirects, callback
     creates session
     Depends on: Task 1
  5. [3h] Add GitHub OAuth flow
     Acceptance: Same pattern as Google
     Depends on: Task 4

Risks
  - OAuth callback URL configuration varies per provider
    Mitigation: Document setup per provider in README
  - JWT secret rotation needs a strategy
    Mitigation: Add rotation endpoint in Phase 2

Estimated total: 16 hours
```

### TDD scaffold output

```
TDD Plan: Payment Processing

Red/Green/Refactor Steps

  Step 1 — Red: test_charge_valid_card_returns_success
    Write test asserting successful charge returns
    status="success" and a transaction ID.
    Run: pytest -k test_charge_valid_card (should FAIL)

  Step 2 — Green: implement charge()
    Minimal implementation that passes the test.
    Run: pytest -k test_charge_valid_card (should PASS)

  Step 3 — Red: test_charge_expired_card_raises
    Write test asserting ExpiredCardError for expired
    cards.
    Run: pytest -k test_charge_expired (should FAIL)

  Step 4 — Green: add expiry validation
    Add date check before charging.
    Run: pytest -k test_charge_expired (should PASS)

  Step 5 — Refactor
    Extract validation into _validate_card() helper.
    Run: pytest (all should PASS)
```

## What to do next

After the plan, you'll be offered follow-up options:

| Goal | What to say |
|------|-------------|
| Start implementing | "let's build task 1" |
| Refine the plan | "add more detail to task 3" |
| Switch mode | "now do TDD for the auth module" |
| Turn into a spec | "create a spec from this plan" |
| Review architecture | "review the architecture of this plan" |
| Go deeper | say "tell me more" for the full reference |

## Want to learn more?

- Say **"tell me more"** for the complete reference
  with all planning modes and output format
- Say **"what is planning?"** to go back to the
  overview
- Say **"create a spec"** to turn a plan into a
  spec-driven workflow with approval gates
