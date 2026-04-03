# A Knowledge Base That Maintains Itself

*Part 5 of a series on building living documentation
with Claude Code*

This is the article I've been building toward. Parts 1-4
covered the help system UX, the code conventions that
make generation possible, the 11 template types, and the
context-aware delivery layer. This one covers the part
that holds it all together: automated maintenance.

557 templates across 11 types is a lot of content. If
maintaining it required manual effort, it would rot just
like any other documentation. The entire premise of this
series — that code is the source of truth — only works
if the system can detect when code changes and
regenerate the affected templates automatically.

Here's how the 5-phase maintenance pipeline does it.

## Phase 1: Detect

Every template tracks which source file it was generated
from. A manifest file maps template IDs to source paths
and SHA-256 hashes:

--- CODE START ---
{
  "err-adding-logger-triggers-e402": {
    "source": ".claude/CLAUDE.md",
    "hash": "a3f8c1...",
    "generated_at": "2026-04-01T12:00:00"
  }
}
--- CODE END ---

Detection is a hash comparison. Load the manifest, hash
the current source files, compare. If the hash changed,
the template is stale.

This runs in seconds because it's just file hashing —
no LLM calls, no network requests.

## Phase 2: Map

A source file can produce multiple templates. CLAUDE.md's
Lessons Learned section alone generates dozens of error,
warning, and FAQ templates. When CLAUDE.md changes, the
pipeline identifies every template type that depends on
it.

The mapping is deterministic — each generator script
declares which sources it reads. Changed source plus
generator script equals stale template type.

## Phase 3: Regenerate

This is where the LLM comes in. Each template type has
its own generator script that parses source files,
extracts structured content, and produces templates.

Two modes:

**Immediate** — Run the generator scripts directly. Fast,
synchronous, uses standard API pricing.

**Batch** — Submit generator requests to Anthropic's
Batch API. 50% cost savings, but results arrive
asynchronously (up to 24 hours). Ideal for large-scale
regeneration where you don't need the results
immediately.

The choice isn't all-or-nothing. You can regenerate
urgent templates immediately and batch the rest.

**Prioritization matters.** Not all stale templates are
equally important. The pipeline sorts them:

1. Low-confidence templates first — ones with poor
   feedback ratings need fixing most urgently
2. High-usage templates next — templates linked to
   workflows people run daily matter more than templates
   nobody reads
3. Then by age — older staleness gets addressed before
   recent changes

This means the security audit reference template (linked
to a workflow used daily, with high user feedback) gets
regenerated before a comparison template for two
features nobody uses. The knowledge base triages itself.

## Phase 4: Rebuild Cross-Links

After templates are regenerated, the relationships
between them need updating. A cross-link builder scans
all templates and applies seven deterministic rules:

- Error links to the warning with the same slug
- Skill references link to the tools mentioned in the
  skill body
- Errors link to tips with 2+ overlapping title words
- Tasks link to references by naming convention
- FAQs link to errors by slug matching
- Notes link to references by keyword overlap
- Everything gets indexed by tag

The output is a single JSON file — no manual
cross-referencing. When a new error template is
generated, it automatically links to its matching
warning, related FAQ, and relevant tips.

This is what makes progressive depth work across
regeneration cycles. The concept -> task -> reference
chain is rebuilt every time, so "tell me more" always
follows the right path even after templates change.

## Phase 5: Validate

The final phase runs every generator in check mode.
Instead of writing files, it compares what would be
generated against what exists on disk.

If everything matches, the pipeline is clean. If
something is out of sync — a template was manually
edited, a generator was updated, or a source file
changed after regeneration — the validator flags it.

This also runs as a pre-commit hook, so stale templates
can't be committed without regeneration.

## The MCP Tool

The entire pipeline is exposed as a single MCP tool:
`help_maintain`. Two flags:

- **dry_run** — report which templates are stale without
  regenerating anything. Good for understanding scope
  before committing to a regeneration run.
- **batch** — use the Batch API for 50% cost savings.
  Results arrive asynchronously.

In Claude Code, you can say "check for stale docs" and
the tool runs in dry-run mode. Say "update help
templates" and it regenerates.

## The Economics

At standard API pricing, regenerating all 557 templates
would be expensive and unnecessary. The pipeline's
design makes this practical:

- **Incremental** — only regenerate stale templates,
  not all 557
- **Prioritized** — high-impact templates first
- **Batch-eligible** — 50% cost reduction for
  non-urgent updates
- **Hash-based detection** — no LLM calls just to check
  staleness

In practice, a typical code change stales a handful of
templates. The pipeline regenerates those in seconds at
minimal cost. Full regeneration is rare and can be
batched overnight.

## The Full Picture

Zooming out across all five articles:

1. **Code conventions** (Part 2) give you structured
   sources — docstrings, type hints, frontmatter, class
   attributes, CLI strings
2. **11 template types** (Part 3) organize those sources
   into purpose-specific help content
3. **Context awareness** (Part 4) delivers the right
   template to the right audience at the right depth
4. **Automated maintenance** (this article) keeps
   everything in sync with the code

The result: a knowledge base you author once, that
adapts to readers, and that maintains itself when the
code changes. No manual doc updates, no sync tickets,
no drift.

## What's Next

This series covered building a help system for your own
project. But there's a bigger idea here: what if you
could use the full authoring toolkit during development,
then ship just the lightweight help runtime to your
users?

That's what we're exploring next — a lean
`attune-help` package that gives any AI app progressive
depth, audience adaptation, and "tell me more" without
shipping 18 workflows and 38 MCP tools. Author with
`attune-ai`, ship with `attune-help`.

More on that soon.

## Try It

--- CODE START ---
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
--- CODE END ---

Say "check for stale docs" to see the maintenance
pipeline in dry-run mode. Say "tell me more" to
experience the help system it maintains.

The entire help system runs on your Claude subscription
— no API key required.

Open source (Apache 2.0):
github.com/Smart-AI-Memory/attune-ai

If you've been following this series, thank you. If you
find Attune useful, a star on the repo helps others
discover the project.

Questions, feedback, or your own approach to living
docs? I'd love to hear from you.
