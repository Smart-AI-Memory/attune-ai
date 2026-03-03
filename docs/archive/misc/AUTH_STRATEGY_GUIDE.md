---
description: Authentication Strategy Guide: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Authentication Strategy Guide

**Version:** 1.0
**Created:** January 29, 2026
**Feature:** Intelligent routing between Claude subscriptions and Anthropic API

---

## Overview

The Attune AI now supports intelligent routing between **Claude.ai/Code subscriptions** and the **Anthropic API** based on:

- Your subscription tier (Pro, Max, Enterprise)
- Module size (small, medium, large)
- Cost optimization preferences

This guide explains how to choose and configure your authentication strategy.

---

## Quick Start

### First-Time Setup

#### Option 1: CLI Command (Recommended)

```bash
python -m attune.models.auth_cli setup
```

#### Option 2: Python API

```python
from attune.models import configure_auth_interactive

strategy = configure_auth_interactive()
```

This will:

1. Ask for your subscription tier
2. Show pros/cons comparison
3. Recommend the optimal strategy
4. Save configuration to `~/.empathy/auth_strategy.json`

### CLI Commands

#### View current configuration

```bash
python -m attune.models.auth_cli status
python -m attune.models.auth_cli status --json  # JSON output
```

#### Get recommendation for a specific file

```bash
python -m attune.models.auth_cli recommend src/my_module.py
```

#### Reset configuration

```bash
python -m attune.models.auth_cli reset --confirm
```

### Automatic Detection

The system will automatically:
- Detect your subscription tier
- Calculate module size
- Route to the optimal authentication method
- Show first-time educational comparison

---

## Authentication Modes

### 1. Subscription Mode

**Use your Claude.ai/Code subscription quota**

**Pros:**
- No additional per-token charges
- Simple auth (already logged in)
- Good for small/medium modules

**Cons:**
- Uses monthly quota
- 200K context limit
- Rate limits apply

**Best for:** Small modules (<500 LOC), Max/Enterprise users

---

### 2. API Mode

**Use Anthropic API (pay-per-token)**

**Pros:**
- 1M context window (fits large modules)
- No quota consumption
- Separate billing (easier tracking)
- Higher rate limits

**Cons:**
- Requires API key setup
- Pay-per-token (~$0.10-0.15 per module)
- Separate authentication

**Best for:** Large modules (>2000 LOC), Pro users

---

### 3. Auto Mode (Recommended)

**Smart routing based on module size**

**Strategy:**
- Small modules (<500 LOC) → **Subscription**
- Medium modules (500-2000 LOC) → **Subscription**
- Large modules (>2000 LOC) → **API**

**Pros:**
- Best of both worlds
- Cost-optimized
- Automatic decision-making

**Cons:**
- Requires both subscription AND API key

**Best for:** Max/Enterprise users with diverse codebases

---

## Recommendations by Tier

### Pro Users ($20/month)

**Recommended:** API Mode

**Why:**
- Pro subscription has limited quota
- Pay-per-token API is more economical for lower usage
- ~$0.10-0.15 per module is affordable

**Setup:**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

---

### Max Users ($200/month)

**Recommended:** Auto Mode

**Why:**
- Max subscription has generous quota
- Use subscription for small/medium modules (saves money)
- Use API for large modules (1M context window)

**Setup:**
```bash
# Set API key for large modules
export ANTHROPIC_API_KEY='your-key-here'

# Log in to Claude.ai/Code for subscription access
```

---

### Enterprise Users

**Recommended:** Auto Mode

**Why:**
- Enterprise has highest quota
- Auto mode optimizes cost across all modules
- 1M context needed for complex enterprise modules

**Setup:**
```bash
export ANTHROPIC_API_KEY='your-enterprise-key'
```

---

## Module Size Thresholds

The system categorizes modules by lines of code (LOC):

| Category | Size Range | Default Auth | Context Required |
|----------|-----------|--------------|------------------|
| Small    | < 500 LOC | Subscription | ~2K tokens |
| Medium   | 500-2K LOC | Subscription | ~8K tokens |
| Large    | > 2K LOC | API | ~20K+ tokens |

### Customizing Thresholds (Advanced)

**Most users won't need to change these defaults.** The 500/2000 LOC thresholds work well for most codebases.

If you have specific needs, manually edit `~/.empathy/auth_strategy.json`:

```json
{
  "subscription_tier": "max",
  "default_mode": "auto",
  "small_module_threshold": 500,
  "medium_module_threshold": 2000,
  "loc_to_tokens_multiplier": 4.0,
  "setup_completed": true
}
```

**Configuration Options:**

| Field | Default | Purpose |
|-------|---------|---------|
| `small_module_threshold` | 500 | Modules under this → small category |
| `medium_module_threshold` | 2000 | Modules under this → medium category |
| `loc_to_tokens_multiplier` | 4.0 | Token estimation (LOC × multiplier) |

**Example Scenarios:**

**Aggressive subscription usage** (Max user with high quota):
```json
{
  "small_module_threshold": 750,
  "medium_module_threshold": 3000
}
```
Effect: Uses subscription for larger modules, maximizes quota usage

**Conservative API usage** (Limited subscription quota):
```json
{
  "small_module_threshold": 300,
  "medium_module_threshold": 1000
}
```
Effect: Switches to API sooner, preserves subscription quota

After editing, restart your workflow for changes to take effect.

---

## Cost Comparison

### Example: 1000 LOC Module

**Subscription Mode:**
- Monetary cost: $0.00
- Quota cost: ~4,000 tokens from subscription
- Fits in 200K context: ✅

**API Mode:**
- Monetary cost: ~$0.0002 (< 1 cent)
- Quota cost: None
- Fits in 1M context: ✅

### Annual Cost Estimate

**Scenario:** 250 modules/year

| Tier | Strategy | Annual Cost |
|------|----------|-------------|
| Pro + API | API Mode | $240 (subscription) + $40 (API) = **$280** |
| Max + API | Auto Mode | $2,400 (subscription) + $10 (API large modules) = **$2,410** |
| API Only | API Mode | $0 (subscription) + $40 (API) = **$40** |

**Key Insight:** Max users should use AUTO mode to maximize subscription value while having API for large modules.

---

## Configuration Reference

### AuthStrategy Class

```python
from attune.models import AuthStrategy, SubscriptionTier, AuthMode

strategy = AuthStrategy(
    subscription_tier=SubscriptionTier.MAX,
    default_mode=AuthMode.AUTO,
    small_module_threshold=500,
    medium_module_threshold=2000,
    prefer_subscription=True,
    cost_optimization=True,
)

# Get recommendation for a module
recommended = strategy.get_recommended_mode(module_lines=1000)
print(f"Recommended: {recommended.value}")

# Estimate cost
cost = strategy.estimate_cost(module_lines=1000)
print(f"Cost: ${cost['monetary_cost']}")
```

### Loading/Saving Configuration

```python
from attune.models import AuthStrategy

# Load from file (or create default)
strategy = AuthStrategy.load()

# Modify
strategy.default_mode = AuthMode.AUTO
strategy.prefer_subscription = True

# Save
strategy.save()  # Saves to ~/.empathy/auth_strategy.json
```

---

## Integration with Document Generation

The DocumentGenerationWorkflow automatically uses auth_strategy:

```python
from attune.workflows.document_gen import DocumentGenerationWorkflow
from attune.models import get_auth_strategy, count_lines_of_code

# Get auth strategy (first-time setup if needed)
strategy = get_auth_strategy()

# Calculate module size
module_lines = count_lines_of_code("src/my_module.py")

# Get recommended auth mode
auth_mode = strategy.get_recommended_mode(module_lines)
print(f"Using {auth_mode.value} for this module")

# Run workflow (uses recommended auth automatically)
workflow = DocumentGenerationWorkflow()
result = await workflow.execute(
    source_code=source_code,
    target="src/my_module.py",
    doc_type="api_reference",
)
```

---

## Troubleshooting

### "First-time authentication setup required"

**Solution:** Run interactive setup:

```python
from attune.models import configure_auth_interactive
strategy = configure_auth_interactive()
```

### "ANTHROPIC_API_KEY not found"

**Solution:** Set API key:

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Or add to `.env` file:

```bash
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

### "Module too large for subscription context"

**Solution:** The system automatically uses API for large modules. Ensure `ANTHROPIC_API_KEY` is set.

### "Subscription quota exceeded"

**Solution:**
1. Wait for monthly quota reset
2. Temporarily switch to API mode:
   ```python
   strategy.default_mode = AuthMode.API
   strategy.save()
   ```

---

## Best Practices

1. **Pro users:** Use API mode exclusively
   - More economical than subscription for documentation generation
   - Pay-per-token matches usage patterns

2. **Max users:** Use AUTO mode
   - Maximizes subscription value
   - API provides overflow capacity for large modules

3. **Set both credentials:**
   - Configure subscription (login to Claude.ai/Code)
   - Set ANTHROPIC_API_KEY for flexibility

4. **Monitor costs:**
   - Check `~/.empathy/workflow_runs.json` for usage stats
   - Review monthly API billing

5. **Adjust thresholds:**
   - Lower thresholds if subscription quota runs out
   - Raise thresholds if API costs are high

---

## FAQ

**Q: Do subscriptions include API access?**
A: No. Claude subscriptions and Anthropic API are separate systems. Subscriptions are for interactive use; API is for programmatic access.

**Q: Can I use subscription without API key?**
A: Yes, but you'll be limited to small/medium modules that fit in 200K context.

**Q: Can I use API without subscription?**
A: Yes! Set `subscription_tier=SubscriptionTier.API_ONLY` and use API exclusively.

**Q: How does the system detect module size?**
A: Counts non-blank, non-comment lines of code (LOC) and multiplies by ~4 tokens/line.

**Q: What if I want to always use subscription?**
A: Set `default_mode=AuthMode.SUBSCRIPTION` in your auth_strategy configuration.

**Q: What if I want to always use API?**
A: Set `default_mode=AuthMode.API` in your auth_strategy configuration.

---

## Related Documentation

- [Claude Subscriptions](https://claude.ai/settings)
- [Anthropic API Pricing](https://docs.anthropic.com/en/pricing)
- [Document Generation Workflow](./WORKFLOWS.md#document-generation)
- [Provider Configuration](./PROVIDER_CONFIG.md)

---

## Changelog

**v1.0 (2026-01-29):**
- Initial release
- Support for Pro, Max, Enterprise tiers
- Auto mode with dynamic routing
- First-time educational comparison
- Cost estimation and recommendations

---

**Questions?** Open an issue at [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
