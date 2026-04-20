---
type: concept
feature: help-system
depth: concept
generated_at: 2026-04-20T01:16:32.470715+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Help System

The help system is a progressive-depth engine that generates, maintains, and serves contextual documentation templates based on your project's source code.

## Core architecture

The help system operates through three layers:

- **Discovery layer** scans your project to identify features and map them to source files using `ProposedFeature` and `FeatureManifest`
- **Generation layer** creates structured markdown templates at three depth levels (concept, task, reference) with automatic staleness detection
- **Runtime layer** serves progressive-depth help through audience-aware rendering and session state tracking

## Template lifecycle

Templates move through a complete lifecycle from discovery to delivery:

1. **Scanning** — The system examines source files and proposes features based on entry points, configuration patterns, and code structure
2. **Generation** — Each feature becomes three template files (concept/task/reference) using structured markdown with YAML frontmatter
3. **Maintenance** — Templates stay current through automatic staleness checking based on source file hashes
4. **Population** — Templates fill with runtime context (file paths, error messages, workflow names) for specific user situations
5. **Adaptation** — Output transforms for different audiences (plain text, CLI, Claude Code, marketplace)

## Progressive depth experience

Users start with concepts and drill deeper without leaving their conversation:

| Depth | Template type | User gets |
|-------|---------------|-----------|
| 0 | Concept | What is this feature and when would I use it? |
| 1 | Task | Step-by-step instructions to use it right now |
| 2 | Reference | Complete details, options, and edge cases |

Session state tracks your current topic and depth level. Asking about the same topic advances to the next level. Asking about a different topic resets to concept level.

## Quality assurance

The system maintains help quality through multiple mechanisms:

- **Feedback scoring** records user ratings and calculates confidence scores per template
- **Usage telemetry** weights template relevance based on actual access patterns
- **Cross-link integrity** ensures all template references resolve to real files
- **Render validation** verifies each audience adapter produces well-formed output
