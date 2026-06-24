---
type: quickstart
name: help-system-quickstart
feature: help-system
depth: quickstart
generated_at: 2026-06-24T11:38:37.880839+00:00
source_hash: ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab
status: generated
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
