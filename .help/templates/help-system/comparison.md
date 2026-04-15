---
type: comparison
feature: help-system
depth: comparison
generated_at: 2026-04-14T15:04:10.499732+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System vs static documentation generators

## Context

The help system generates context-aware documentation templates that adapt to your codebase and usage patterns. Unlike static documentation generators that produce fixed output, this system creates progressive-depth help that responds to workflow events and tracks user feedback.

## Feature comparison

| Feature | Help System | Static Generators (Sphinx, MkDocs) |
|---------|------------|-------------------------------------|
| **Content generation** | Scans source code to auto-generate templates | Requires manual writing of documentation files |
| **Adaptive depth** | Three levels (concept/task/reference) based on user needs | Fixed structure determined at build time |
| **Workflow integration** | Contextual help triggered by workflow completion | Documentation separate from development workflow |
| **Feedback tracking** | Records user ratings and adjusts template confidence | No built-in feedback mechanism |
| **Staleness detection** | Compares source file hashes to detect outdated content | Manual maintenance or build-time checks |
| **Usage analytics** | Tracks template access patterns for relevance weighting | Basic page view statistics only |
| **Template polish** | AI-assisted rewriting following style guides | Raw content or manual editing |

## Performance characteristics

The help system prioritizes **runtime adaptability** over build speed. Template generation is ~2-3x slower than static builds but enables:
- Real-time content updates when source files change
- Contextual help delivery based on current workflow state
- Progressive disclosure that scales complexity to user needs

Static generators excel at **build performance** and are better for:
- Large documentation sites with stable content
- SEO-optimized public documentation
- Integration with existing documentation workflows

## Use Help System when...

Choose the help system for:
- **Active codebases** where documentation must stay synchronized with frequent code changes
- **Developer tooling** that needs contextual help during workflows
- **Progressive onboarding** where users need different detail levels over time
- **Feedback-driven improvement** of documentation quality

## Use static generators when...

Choose traditional documentation tools for:
- **Public-facing documentation** that requires custom styling and SEO
- **Stable APIs** where content changes infrequently
- **Large teams** with dedicated technical writers
- **Integration requirements** with existing documentation infrastructure

## Migration path

If you're currently using static generators, you can adopt the help system incrementally:
1. Run `scan_project()` to identify features for template generation
2. Use `generate_feature_templates()` for high-change areas first
3. Keep existing documentation for stable, public-facing content
4. Monitor `get_template_confidence()` scores to identify successful templates
