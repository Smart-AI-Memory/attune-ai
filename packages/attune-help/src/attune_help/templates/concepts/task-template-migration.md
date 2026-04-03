---
type: concept
name: task-template-migration
tags: [migration, help-system, documentation, templates]
source: developer-guidance
---

# Template Migration

Static documentation rots. README files go stale the week
after someone writes them. Wiki pages accumulate layers of
outdated instructions that nobody trusts enough to follow.
Markdown files sit in a docs folder, disconnected from the
code they describe, silently drifting out of sync.

Template-based help solves this by treating documentation
as structured data rather than prose files. Content is
authored once, rendered per audience, maintained by AI
agents, and improved through usage signals.

## Why static docs fail

Static documentation has a fundamental structural problem:
the person who writes it and the person who reads it have
completely different needs. The writer knows the system
deeply and writes for completeness. The reader wants one
specific answer and has to wade through everything else to
find it.

| Problem | What happens | Why it persists |
|---|---|---|
| **Staleness** | Docs describe last quarter's architecture | Nobody owns maintenance; updates are unpaid work |
| **Audience blindness** | Beginner reads expert-level docs, gives up | One doc serves all readers at one depth |
| **Discovery failure** | User can't find the doc that answers their question | No connection between user intent and doc location |
| **Maintenance burden** | Keeping docs current is a full-time job nobody has | Manual maintenance doesn't scale with code velocity |
| **No feedback loop** | Nobody knows which docs are read, which are wrong | Static files have no usage telemetry |
| **Depth mismatch** | User needs a quickstart, gets a 50-page reference | No progressive depth; all content at one level |

## What template-based help changes

Templates restructure documentation around how people
actually learn: start shallow, go deeper when needed,
get different content depending on what you already know.

| Capability | Static docs | Template-based help |
|---|---|---|
| **Freshness** | Decays from the moment of writing | AI agents detect drift and update automatically |
| **Audience awareness** | One version for everyone | Concepts for beginners, references for experts, tasks for doers |
| **Maintenance effort** | Manual, ongoing, untracked | Automated staleness detection, AI-assisted updates |
| **Discoverability** | Search or browse a file tree | Cross-links, tag-based routing, intent matching |
| **Progressive depth** | Scroll through everything or nothing | Quickstart (2 min) to concept to task to full reference |
| **Feedback loop** | None -- docs are write-only | Usage tracking shows what's read, what's skipped, what's missing |
| **Consistency** | Every author writes differently | Templates enforce structure; content varies, shape doesn't |
| **Cross-referencing** | Manual links that break on rename | Automatic cross-links generated from tags and names |

## The four template types

Every topic in a template-based help system is expressed
through four perspectives, each serving a different reader
need:

| Template type | Reader need | Depth | Example title |
|---|---|---|---|
| **Concept** | "What is this and why should I care?" | Understanding the idea | "Template Migration" (this page) |
| **Task** | "Walk me through doing it step by step" | Guided execution | "How to Migrate Your Docs to Templates" |
| **Reference** | "Show me all the details and edge cases" | Complete lookup | "Migration Decision Matrix and Patterns" |
| **Quickstart** | "I need to do this in 5 minutes" | Minimum viable action | "Move Your First Doc to a Template" |

A reader asking "what is template migration?" gets the
concept. A reader asking "how do I migrate my docs?" gets
the task. A reader asking "what template type should my
FAQ page become?" gets the reference. A reader saying
"just get me started" gets the quickstart.

## What you gain

- **Progressive depth**: Users start with a quickstart and
  drill deeper only when they need to. No more "read this
  entire 200-line doc before you can do anything."
- **Audience adaptation**: The same topic is explained four
  different ways. Beginners and experts both find what they
  need without wading through content meant for the other.
- **Precursor warnings**: Cross-links surface prerequisites
  before a user hits a wall. "Before migrating templates,
  understand how cross-linking works."
- **Self-maintenance**: AI agents scan templates for
  staleness, detect when code changes invalidate content,
  and flag or fix drift automatically.
- **Usage-driven improvement**: Telemetry shows which
  templates are read, which are skipped, and where users
  ask follow-up questions -- pointing directly at gaps.

## What it costs

Template migration is not free. The upfront investment
is real:

| Cost | Magnitude | Payoff timeline |
|---|---|---|
| **Auditing existing docs** | Hours to days depending on doc volume | Immediate clarity on what exists |
| **Learning template structure** | 30 minutes to understand the four types | Permanent; applies to every future doc |
| **Converting first doc** | 1-2 hours for a pilot conversion | Same day; proves the pattern works |
| **Building cross-links** | Minutes per template (tags do most of the work) | Compounds as more templates are added |
| **Ongoing structuring** | 10-15 min per new topic (vs unstructured writing) | Each new template is faster than the last |

The break-even point is typically 5-10 templates. After
that, the system maintains itself better than static docs
ever could.

## Want to learn more?

- Say **"how do I migrate my docs to templates?"** for the
  step-by-step migration guide
- Say **"show me the migration reference"** for the
  decision matrix, audit checklist, and common mistakes
- Say **"I need to move my docs to templates"** for the
  5-minute quickstart
- Ask **"/doc-gen"** to generate template stubs from
  existing source code
- Ask **"/help"** to browse all available help templates
  and see the system in action
