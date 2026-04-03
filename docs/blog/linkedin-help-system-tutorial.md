# We Built a Help System That Maintains Itself

Static docs rot. We all know it. The README goes stale
the moment you merge. Help pages don't know if you're a
beginner or an expert. Nobody maintains them — and it
shows.

I spent the last few months building a different approach
with Attune AI, and I think it's worth sharing what I
learned.

**The problem in one sentence:** Documentation is written
once and abandoned, but the code it describes changes
every week.

**The idea:** What if documentation was authored as
templates, rendered at runtime with audience awareness,
maintained automatically by AI agents, and learned from
based on how people actually use it?

Here's how it works in practice.

## "Tell me more" — help that meets you where you are

Ask about any topic and the system starts with a concept
overview — "what is this and when would I use it?" Then
say "tell me more" and it escalates to a step-by-step
task guide. Say it again and you get the full reference
with edge cases, configuration details, and related
topics.

--- CODE START ---
You:    "what is security audit?"
Attune: [concept — what it is, when to use it]
        (say "tell me more" for step-by-step)

You:    "tell me more" (for procedural help)
Attune: [task — how to run it, options, examples]
        (say "tell me more" for full reference)

You:    "tell me more"
Attune: [reference — edge cases, config, related tools]
--- CODE END ---

No menus, no navigation, no searching through a docs
site. Just a short phrase that takes you deeper. Session
state tracks where you are with a 4-hour TTL — you don't
have to remember what you've read.

## Audience adaptation — one source, three outputs

The same template renders differently for Claude Code
users, CLI users, and marketplace readers. Claude Code
gets concise tool hints. CLI gets rich-formatted panels.
The marketplace gets full markdown. You write once; the
system adapts.

## Self-maintaining docs — the part that surprised me

A 5-phase maintenance workflow runs automatically:

1. Detect which source files changed
2. Map changes to affected templates
3. Regenerate stale templates (via Anthropic's Batch API
   at 50% cost)
4. Rebuild cross-links between related topics
5. Validate everything is in sync

The key insight: usage telemetry weights the priority
queue. Templates that help people more get maintained
first. Templates nobody reads get deprioritized. The
knowledge base optimizes itself.

## The scale

557 templates across 11 types — errors, warnings, tips,
references, tasks, FAQs, notes, quickstarts, concepts,
troubleshooting, and comparisons. Each has structured
frontmatter, tags, confidence scores, and cross-links.
The whole thing is powered by 18 multi-agent workflows
and 38 MCP tools.

## Try it in 30 seconds

If you use Claude Code:

--- CODE START ---
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
--- CODE END ---

Then type "what can attune do?" and the help system will
introduce itself. Say "tell me more" to go deeper. The
entire help system runs on your Claude subscription — no
API key required.

The project is open source (Apache 2.0):
github.com/Smart-AI-Memory/attune-ai

This is the first in a series of articles where I'll
walk through building knowledge bases, help systems,
dynamic assistance, context-aware documents, and more —
all with Claude Code and MCP. Follow along if you want
to build something similar.

If you find it useful, a star on the repo helps others
discover the project.

What's your strategy for keeping docs accurate? I'd love
to hear how you're handling the same problem.
