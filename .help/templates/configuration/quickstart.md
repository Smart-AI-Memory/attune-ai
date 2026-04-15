---
type: quickstart
feature: configuration
depth: quickstart
generated_at: 2026-04-14T15:31:23.324935+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Quickstart: configuration

Load and manage your Attune AI configuration with a single function call.

```python
from attune.config.loader import load_unified_config

config = load_unified_config()
print(f"Model: {config.model_id}")
print(f"Provider: {config.provider}")
```

## Set up your configuration

1. **Create a configuration file** in one of these locations:
   - `./attune.config.json` (project directory)
   - `~/.attune/config.json` (user directory)
   - `~/.config/attune/config.json` (XDG config directory)

2. **Add basic settings** to your JSON file:
   ```json
   {
     "provider": "openai",
     "model": "gpt-4",
     "temperature": 0.7,
     "max_tokens": 2000
   }
   ```

3. **Load and verify** your configuration:
   ```python
   from attune.config.loader import load_unified_config

   config = load_unified_config()
   print(f"Using {config.provider} with model {config.model_id}")
   ```

Expected output:
```
Using openai with model gpt-4
```

You can also override any setting using environment variables with the `ATTUNE_` prefix, like `ATTUNE_MODEL=gpt-3.5-turbo`.

## Next steps

Configure Redis integration for state management by adding a `redis` section to your config file.
