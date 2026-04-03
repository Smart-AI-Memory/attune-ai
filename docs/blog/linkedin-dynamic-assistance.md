# Help That Knows Who's Reading and What's Coming

*Part 4 of a series on building living documentation
with Claude Code*

Part 3 covered the 11 template types — the building
blocks. This article is about what makes those templates
come alive: context awareness.

A static help system shows the same content to everyone,
every time. A dynamic one adapts to who's asking, where
they are in their learning, and what's about to go wrong
in their code. Here's how Attune AI does each of those.

## Audience Adaptation: One Template, Three Outputs

Every template in the system is a single markdown file
with YAML frontmatter. But the same template renders
differently depending on who's reading.

**Claude Code** — The user is mid-conversation with an
AI assistant. Context window matters. The renderer
strips verbose sections, truncates explanations to ~500
characters, and appends tool hints like "Run
code_review() to investigate further." Concise, because
the user can always ask a follow-up.

**CLI terminal** — The user ran `attune help` in their
terminal. The renderer produces Rich-formatted panels
with colored titles — red for errors, yellow for
warnings, green for tips. Falls back to plain ASCII if
Rich isn't installed. Designed for scanning, not
reading.

**Marketplace** — The template is being published to a
static docs site. The renderer preserves the full
untruncated body, includes YAML frontmatter for site
generators, and adds "See Also" links with template IDs.
Complete, because the reader has no way to ask
follow-ups.

The key: no content is rewritten between audiences. The
renderers apply strategic inclusion, exclusion, and
formatting to the same source. The concept explanation
for "audience adaptation" is the same three sentences
whether you read it in Claude Code or on a docs site —
just presented differently.

## Precursor Warnings: Help Before You Need It

Most help systems wait for you to ask. Precursor
warnings don't wait.

When you're editing a Python file, the help engine maps
the `.py` extension to relevant tags — python, imports,
testing. It searches the template index for warnings and
errors tagged with those keywords and surfaces the top
matches proactively.

--- CODE START ---
Editing: src/attune/config/__init__.py

Precursor warnings:
  - Adding logger before eager imports triggers E402
  - config.py alongside config/ creates duplicate module
  - Pre-commit stash conflicts with auto-fix hooks
--- CODE END ---

These aren't random tips. They're warnings generated
from real bugs the project has hit before — each one
linked to a Lessons Learned entry with the root cause
and fix. The system surfaces them because the file
you're editing matches the pattern that caused the
problem.

The mapping is simple — file extensions to tags:

- `.py` files trigger python, imports, testing tags
- `.yml`/`.yaml` trigger CI tags
- `.json`/`.toml` trigger packaging tags

Simple, but effective. You see the warning while you're
in the file where the problem happens, not after you've
already broken something.

## Progressive Depth: Session State That Learns

Parts 1-3 introduced "tell me more" — the three-level
escalation from concept to task to reference. Here's
how the session state behind it works.

A small JSON file tracks three things:

--- CODE START ---
{
  "last_topic": "security-audit",
  "depth_level": 1,
  "timestamp": 1743580800
}
--- CODE END ---

**Depth escalation:** Ask about "security audit" and
you get the concept (level 0). Ask again — or say
"tell me more" — and depth increments to 1 (task
template). Once more and you're at level 2 (reference).

**Topic switching:** Ask about a different topic and
depth resets to 0. You start fresh because you're
learning something new.

**4-hour TTL:** If more than 4 hours pass between
requests, the session resets. You probably forgot where
you were, so the system doesn't assume continuity.

**Crash safety:** The file is written via atomic rename
— write to a temp file, then move it into place. No
half-written state if the process dies.

This is intentionally simple. Three fields, one file,
clear rules. The complexity is in the template
cross-links that progressive depth follows, not in the
session tracking itself.

## Four Modes of help_lookup

The help MCP tool supports four modes, each for a
different context:

**Progressive** (default) — The "tell me more" flow.
Concept on first call, task on second, reference on
third. Falls back to verbosity-based rendering if
type-specific templates don't exist for the topic.

**Workflow help** — Post-execution tips. After running
a security audit, the engine maps the workflow name to
relevant templates and returns compact suggestions for
what to do next.

**Precursor** — File-based warnings as described above.
Takes a file path, maps the extension to tags, returns
matching warnings and errors.

**Search by tag** — Find templates by keyword. Optionally
sorted by usage frequency so high-impact templates
surface first.

## Usage Telemetry: Docs That Know What Matters

The maintenance pipeline (covered in Part 5) needs to
decide which templates to regenerate first. It can't
regenerate all 557 at once — that would be expensive
and slow.

The answer: usage weighting.

Every workflow run is tracked with its LLM cost. The
system normalizes costs to a 0-1 range and maps
workflows to their related templates via cross-links.
Templates linked to expensive, frequently-used workflows
get higher maintenance priority.

The result: the security audit reference template (linked
to a workflow people run daily) gets regenerated before
the comparison template for two features nobody uses.
The knowledge base maintains itself based on what
actually matters to users.

## The Design Principle

All four features — audience adaptation, precursor
warnings, progressive depth, and usage weighting — share
one principle: **the help system adapts to context
without asking the user to configure anything.**

- Your audience is detected, not selected
- Warnings are surfaced, not searched for
- Depth escalates, not navigates
- Priority is measured, not assigned

Zero configuration. The system observes context and
responds accordingly.

## Try It

--- CODE START ---
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
--- CODE END ---

- "what is security audit?" — progressive depth (concept)
- "tell me more" — escalates to task, then reference
- Edit a .py file and ask for help — precursor warnings

The entire help system runs on your Claude subscription
— no API key required.

This is part 4 of a series on building knowledge bases,
help systems, dynamic assistance, and context-aware
documents with Claude Code and MCP.

If you find it useful, a star on the repo helps others
discover the project:
github.com/Smart-AI-Memory/attune-ai

Next up: Building a knowledge base that maintains itself
— the 5-phase maintenance pipeline.
