# Plugin Architecture — attune-ai & Healthcare CDS

## Overview

Two Claude Code plugins built on the attune-ai Python library, targeting different audiences through different Anthropic marketplaces. Both follow a Socratic design philosophy: minimal surface area, intelligent routing, and guided setup rather than menu overload.

```
PyPI (attune-ai)              ← Python library, primary distribution
GitHub (Smart-AI-Memory)      ← Source of truth
  │
  ├── attune-ai plugin        ← Developer-facing (claude-plugins-official)
  │     └── MCP server (stdio, local process)
  │     └── Skills (memory, orchestration)
  │     └── Single command: /attune
  │
  └── healthcare-cds plugin   ← Healthcare dev prototype (claude-plugins-official)
        └── Depends on attune-ai plugin
        └── Skills (clinical decision support)
        └── Single command: /care
        └── Requires Redis
```

## Design Principles

1. **Socratic approach** — Don't dump 26 workflows into the slash menu. One entry point per plugin. The skill asks the right questions and routes to the right workflow internally.

2. **Detect and adapt** — The MCP server detects its environment at startup (Redis available? pip package installed?) and adapts gracefully. Never fail silently; guide the user through what's needed.

3. **Skills teach thinking, not button-pressing** — Skills describe *how to reason about a domain*, not which specific workflow to invoke. The 26 workflows exist in the Python library and are accessed through MCP tools, orchestrated by skills that know when to use them.

4. **Layered distribution** — PyPI and GitHub remain the primary channels. The Claude plugins are an additional integration surface for developers already working in Claude Code/Cowork.

---

## Plugin 1: attune-ai (Developer Plugin)

### Audience
Developers building AI applications that need contextual memory, adaptive empathy, agent orchestration, and progressive tier routing.

### Marketplace
`claude-plugins-official` — submission via `clau.de/plugin-directory-submission`

### Directory Structure

```
attune-ai/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── README.md
├── commands/
│   └── attune.md                  # Single entry point: /attune
├── skills/
│   ├── memory-and-context/
│   │   └── SKILL.md               # Memory system, empathy levels, when to store vs retrieve
│   └── workflow-orchestration/
│       └── SKILL.md               # Multi-agent teams, tier routing, workflow composition
└── agents/
    └── setup-guide.md             # Detects environment, guides pip install + optional Redis
```

### plugin.json

```json
{
  "name": "attune-ai",
  "version": "2.4.0",
  "description": "AI-powered memory, empathy, and agent orchestration framework for developers",
  "author": {
    "name": "Smart AI Memory",
    "email": "patrick.roebuck@smartaimemory.com"
  },
  "homepage": "https://smartaimemory.com",
  "repository": "https://github.com/Smart-AI-Memory/attune-ai",
  "license": "Apache-2.0",
  "keywords": ["memory", "empathy", "agents", "orchestration", "tier-routing", "anthropic"]
}
```

### .mcp.json

```json
{
  "mcpServers": {
    "attune-ai": {
      "command": "python",
      "args": ["-m", "attune.mcp_server"],
      "env": {
        "ATTUNE_REDIS_REQUIRED": "false",
        "ATTUNE_CONFIG": "${CLAUDE_PLUGIN_ROOT}/config.json"
      }
    }
  }
}
```

### /attune Command (commands/attune.md)

```markdown
---
description: AI-powered memory, empathy, and agent orchestration
argument-hint: "<what you need help with>"
---

Single entry point for all attune-ai capabilities. Routes to the appropriate
workflow based on context. Ask about:

- Memory operations (store, retrieve, context management)
- Empathy level configuration and adaptive responses
- Agent team composition and orchestration
- Progressive tier routing (Haiku → Sonnet → Opus)
- Workflow execution and customization
- Redis setup and performance optimization

If no argument is provided, start with: "What are you building?"
```

### Skills

**memory-and-context/SKILL.md** — Teaches Claude:
- How attune-ai's memory system works (short-term, long-term, shared library)
- When to store vs retrieve vs forget
- How empathy levels modulate responses (1-10 scale)
- Local in-memory mode vs Redis-backed mode
- The memory/ directory structure and CLAUDE.md working memory

**workflow-orchestration/SKILL.md** — Teaches Claude:
- How to compose multi-agent teams from attune-ai's agent primitives
- Progressive tier escalation: start Haiku, escalate Sonnet, reserve Opus for complex reasoning
- How to run workflows via MCP tools (not slash commands)
- Release-prep team pattern as a reference example
- How to create custom workflows from existing building blocks

### MCP Server Tools (exposed via attune.mcp_server)

The existing 10+ tools, including:
- Memory CRUD operations
- Empathy level get/set
- Agent team creation and coordination
- Workflow execution
- Redis state management (when available)
- Telemetry and metrics

### Dependencies

- **Required**: Python 3.10+, `pip install attune-ai`
- **Optional**: Redis 7.x/8.x (detected at startup; falls back to local in-memory)
- **Optional**: Anthropic SDK ≥0.40.0 (for direct API calls; not needed if using through Claude)

### Setup Flow

1. Developer runs `/attune` or Claude detects the MCP server isn't responding
2. Setup agent checks: Is `attune-ai` pip-installed? Is Redis available?
3. Guides through `pip install attune-ai` if missing
4. Offers Redis setup if developer wants real-time coordination
5. Confirms MCP server is running with a health check

---

## Plugin 2: Healthcare CDS (Prototype Plugin)

### Audience
Healthcare developers evaluating how to build clinical decision support systems. This is a **reference implementation**, not a production-ready clinical tool.

### Marketplace
`claude-plugins-official` (published after attune-ai plugin is stable)

### Directory Structure

```
healthcare-cds/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── README.md
├── DISCLAIMER.md                  # Not a medical device; prototype only
├── commands/
│   └── care.md                    # Single entry point: /care
├── skills/
│   └── clinical-decision-support/
│       └── SKILL.md               # CDS patterns, vitals monitoring, alert design
└── agents/
    ├── protocol-monitor.md        # Monitors clinical metrics against protocols
    └── setup-guide.md             # Redis required; HIPAA considerations
```

### plugin.json

```json
{
  "name": "healthcare-cds",
  "version": "1.0.0",
  "description": "Prototype clinical decision support system built on attune-ai — for healthcare developers",
  "author": {
    "name": "Smart AI Memory",
    "email": "patrick.roebuck@smartaimemory.com"
  },
  "homepage": "https://smartaimemory.com",
  "repository": "https://github.com/Smart-AI-Memory/attune-ai",
  "license": "Apache-2.0",
  "keywords": ["healthcare", "clinical-decision-support", "nursing", "vitals", "HIPAA", "prototype"]
}
```

### .mcp.json

```json
{
  "mcpServers": {
    "healthcare-cds": {
      "command": "python",
      "args": ["-m", "attune.mcp_server.healthcare"],
      "env": {
        "ATTUNE_REDIS_REQUIRED": "true",
        "ATTUNE_CONFIG": "${CLAUDE_PLUGIN_ROOT}/config.json"
      }
    }
  }
}
```

### Key Differences from attune-ai Plugin

| Aspect | attune-ai | healthcare-cds |
|--------|-----------|----------------|
| Redis | Optional (detected at startup) | Required (setup enforced) |
| Entry command | `/attune` | `/care` |
| Skills focus | Memory, orchestration, tier routing | CDS patterns, vitals, alert thresholds |
| Target user | Any AI developer | Healthcare implementation developer |
| HIPAA guidance | Not applicable | Included in skill and disclaimer |
| Marketplace | claude-plugins-official | claude-plugins-official (post attune-ai) |
| Dependency | pip install attune-ai | pip install attune-ai + Redis |

### Healthcare Disclaimer

Consistent with smartaimemory.com/terms/:
> This plugin is a prototype and is NOT intended as a medical device or for direct clinical use. Developers deploying in regulated healthcare environments must independently validate outputs and ensure compliance with HIPAA, FDA, and institutional requirements.

---

## Distribution Strategy

### Primary Channels (unchanged)
- **PyPI**: `pip install attune-ai` — the Python library
- **GitHub**: `github.com/Smart-AI-Memory/attune-ai` — source, issues, PRs

### Plugin Channels (new)
- **claude-plugins-official**: Both plugins, submitted via `clau.de/plugin-directory-submission`
- **Own marketplace** (future option): `Smart-AI-Memory/attune-plugins` on GitHub, if a family of plugins grows beyond two

### Version Alignment
- Plugin version tracks the PyPI package version (currently 2.4.0)
- Healthcare plugin version independent (starts at 1.0.0)
- Breaking changes in attune-ai that affect healthcare plugin documented in both CHANGELOGs

---

## Resolved Decisions

1. **Healthcare plugin location**: **Separate repo** (`Smart-AI-Memory/healthcare-cds-plugin`). Independent versioning, release cycles, and clear separation of concerns.

2. **MCP server modes**: **Separate entry point** (`python -m attune.mcp_server.healthcare`). Keeps the base server clean for general developers. Healthcare module imports the base and registers additional clinical tools.

3. **Skill evaluation**: Use the skill-creator eval framework to benchmark routing accuracy. Target 80%+ across all 26 workflows before publishing. See Phase 3 of PLUGIN_DEVELOPMENT_PLAN.md.

4. **Official marketplace acceptance**: Submit to `claude-plugins-official` first. Fallback: own marketplace (`Smart-AI-Memory/attune-plugins`) for immediate availability, resubmit to official after building traction.

5. **Plugin auto-updates**: Passive PyPI version check at MCP server startup. One-confirmation upgrade via `pip install --upgrade attune-ai`. Network failures silently skip the check.

---

## Memory Layer Positioning

### The Problem This Solves

Anthropic ships native memory features (CLAUDE.md, Auto Memory, Session Memory, Memory Tool API). attune-ai's memory system must not duplicate what's already built in — it must sit above it as an **application-layer knowledge management framework**.

### Layer Separation

```
┌────────────────────────────────────────────────────────┐
│  attune-ai memory layer (structured knowledge mgmt)    │
│  ├── Pattern lifecycle: staged → validated → promoted  │
│  ├── Security pipeline: PUBLIC / INTERNAL / SENSITIVE  │
│  ├── Empathy-modulated storage (5 levels)              │
│  ├── Multi-agent coordination (Redis pub/sub)          │
│  └── Confidence thresholds & retention policies        │
├────────────────────────────────────────────────────────┤
│  Anthropic native memory (conversation continuity)     │
│  ├── CLAUDE.md — project instructions (manual)         │
│  ├── Auto Memory — learnings (automatic)               │
│  ├── Session Memory — session summaries (automatic)    │
│  └── Memory Tool API — CRUD on /memories (beta)        │
└────────────────────────────────────────────────────────┘
```

### When to Use Which

| Use Case | Use Anthropic Native | Use attune-ai |
|----------|---------------------|---------------|
| "Remember my code style" | CLAUDE.md | — |
| "What did we do last session?" | Session Memory | — |
| "Store this pattern for reuse across agents" | — | memory_store (shared library) |
| "Classify this finding as SENSITIVE" | — | Security pipeline |
| "Coordinate memory across 3 parallel agents" | — | Redis pub/sub |
| "Promote this pattern after 5 successful uses" | — | Pattern lifecycle |
| "Adjust response depth based on user context" | — | Empathy modulation |
| "Track what this project uses" | Auto Memory | — |

### Skill Guidance

The memory-and-context skill (Phase 1.4) must explicitly teach Claude:

1. **Don't replace native memory for simple cases** — conversation continuity, project preferences, and session recall are handled natively.
2. **Use attune-ai when structure matters** — security classification, confidence scoring, cross-agent coordination, and empathy-modulated behavior.
3. **The two systems are complementary** — native memory feeds context into attune-ai's structured processing, not the other way around.

### Healthcare Differentiation

For healthcare-cds, attune-ai's memory layer is non-negotiable:

- HIPAA compliance requires security classification — Anthropic's flat-file memory doesn't provide it
- PII scrubbing and AES-256-GCM encryption on SENSITIVE patterns
- Audit logging for all memory operations
- Redis-backed real-time coordination for multi-agent clinical monitoring

---

## Redis Upgrade Path

### Design Principle

Non-healthcare developers should never be forced into Redis. The upgrade from in-memory to Redis must be frictionless and well-documented.

### How It Works

```
Default install (no Redis):
  pip install attune-ai
  → In-memory storage
  → All features work (memory, empathy, orchestration)
  → Patterns persist to local JSON files between sessions
  → Single-agent workflows only

Upgrade to Redis:
  pip install attune-ai[redis]   # or: pip install redis separately
  → MCP server auto-detects Redis at startup
  → Zero config changes required (connects to localhost:6379 by default)
  → Unlocks: real-time multi-agent coordination, pub/sub, faster lookups
  → Patterns persist in Redis with configurable TTL
  → Falls back to in-memory gracefully if Redis goes down mid-session
```

### Upgrade Documentation Requirements

The setup agent and skill documentation must include:

1. **Clear benefit framing** — not "you should use Redis" but "here's what Redis adds: multi-agent coordination, sub-millisecond lookups, shared state across sessions"
2. **One-command upgrade** — `pip install attune-ai[redis]` or `pip install redis`
3. **Zero config for defaults** — `localhost:6379` with no auth works out of the box
4. **Custom config when needed** — `ATTUNE_REDIS_URL=redis://user:pass@host:port/db`
5. **Graceful degradation** — if Redis disconnects mid-session, the system falls back to in-memory with a single warning, not a crash
6. **No data migration** — in-memory patterns and Redis patterns are compatible formats; switching backends doesn't lose data if both were persisting to the same JSON fallback

---

## Consistency References

- **Terms of Service**: https://smartaimemory.com/terms/ (healthcare disclaimer language)
- **Privacy Policy**: https://smartaimemory.com/privacy/ (local processing, no telemetry)
- **PhysioNet Ethics Statement**: Aligned with both documents above
- **License**: Apache 2.0 across all distribution channels
