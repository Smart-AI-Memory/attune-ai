---
feature: help-system
depth: concept
generated_at: 2026-04-06T16:05:31.998412+00:00
source_hash: caf95aed14eb4d6660007f9eacb673cd2c7f4d1f2ac8d5301599e9ffee1dad6f
status: generated
---

# Help System

## How it works

Progressive-depth help engine and template management.

The main building blocks are:

- **`ProposedFeature`** — A feature discovered by scanning.
- **`GeneratedTemplate`** — Result of generating one template file.
- **`GenerationResult`** — Result of generating templates for a feature.
- **`MaintenanceResult`** — Result of a help maintenance run.
- **`Feature`** — A project feature mapped to source files.

Under the hood, this feature spans 686 source
files covering:

- Project scanning and manifest bootstrapping.
- Template engine for the documentation help system.
- Feedback and confidence scoring for help templates.

## What connects to it

This feature relates to: help, templates, docs.

Other parts of the codebase interact with
help system through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ProposedFeature` | A feature discovered by scanning. | `src/attune/help/bootstrap.py` |
| `GeneratedTemplate` | Result of generating one template file. | `src/attune/help/generator.py` |
| `GenerationResult` | Result of generating templates for a feature. | `src/attune/help/generator.py` |
| `MaintenanceResult` | Result of a help maintenance run. | `src/attune/help/maintenance.py` |
| `Feature` | A project feature mapped to source files. | `src/attune/help/manifest.py` |
