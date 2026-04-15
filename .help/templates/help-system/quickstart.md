---
type: quickstart
feature: help-system
depth: quickstart
generated_at: 2026-04-14T15:03:40.179831+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Quickstart: help system

Scan your project and generate contextual help templates automatically.

```python
from attune.help.bootstrap import scan_project

# Scan your project for features
features = scan_project('.')
print(f"Found {len(features)} features:")
for feature in features[:3]:  # Show first 3
    print(f"  {feature.name}: {feature.description}")
```

Expected output:
```
Found 12 features:
  authentication: User login and session management
  database: SQLite connection and query handling
  api-endpoints: REST API route definitions
```

## Generate your first template

1. **Create a feature manifest** from your scan results:
   ```python
   from attune.help.bootstrap import proposals_to_manifest, save_manifest

   manifest = proposals_to_manifest(features)
   save_manifest(manifest, 'features.yaml')
   ```

2. **Generate templates** for a specific feature:
   ```python
   from attune.help.generation import generate_feature_templates

   # Pick any feature from your scan
   auth_feature = next(f for f in features if 'auth' in f.name.lower())
   result = generate_feature_templates(auth_feature, '.help', '.')
   print(f"Generated {len(result.templates)} templates")
   ```

3. **Search your generated templates** by topic:
   ```python
   from attune.help.feedback import search_by_tag

   auth_templates = search_by_tag('authentication')
   print(f"Found {len(auth_templates)} authentication templates")
   ```

**Next:** Run `generate_feature_templates()` on each feature in your manifest to build a complete help system.
