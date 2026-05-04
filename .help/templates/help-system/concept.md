---
type: concept
feature: help-system
depth: concept
generated_at: 2026-05-04T02:30:33.548305+00:00
source_hash: 02f860e914d05f44ecfe133be87b26cad7e3f200e70a1a30901af220c56e2181
status: generated
---

# Help System

## How it works

The help system generates contextual documentation by scanning your project, mapping features to source files, and creating progressive-depth templates that adapt to different audiences and usage patterns.

When you scan a project, the system analyzes code structure and proposes features automatically. Each feature gets mapped to specific files, then generates three template depths: concept (mental model), task (step-by-step), and reference (complete lookup). The engine tracks user feedback and usage patterns to surface the most relevant content first.

## Core components

- **`ProposedFeature`** — Discovered features with confidence scores and file mappings from project scanning
- **`GeneratedTemplate`** — Individual template file with source hash tracking for staleness detection
- **`GenerationResult`** — Complete template set for one feature, including all depths and matched files
- **`MaintenanceResult`** — Staleness report and regeneration results from a maintenance run
- **`Feature`** — Finalized feature definition linking project capabilities to source files

The system maintains a features manifest (`features.yaml`) that maps each project capability to its implementation files. When source files change, the system detects staleness by comparing file hashes and regenerates affected templates.

## Template lifecycle

Templates follow a three-stage lifecycle: discovery, generation, and maintenance. During discovery, the scanner identifies features by analyzing file patterns, entry points, and configuration files. Generation creates structured markdown templates with YAML frontmatter for each depth level. Maintenance tracks changes to source files and updates stale templates automatically.

The engine supports multiple audience profiles (Claude Code, CLI, marketplace) and transforms the same base template for different contexts. User feedback scores help rank template quality, while usage telemetry weights search results by real-world relevance.

## What connects to it

The help system integrates with development workflows through precursor warnings (alerts before editing risky files), post-workflow guidance (relevant templates after completing tasks), and tag-based search across all generated content.

| Interface | Purpose | File |
|-----------|---------|------|
| `ProposedFeature` | Feature discovery with confidence scoring | `src/attune/help/bootstrap.py` |
| `GeneratedTemplate` | Template file with staleness tracking | `src/attune/help/generator.py` |
| `GenerationResult` | Complete feature template set | `src/attune/help/generator.py` |
| `MaintenanceResult` | Staleness and regeneration report | `src/attune/help/maintenance.py` |
| `Feature` | Project capability to file mapping | `src/attune/help/manifest.py` |
