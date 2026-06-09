---
description: Claude-Native Architecture Migration Guide: **Version:** v3.0.4 **Status:** Complete (Claude-Native) **Completed:** January 26, 2026 --- ## Overview Empathy Fra
---

# Claude-Native Architecture Migration Guide

**Version:** v3.0.4
**Status:** Complete (Claude-Native)
**Completed:** January 26, 2026

---

## Overview

Attune AI is transitioning to a **Claude-native architecture** to fully leverage Anthropic's advanced features and provide the best possible development experience for AI-powered workflows.

**Strategic Direction:**
Rather than maintaining compatibility with multiple LLM providers (OpenAI, Google Gemini, Ollama), we're focusing exclusively on Claude to unlock features that are impossible to achieve with multi-provider abstraction.

---

## Why Claude-Native?

### Unique Anthropic Features

1. **Prompt Caching (90% Cost Reduction)**
   - Cache repeated prompts (system messages, examples, context)
   - Reduce costs by up to 90% on cached content
   - Faster response times (cached content processed instantly)
   - [Learn more](https://docs.anthropic.com/claude/docs/prompt-caching)

2. **200K Context Window**
   - Largest context window available (vs 128K for competitors)
   - Process entire codebases in a single request
   - Maintain conversation context across long sessions
   - [Learn more](https://docs.anthropic.com/claude/docs/models-overview)

3. **Extended Thinking (Reasoning Transparency)**
   - See Claude's internal reasoning process
   - Debug AI decision-making
   - Improve prompt engineering with visibility
   - [Learn more](https://docs.anthropic.com/claude/docs/thinking)

4. **Computer Use & Tool Calling Optimizations**
   - Advanced tool use capabilities
   - Multi-step agentic workflows
   - Code execution and validation
   - [Learn more](https://docs.anthropic.com/claude/docs/tool-use)

### Simplification Benefits

By removing multi-provider support, we can:

- **Reduce codebase complexity** - Remove ~2,300 lines of provider abstraction code
- **Faster iteration** - No need to test against 4 different APIs
- **Better features** - Build Claude-specific optimizations without workarounds
- **Clearer positioning** - "The Claude framework" vs "Multi-LLM framework"

---

## Migration Timeline

### ✅ Phase 1: Deprecation Warnings (v4.8.0 - January 2026)

**Status:** Current Phase

**What's happening:**
- Deprecation warnings added to OpenAI, Google, Ollama, and Hybrid providers
- All existing code continues to work
- Documentation updated with migration guidance
- Users informed of upcoming changes

**What you should do:**
1. Run `attune version` to check you're on v4.8.0+
2. If you see deprecation warnings, start planning migration
3. Test your workflows with Anthropic provider
4. Report any issues or blockers

### ✅ Phase 2: Provider Removal (v5.0.0 - January 26, 2026)

**Status:** COMPLETE (BREAKING RELEASE)

**What changed:**
- OpenAI, Google Gemini, and Ollama providers **REMOVED**
- `primary_provider` config must be `"anthropic"` (only valid value)
- Hybrid mode **REMOVED** (ProviderMode.SINGLE only)
- Multi-provider abstractions **REMOVED**
- ~600 lines of provider abstraction code removed
- All tests updated to Anthropic-only

**Migration completed:**

1. ✅ MODEL_REGISTRY now contains only Anthropic models
2. ✅ ModelProvider enum reduced to ANTHROPIC only
3. ✅ ProviderMode enum reduced to SINGLE only
4. ✅ CLI commands updated (provider set/show)
5. ✅ All test files updated to use Anthropic
6. ✅ Fallback system simplified (tier-to-tier within Anthropic)

**For users upgrading from v4.x:**

1. Set `ANTHROPIC_API_KEY` environment variable
2. Update configuration: `provider: "anthropic"`
3. Remove references to OpenAI/Google/Ollama from your code
4. All workflows will automatically use Claude models

### 🎯 Phase 3: Claude-Native Features (v5.1.0 - Late February 2026)

**Status:** Planned

**What's coming:**
- Prompt caching enabled by default (90% cost reduction)
- Extended thinking support for debugging
- Optimized for Claude's 200K context window
- New Claude-specific workflow examples
- Performance optimizations for tool calling

---

## Migration Guide

### Step 1: Get Anthropic API Key

1. Sign up for Anthropic account: [https://console.anthropic.com/](https://console.anthropic.com/)
2. Navigate to Settings → API Keys
3. Create new API key
4. Copy the key (starts with `sk-ant-`)

### Step 2: Configure Environment

**Option A: Environment Variable (Recommended)**

```bash
# Add to ~/.bashrc, ~/.zshrc, or .env file
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Option B: Project .env File**

```bash
# Create .env in project root
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

**Option C: Attune Config File**

```bash
# Create ~/.attune/.env
mkdir -p ~/.attune
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > ~/.attune/.env
```

### Step 3: Update Provider Configuration

**Current configuration (deprecated):**

```yaml
# empathy.config.yml
provider:
  mode: single
  primary_provider: openai  # ⚠️ DEPRECATED

# Or hybrid mode
provider:
  mode: hybrid  # ⚠️ DEPRECATED
```

**New configuration:**

```yaml
# empathy.config.yml
provider:
  mode: single
  primary_provider: anthropic  # ✅ Required in v5.0.0
```

### Step 4: Update Workflow Definitions

**If you're using WorkflowConfig:**

```python
from attune.workflows.config import WorkflowConfig

# Before (deprecated)
config = WorkflowConfig(
    provider="openai",  # ⚠️ DEPRECATED
    models={
        "cheap": "gpt-4o-mini",
        "capable": "gpt-4o",
        "premium": "o1"
    }
)

# After (Claude-native)
config = WorkflowConfig(
    provider="anthropic",  # ✅ Use Claude models
    models={
        "cheap": "claude-3-5-haiku-20241022",
        "capable": "claude-sonnet-4-5",
        "premium": "claude-opus-4-5-20251101"
    }
)
```

**If you're using the Builder pattern:**

```python
from attune.workflows.builder import WorkflowBuilder
from attune.workflows.test_gen import TestGenerationWorkflow

# Provider is automatically detected from config
workflow = (
    WorkflowBuilder(TestGenerationWorkflow)
    .with_config(config)  # Config specifies anthropic
    .with_cache_enabled(True)
    .build()
)
```

### Step 5: Test Your Workflows

```bash
# Run your workflows with Anthropic provider
attune workflow run test-gen --input '{"file":"src/main.py"}'

# Check for deprecation warnings
attune workflow run my-workflow 2>&1 | grep DEPRECATION

# Verify API key is working
attune provider show
```

### Step 6: Update Dependencies (if needed)

```bash
# Upgrade to v4.8.0+ to get deprecation warnings
pip install --upgrade attune-ai

# When v5.0.0 is released (February 2026)
pip install --upgrade attune-ai>=5.0.0
```

---

## Model Recommendations

### Tier Mapping (Optimized for Claude)

| Tier | Model | Cost (per 1M tokens) | Best For |
|------|-------|----------------------|----------|
| **Cheap** | `claude-3-5-haiku-20241022` | $0.80 / $4.00 | Simple tasks, validation, formatting |
| **Capable** | `claude-sonnet-4-5` | $3.00 / $15.00 | Code generation, analysis, most workflows |
| **Premium** | `claude-opus-4-5-20251101` | $15.00 / $75.00 | Complex reasoning, architecture, critical decisions |

### When to Use Each Tier

**Cheap Tier (Haiku):**
- Syntax validation
- Code formatting
- Simple refactoring
- Documentation generation
- Fast iteration during development

**Capable Tier (Sonnet 4.5):**
- Test generation
- Code review
- Feature implementation
- Bug analysis
- Most production workflows

**Premium Tier (Opus 4.5):**
- Architecture design
- Complex debugging
- Security analysis
- Performance optimization
- Mission-critical decisions

---

## Cost Comparison

### Before: Multi-Provider Hybrid Mode

```
Workflow: Test Generation (10 files)
├─ Cheap: GPT-4o-mini ($0.15/M in, $0.60/M out)
├─ Capable: GPT-4o ($2.50/M in, $10.00/M out)
└─ Premium: o1 ($15.00/M in, $60.00/M out)

Total cost: ~$2.50 per run
No prompt caching available
```

### After: Claude-Native with Prompt Caching

```
Workflow: Test Generation (10 files)
├─ Cheap: Claude Haiku ($0.80/M in, $4.00/M out)
├─ Capable: Claude Sonnet 4.5 ($3.00/M in, $15.00/M out)
└─ Premium: Claude Opus 4.5 ($15.00/M in, $75.00/M out)

First run: ~$3.20
Subsequent runs (with cache): ~$0.32 (90% cheaper!)
```

**Prompt caching saves ~$2.88 per run after first execution.**

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"

**Solution:**
```bash
# Check if key is set
echo $ANTHROPIC_API_KEY

# If empty, add to your shell config
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

### "Provider 'openai' is deprecated"

**Solution:**
Update your configuration to use `anthropic`:

```yaml
# empathy.config.yml
provider:
  primary_provider: anthropic  # Changed from 'openai'
```

### "Model 'gpt-4o' not found"

**Solution:**
Update model IDs to Claude models:

```python
# Before
models = {"capable": "gpt-4o"}

# After
models = {"capable": "claude-sonnet-4-5"}
```

### "Deprecation warning spam"

**Solution:**
Warnings are shown once per session to avoid spam. To suppress entirely:

```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

**Note:** Better to migrate than suppress warnings!

---

## FAQ

### Q: Will my existing workflows break in v4.8.0?

**A:** No, all existing code continues to work. You'll see deprecation warnings, but functionality is unchanged.

### Q: When exactly will non-Anthropic providers be removed?

**A:** v5.0.0 (planned for February 2026). You have ~1 month to migrate.

### Q: What if I can't get an Anthropic API key?

**A:** Contact Anthropic support or consider using v4.x until you can migrate. We recommend migrating soon to benefit from new features.

### Q: Can I still use the framework offline with local models?

**A:** Not after v5.0.0. Ollama support is being removed. If offline usage is critical, stay on v4.x.

### Q: What about GPT-4's vision capabilities?

**A:** Claude Sonnet 4.5 and Opus 4.5 both support vision. Claude's vision is competitive with GPT-4o.

### Q: Will prompt caching work automatically?

**A:** Yes! In v5.1.0, prompt caching will be enabled by default. No code changes needed.

### Q: What if I prefer OpenAI/Google?

**A:** You can stay on v4.x (which will receive security patches through 2026), or fork the framework and maintain your own provider support.

### Q: Is this reversible?

**A:** Technical decision is reversible, but unlikely. We're committed to Claude-native architecture for the long term.

---

## Getting Help

### Report Issues

If you encounter migration problems:

1. Check [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
2. Create new issue with:
   - Current configuration
   - Error messages
   - What you've tried
   - Framework version (`attune version`)

### Community Support

- **Discussions:** [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)
- **Documentation:** [docs.attune-ai.dev](https://docs.attune-ai.dev)

### Migration Assistance

Need help migrating? We're here to help:

1. Open a discussion thread titled "Migration Help: [Your Use Case]"
2. Describe your current setup
3. Community and maintainers will assist

---

## What's Next?

After migrating to Claude:

1. **Enable prompt caching** (coming in v5.1.0) - 90% cost reduction
2. **Try extended thinking** - See Claude's reasoning process
3. **Use 200K context** - Process larger codebases
4. **Explore new workflows** - Claude-native examples coming soon

---

## Additional Resources

- [Anthropic Documentation](https://docs.anthropic.com/)
- [Claude Models Overview](https://docs.anthropic.com/claude/docs/models-overview)
- [Prompt Caching Guide](https://docs.anthropic.com/claude/docs/prompt-caching)
- [Extended Thinking Documentation](https://docs.anthropic.com/claude/docs/thinking)
- [Attune AI Changelog](../CHANGELOG.md)

---

**Questions?** Open an issue or discussion on GitHub.
**Timeline concerns?** Let us know - we're listening!

---

**Last Updated:** January 26, 2026
**Version:** v4.8.0
**Status:** Deprecation Phase (Phase 1/3)
