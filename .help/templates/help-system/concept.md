---
feature: help-system
depth: concept
generated_at: 2026-04-06T04:30:19.440252+00:00
source_hash: e4918f66598750dc930dee90c838cd2acf979b30107bd9345c3738c2b2f0dbac
status: generated
---

# Help System

## How it works

Progressive-depth help engine that generates and manages documentation templates with audience targeting and feedback scoring.

The main building blocks are:

- **`ProposedFeature`** — A feature discovered by scanning project source code.
- **`GeneratedTemplate`** — Result of generating one template file with metadata.
- **`GenerationResult`** — Result of generating all templates for a feature.
- **`MaintenanceResult`** — Result of a help maintenance run including staleness checks.
- **`Feature`** — A project feature mapped to its source files and documentation.

Under the hood, this feature spans 686 source
files covering:

- Project scanning and manifest bootstrapping for feature discovery.
- Template engine that adapts content for different audiences.
- Feedback collection and confidence scoring for template quality assessment.

## What connects to it

This feature relates to: help, templates, docs.

Other parts of the codebase interact with
help system through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ProposedFeature` | A feature discovered by scanning project source code. | `src/attune/help/bootstrap.py` |
| `GeneratedTemplate` | Result of generating one template file with metadata. | `src/attune/help/generator.py` |
| `GenerationResult` | Result of generating all templates for a feature. | `src/attune/help/generator.py` |
| `MaintenanceResult` | Result of a help maintenance run including staleness checks. | `src/attune/help/maintenance.py` |
| `Feature` | A project feature mapped to its source files and documentation. | `src/attune/help/manifest.py` |
