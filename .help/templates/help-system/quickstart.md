---
type: quickstart
feature: help-system
depth: quickstart
generated_at: 2026-04-20T01:18:51.281969+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Quickstart: Help System

Scan your project and generate contextual help templates that respond to user queries with progressive depth.

```python
from attune_help.bootstrap import scan_project, proposals_to_manifest
from attune_help.generation import generate_feature_templates

# Scan your project for features
proposals = scan_project(".")
manifest = proposals_to_manifest(proposals)

# Generate help templates for the first discovered feature
feature = list(manifest.features.values())[0]
result = generate_feature_templates(feature, ".help", ".")
print(f"Generated {len(result.templates)} templates for {feature.name}")
```

Expected output:
```
Generated 3 templates for authentication-system
```

## Step 1: Scan your project

Run `scan_project()` on your project root to discover features automatically:

```python
proposals = scan_project(".")
print(f"Found {len(proposals)} potential features")
```

This examines your source files and identifies patterns like authentication, API endpoints, and data processing workflows.

## Step 2: Generate templates

Convert proposals to a manifest and create help templates:

```python
manifest = proposals_to_manifest(proposals)
for feature in manifest.features.values():
    result = generate_feature_templates(feature, ".help", ".")
    print(f"Created templates: {[t.path.name for t in result.templates]}")
```

You'll get concept, task, and reference templates for each feature.

## Step 3: Test the help lookup

Query the generated templates to see progressive depth in action:

```python
from attune_help.engine import HelpEngine

engine = HelpEngine()
response = engine.lookup("authentication")
print(response[:200])  # Shows concept-level help first
```

Each subsequent query on the same topic returns deeper, more detailed guidance.

## What you just did

You built a help system that automatically discovers your project's features and generates contextual documentation. The templates adapt their depth based on user interaction patterns and provide cross-linked guidance across concept, task, and reference materials.

## Next steps

Run `engine.lookup("help-system")` to explore the concept documentation and understand how progressive depth works.
