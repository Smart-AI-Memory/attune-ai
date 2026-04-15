---
type: tip
feature: configuration
depth: tip
generated_at: 2026-04-14T15:31:30.990630+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Use convenience functions instead of instantiating ConfigLoader directly

## Recommendation

Call `load_unified_config()` and `save_unified_config()` rather than creating ConfigLoader instances yourself. These functions handle the global loader singleton and path discovery automatically.

```python
# Do this
config = load_unified_config()

# Not this
loader = ConfigLoader()
config = loader.load()
```

## Why

The convenience functions eliminate boilerplate and ensure consistent behavior across your application, since they all share the same ConfigLoader instance with its cached configuration path.

## Tradeoff

You lose fine-grained control over the config file location, but you can still override this by passing an explicit path to the convenience functions when needed.
