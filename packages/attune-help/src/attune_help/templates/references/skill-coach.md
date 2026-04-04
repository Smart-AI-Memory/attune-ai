---
type: reference
subtype: procedural
name: skill-coach
category: skill
tags: [skill, help-system, plugin, reference]
source: plugin/skills/coach/SKILL.md
---

# Coach Reference

Complete reference for the coach skill -- the help
system's own help. Covers the template knowledge base,
progressive depth engine, session state, cross-linking,
and maintenance.

## Invocation

```
/coach <topic>
```

Or natural language:

```
what is security audit?
tell me about code review
explain progressive depth
how does the help system work?
```

**Trigger phrases:** coach, learn, explain, tell me more,
how does, what is, help with, deeper.

Runs on your Claude subscription -- no API key or
additional cost.

## The three depth levels

Each level serves a different kind of content:

| Level | Template type | What you get | How to trigger |
|-------|---------------|--------------|----------------|
| 0 | **Concept** | What and why -- overview, use cases | Ask about any topic |
| 1 | **Task** | Step-by-step -- how to do it now | "tell me more" |
| 2 | **Reference** | Full detail -- every option, edge case, config | "tell me more" again |

Repeated calls on the same topic auto-advance. A new
topic resets to concept (level 0).

## All 11 template types

The knowledge base contains 557 templates across 11
types. The three progressive-depth types (concept,
task, reference) are the primary learning path. The
remaining 8 types serve specialized needs:

| Type | Count | Purpose |
|------|-------|---------|
| **concepts** | 24 | What-and-why overviews |
| **tasks** | 21 | Step-by-step how-to guides |
| **references** | 45 | Full-detail skill and tool docs |
| **errors** | 100+ | Lessons learned from real bugs |
| **warnings** | 100+ | Proactive "watch out for this" |
| **faqs** | 100+ | Question-and-answer format |
| **tips** | 16 | Post-workflow suggestions |
| **troubleshooting** | 7 | Diagnosis and fix guides |
| **notes** | 22 | Terms, decisions, conventions |
| **quickstarts** | 22 | Minimal "just get started" |
| **comparisons** | 4 | Side-by-side feature tables |

## Topic slug resolution

The engine maps natural language to topic slugs, then
resolves slugs to templates at the current depth level:

| User says | Topic slug | Level 0 template | Level 1 template | Level 2 template |
|-----------|-----------|-------------------|-------------------|-------------------|
| security audit | `security-audit` | con-tool-security-audit | tas-use-security-audit | ref-skill-security-audit |
| code quality | `code-quality` | con-tool-code-quality | tas-use-code-quality | ref-skill-code-quality |
| bug prediction | `bug-predict` | con-tool-bug-predict | tas-use-bug-predict | ref-skill-bug-predict |
| test generation | `smart-test` | con-tool-smart-test | tas-use-smart-test | ref-skill-smart-test |
| release prep | `release-prep` | con-tool-release-prep | tas-use-release-prep | ref-skill-release-prep |
| refactor | `refactor-plan` | con-tool-refactor-plan | tas-use-refactor-plan | ref-skill-refactor-plan |
| doc gen | `doc-gen` | con-tool-doc-gen | tas-use-doc-gen | ref-skill-doc-gen |

The resolution order tries `con-tool-{topic}` then
`con-{topic}` at level 0, `tas-use-{topic}` then
`tas-tool-{topic}` at level 1, and `ref-skill-{topic}`
then `ref-tool-{topic}` at level 2.

## Cross-linking

Templates are linked by tags. The `cross_links.json`
index maps 430 of 557 templates across 62 tags. When
a template is served, the engine includes related
templates as suggestions.

Link rules by type:

| Template type | Links to |
|---------------|----------|
| Error | Warning for the same lesson |
| Warning | FAQ for the same lesson |
| FAQ | Error for the same lesson |
| Task | Reference for the same skill |
| Concept | Task for the same skill |
| Tip | Concept for the related workflow |

**Tag search:** ask "show me everything tagged
security" to find all templates across all types with
that tag.

## Session state details

Session state is stored as a JSON file per user in
`~/.attune-help/sessions/`.

| Field | Type | Description |
|-------|------|-------------|
| `last_topic` | string | Most recent topic slug |
| `depth_level` | int | Current depth (0, 1, or 2) |
| `timestamp` | float | Last access time (epoch) |

**Expiry:** sessions expire after 4 hours of
inactivity (`_SESSION_TTL_SECONDS = 14400`). After
expiry, the next request starts fresh at level 0.

**Reset:** the user can say "start from the beginning"
or "reset" to manually reset depth to 0.

**Post-workflow skip:** when `last_workflow` is
provided, the engine starts at level 1 (task) instead
of level 0 (concept), since the user already knows
what the tool does.

## Execution details

1. If the user provided a topic, call:

```
help_lookup(topic="<topic>", mode="progressive")
```

2. If the user says "tell me more" or "go deeper"
   without a new topic, call `help_lookup` with the
   same topic again -- it auto-advances.

3. To reset depth:

```
help_lookup(topic="<topic>", mode="progressive", reset=true)
```

4. To skip to task level after a workflow:

```
help_lookup(
    topic="<topic>",
    mode="progressive",
    last_workflow="<workflow-name>"
)
```

5. For file-based warnings (precursor mode):

```
help_lookup(
    topic="warnings",
    mode="precursor",
    file_path="<path to file>"
)
```

## Output format

The returned `body` is pre-formatted markdown. Append
a level indicator after presenting it:

- Level 0: "(concept view -- say 'tell me more' for
  step-by-step guide)"
- Level 1: "(task view -- say 'tell me more' for full
  reference)"
- Level 2: "(reference view -- full detail)"

If the result includes `related` entries, list them as
suggested next reads.

## Maintenance mode

If the user says "update help", "refresh templates",
or "check for stale docs":

Preview what's stale:

```
help_maintain(dry_run=true)
```

Regenerate stale templates:

```
help_maintain(dry_run=false)
```

For cost-optimized bulk updates (50% savings via
Anthropic Batch API):

```
help_maintain(batch=true, dry_run=false)
```

## Want to learn more?

- Say **"what is coach?"** to go back to the overview
- Say **"how do I use coach?"** for the step-by-step
  guide
- Say **"what is progressive depth?"** to understand
  the depth engine
- Say **"tell me about cross-linking"** to see how
  templates connect
