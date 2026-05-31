# Spec: Dashboard Tools Inventory Unification — Decisions

**Status:** approved (2026-05-31)

> Pre-committed decisions per the existing lesson "Pre-committed
> decision matrices survive contact with data." Edits to this file
> after v1 ships require a follow-up PR with rationale.

## Context

The ops dashboard's `/workflows` page lists server-runnable workflows
but is silent about **skills** (auto-triggered by natural-language
phrases in Claude Code chat) and **slash commands** (explicit
chat-side invocation). New users who don't know the trigger phrases
never invoke the skill-side capabilities — they're effectively
hidden.

Patrick named the gap 2026-05-31 in architect-mode: skills like
`smart-test` ship real value but are invisible from the visible
surface (the dashboard). Recommendation surfaced in the same
session: unify all three capability types onto one inventory page,
rename it for intent clarity, and add a "Use in chat" copy
affordance so skill-only entries get a one-click bridge to chat.

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Page label | **"Tools"** | Short, intent-clear, doesn't collide with Claude Code's `/commands`. "Workflows" is jargon; "Capabilities" reads corporate; "Actions" is ambiguous. Browser-tab-friendly. |
| URL path | **Keep `/workflows`** | The page's H1 says "Tools", but the URL stays legacy. Bookmarks, external links, and existing docs don't break. Migration is render-only. |
| Inventory scope | **Workflows + skills + slash commands; hooks excluded** | Workflows + skills + commands are user-invoked capabilities. Hooks are event-driven (PreToolUse / SessionStart / Stop) — not "things the user does," so they don't belong in a Tools inventory. Hooks may get a separate "Active enforcements" surface later (the enforcement-vs-documentation framework anticipates this). |
| Discovery sources | **`attune.workflows.list_workflows()` + parse `plugin/skills/*/SKILL.md` frontmatter + parse `plugin/commands/*.md` frontmatter** | Each source is the canonical existing inventory for its type. No new registry needed. Frontmatter parsing reuses the existing `python-frontmatter` dependency. |
| Top-level sectioning | **Group by use-mode: "Run from dashboard" / "Use in chat"** with type-badges inside each section | Matches user intent ("can I run this here?"). Beats top-grouping by type (workflow/skill/command) which would force users to understand the implementation distinction. Type-badges still expose the underlying kind for users who care. |
| Per-entry actions | **Server-runnable: Run button (existing). Skill-only / command-only: "Use in chat" copy-to-clipboard button with the trigger phrase + toast feedback.** | Mirrors the existing `data-copy-report` pattern in `run_view.html`. The button copies the natural-language trigger (skill) or slash command (`/foo`); user pastes into Claude Code chat. Cheap to ship, doesn't fight the chat-side trigger model, preserves the conceptual map. |
| Trigger phrase source for skills | **Parse the "Triggers on:" pattern from the SKILL.md description** when present; fall back to the skill name (e.g. `"smart-test"` → `"smart test for src/"`). | Most SKILL.md descriptions already include "Triggers on:" or "Use this when:" prose. When absent, the skill name itself works as a reasonable trigger phrase for natural-language auto-trigger. |
| Out of scope (v1) | **No invocation bridge** — dashboard does not fire skills directly. **No execution-history merging** — skill-only entries don't show a run history (they don't have one). | Bridging dashboard → embedded Claude Code session would require auth, session lifecycle, and streaming plumbing — a separate spec. v1 ships discovery only. |

## Naming alternatives considered

| Label | Verdict | Reason |
|---|---|---|
| **Tools** | ✅ chosen | Short, intent-clear, no collision |
| "What you can do" | ❌ | Too long for nav; reads instructional |
| "Capabilities" | ❌ | Corporate-jargon feel |
| "Actions" | ❌ | Ambiguous (UI actions? CI actions?) |
| "Tools & shortcuts" | ❌ | Mixed; "shortcuts" overloads keyboard shortcuts |

## Out of scope (parking lot)

- **Bridge invocation**: dashboard fires skills via an embedded Claude
  Code session. Real plumbing project (auth, session lifecycle,
  streaming). Separate spec when prioritized.
- **Inventory of hooks**: PreToolUse / PostToolUse / SessionStart / Stop
  hooks. Event-driven, not user-invoked. The
  enforcement-vs-documentation framework anticipates a separate
  "Active enforcements" surface for hard-blocking hooks (per
  `docs/specs/enforcement-vs-documentation/`).
- **Per-entry detail page**: a deeper `/tools/<name>` page showing
  full description + when-to-use + example. v1 ships the inventory
  only; detail pages later if user feedback supports it.
- **Multi-corpus aggregation**: aggregating tools from sibling packages
  (`attune-author`, `attune-help`, `attune-rag`) into one cross-package
  inventory. v1 is attune-ai-local only.

## Rollback plan

Single PR. Rollback = `git revert <merge-commit>`. The data-layer
addition (`data.list_tools()`) and template extension are additive —
existing `/workflows` route + render still work with just
`list_workflows()` if the inventory parts are removed. The nav label
rename is the only user-visible touch outside the page itself; it
reverts cleanly.

## Carryover

- 2026-05-31 — Decisions captured in the same session as the architect
  conversation that produced them. Patrick approved the recommendation
  ("proceed with your recommendation. it's a good one :)") and chose
  Path 1 (full single-session build inclusive of Phase 3b + Task 7
  after the inventory PR ships).
