---
name: help-system
source: content/features/help-system.md
tags:
- help
- templates
- docs
type: task
---

# The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help

## Tasks

### Discover features in a project

**Goal:** turn a source tree into a feature manifest.

**Steps:**

```python
from attune.help.bootstrap import scan_project, proposals_to_manifest

proposals = scan_project(".")
manifest = proposals_to_manifest(proposals)
print([p.name for p in proposals])
```

**Verify:** `scan_project()` returns a `list[ProposedFeature]`;
`proposals_to_manifest()` returns a `FeatureManifest` mapping feature
names to their matched source files.

### Generate templates for a feature (deprecated path)

**Goal:** write depth-layered help for one feature directly from the
engine. **Prefer the single-source pipeline** (`attune-author generate
<feature> --all-kinds`); this engine call is deprecated and emits a
`DeprecationWarning`, kept as the MCP `help_update` escape hatch.

**Steps:**

```python
import warnings

from attune.help.manifest import load_manifest
from attune.help.generator import generate_feature_templates

manifest = load_manifest(".help")
feature = manifest.features["help-system"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    result = generate_feature_templates(feature, ".help", ".")
print(result)
```

**Verify:** `generate_feature_templates()` returns a `GenerationResult`
of `GeneratedTemplate` objects, each with a `source_hash`. It is
synchronous (no `await`) but warns — it writes only three depths.

### Regenerate only what's stale

**Goal:** keep templates in sync as source changes, cheaply.

**Steps:**

```python
from attune.help.maintenance import run_maintenance

result = run_maintenance(".help", ".", dry_run=False)
print(result.regenerated_count, "regenerated;", result.stale_count, "were stale")
```

**Verify:** `run_maintenance()` returns a `MaintenanceResult`. Read
`regenerated_count` and `stale_count` as **properties** (no `()`). With
`dry_run=True` it reports without rewriting.

### Find help relevant to a file or workflow

**Goal:** surface contextual help without knowing a template ID.

**Steps:**

```python
from attune.help.engine import get_precursor_warnings, get_workflow_help

for t in get_precursor_warnings("src/attune/config/unified.py"):
    print(t.template_id)
for t in get_workflow_help("security-audit"):
    print(t.template_id)
```

**Verify:** both return a `list[PopulatedTemplate]` (default
`max_results=3`). They are exported from `help.feedback` and
re-exported from `help.engine`.
