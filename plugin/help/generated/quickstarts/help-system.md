---
name: help-system
source: content/features/help-system.md
tags:
- help
- templates
- docs
type: quickstart
---

# The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help

## Quickstart

Serve a template that has already been generated (the ID is
`<type-prefix>-<name>`, so `con-progressive-depth` is the *concept*
named `progressive-depth`):

```python
from attune.help.templates import populate

template = populate("con-progressive-depth")
if template is not None:
    print(template.body)
```

Check whether any feature's templates are out of date:

```python
from attune.help.manifest import load_manifest
from attune.help.staleness import check_staleness

manifest = load_manifest(".help")
report = check_staleness(manifest, ".help", ".")
print(report.stale_count, "stale:", report.stale_features)
```
