---
description: Anthropic-Only Architecture: Strategic Brainstorming: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Anthropic-Only Architecture: Strategic Brainstorming

**Date:** January 26, 2026
**Status:** 🤔 Discussion Draft
**Decision:** Pending

---

## The Question

Should we remove multi-provider support (OpenAI, Google Gemini, local models) and focus exclusively on Anthropic/Claude?

**Current state:**
- Framework supports 4 providers: Anthropic, OpenAI, Google, Local
- Tier routing works across providers
- Complex abstraction layer to handle provider differences

**Proposed state:**
- Anthropic/Claude only
- Simplified codebase
- Optimized for Claude-specific features
- Clearer value proposition

---

## Arguments FOR Anthropic-Only

### 1. **Simplification Benefits**

**Code reduction:**
- Remove provider abstraction layer (~500 lines)
- Remove OpenAI-specific code (~800 lines)
- Remove Google Gemini code (~600 lines)
- Remove local model support (~400 lines)
- **Total:** ~2,300 lines removed (6% of codebase)

**Cognitive load:**
- One API to learn, not four
- One set of quirks to handle
- One billing model to understand
- Simpler testing (no provider matrix)

### 2. **Claude-Specific Optimization**

**Features only Anthropic has:**
```python
# Prompt caching (90% cost reduction on repeated prompts)
messages = [{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": long_system_prompt,
            "cache_control": {"type": "ephemeral"}  # Anthropic-only
        }
    ]
}]

# Extended context (200K tokens)
# Other providers: 128K max

# Tool use with computer control
# Other providers: Limited tool use

# Thinking tokens (Claude 3.5 Sonnet v2)
# Other providers: Not available
```

**Current limitations:**
We can't fully leverage these features because we need compatibility with OpenAI/Gemini.

### 3. **Market Positioning**

**Claude Code integration:**
- Framework is already "Claude Code optimized" (per v4.6.5 changelog)
- Slash commands designed for Claude Code
- Socratic agents align with Anthropic's values
- Prompt caching is Anthropic-specific

**Clearer value proposition:**
```markdown
# Current (confusing):
"Multi-LLM framework optimized for Claude Code"
- Wait, so it's not Claude-only?
- Why optimize for Claude but support others?

# Proposed (clear):
"Claude-native development framework"
- Crystal clear positioning
- No hedging or confusion
- Matches Claude Code ecosystem
```

### 4. **Maintenance Burden**

**Testing matrix reduction:**
```
Current: 4 providers × 3 tiers × 20 workflows = 240 test combinations
Proposed: 1 provider × 3 tiers × 20 workflows = 60 test combinations

75% reduction in provider-related testing
```

**Dependency management:**
```python
# Current: Must track all provider SDKs
openai>=1.0.0
anthropic>=0.18.0
google-generativeai>=0.3.0
# + all their transitive dependencies

# Proposed: One SDK
anthropic>=0.18.0
```

### 5. **Alignment with Rename Plan**

You mentioned renaming from "attune-ai" to something else.

**Names that work with Anthropic-only:**
- `claude-workflow-engine`
- `claude-dev-framework`
- `anthropic-workflows`
- `claude-native`

**Names that DON'T work:**
- Any "LLM" or "multi-model" branding

---

## Arguments AGAINST Anthropic-Only

### 1. **Breaks Existing Users**

**Who uses other providers?**
Let's find out:

```bash
# Check telemetry data
sqlite3 .empathy/history.db "SELECT provider, COUNT(*) FROM workflow_runs GROUP BY provider"

# Expected output:
# anthropic | 489
# openai    | 12
# google    | 3
# local     | 0
```

If >10% of runs use non-Anthropic providers, this is a breaking change.

**Migration pain:**
- Users on OpenAI API credits can't switch easily
- Some orgs ban Anthropic due to procurement/legal
- Some use cases genuinely need GPT-4 specifically

### 2. **Market Risk**

**What if Anthropic...?**
- Raises prices 10x (unlikely but possible)
- Has extended downtime (happened in 2023)
- Pivots away from developer tools
- Gets acquired and changes strategy

**Hedge value:**
Multi-provider support is insurance against vendor lock-in.

### 3. **Feature Gaps**

**Things OpenAI does better:**
- GPT-4o vision (better OCR than Claude)
- Whisper API (speech-to-text)
- DALL-E integration (image generation)
- JSON mode with schema enforcement

**Things local models offer:**
- No API costs
- Full data privacy
- Air-gapped deployments
- Custom fine-tuning

### 4. **Community Expectations**

**"Framework" implies flexibility:**
Users expect frameworks to support multiple backends.

- Django: Multiple databases
- LangChain: Multiple providers
- Haystack: Multiple providers

Going single-provider feels like a regression.

---

## Middle Ground Options

### Option A: Anthropic First-Class, Others Community

**Implementation:**
```python
# Core: Anthropic only
from attune.providers import AnthropicProvider  # Built-in

# Plugins: Other providers
from attune_openai import OpenAIProvider  # Separate package
from attune_google import GoogleProvider   # Separate package
```

**Benefits:**
- Core codebase simplified
- Anthropic features fully leveraged
- Community can maintain other providers
- Clear "official" vs "community" distinction

**Precedent:** Django does this (postgres is "first-class", others are external)

### Option B: Keep Abstraction, Add "Native Mode"

**Implementation:**
```python
# Normal mode: Provider abstraction
workflow = TestGenerationWorkflow(provider="anthropic")

# Native mode: Direct Anthropic API access
from attune.anthropic import NativeAnthropicWorkflow
workflow = NativeAnthropicWorkflow(
    prompt_caching=True,
    extended_thinking=True,
    computer_use=False
)
```

**Benefits:**
- Best of both worlds
- Users choose their mode
- No breaking changes
- Can deprecate abstraction later

### Option C: Fork Into Two Projects

**Two separate packages:**
```
attune-ai (v4.x)
├── Multi-provider support
├── Maintenance mode
└── Community-driven

claude-native (v1.0)
├── Anthropic-only
├── Full Claude features
└── Active development
```

**Benefits:**
- Clean break
- No migration pain for existing users
- Fresh start with better architecture
- Clear positioning

---

## Technical Implementation Path

If we decide to go Anthropic-only, here's the plan:

### Phase 1: Deprecation (v4.8.0)

```python
# Add warnings
@deprecated("OpenAI provider will be removed in v5.0. Use Anthropic instead.")
class OpenAIProvider:
    pass

# Update docs
"""
⚠️ DEPRECATION NOTICE
OpenAI, Google, and Local providers are deprecated and will be removed in v5.0.
Please migrate to Anthropic: https://...
"""
```

### Phase 2: Extract Plugins (v4.9.0)

```bash
# Create separate packages
empathy-openai-provider/
empathy-google-provider/
empathy-local-provider/

# Update main package
pip install attune-ai  # Anthropic only
pip install empathy-openai-provider  # Opt-in OpenAI support
```

### Phase 3: Remove (v5.0.0)

```python
# Delete provider files
rm src/attune/providers/openai.py
rm src/attune/providers/google.py
rm src/attune/providers/local.py

# Simplify base classes
# No more provider abstraction
```

---

## Strategic Decision Framework

### Ask These Questions:

1. **Usage data:** What % of workflows use non-Anthropic providers?
   - <5%: Safe to remove
   - 5-20%: Consider plugin approach
   - >20%: Keep multi-provider

2. **User feedback:** What do users say when asked?
   - Survey: "Would Anthropic-only be a dealbreaker?"

3. **Competitor analysis:** What do similar tools do?
   - LangChain: Multi-provider (but bloated)
   - Cursor: Anthropic + OpenAI
   - GitHub Copilot: OpenAI-only (works fine)

4. **Resource constraints:** Can we maintain 4 providers?
   - Small team → Focus on one
   - Large community → Community can help

5. **Long-term vision:** Where do we want to be in 2 years?
   - "The Claude framework" → Anthropic-only
   - "LLM workflow engine" → Multi-provider

---

## Recommended Approach (My Take)

### Short-term (v4.8.0 - v4.9.0): **Option B**

Keep abstraction, add "Native Mode" for Anthropic-specific features:

```python
# For users who need multi-provider
workflow = TestGenerationWorkflow(provider="anthropic")

# For users who want full Claude features
from attune.claude import ClaudeNativeWorkflow
workflow = ClaudeNativeWorkflow(
    model="claude-3-5-sonnet-20241022",
    prompt_caching=True,
    extended_thinking=True,
)
```

**Why:**
- No breaking changes
- Test market appetite for Anthropic-only
- Gather data on provider usage
- Reversible decision

### Mid-term (v5.0.0): **Option A**

Based on data from v4.8-4.9, move others to plugins:

```python
# Core: Anthropic (90%+ of usage)
from attune import Workflow

# Plugins: Others (community-maintained)
from empathy_openai import OpenAIWorkflow
from empathy_google import GoogleWorkflow
```

**Why:**
- Data-driven decision
- Community can maintain niche providers
- Core stays focused

### Long-term (v6.0.0): **Full Anthropic**

If plugins see <1% usage, remove entirely:

```python
# Just Anthropic
from attune import Workflow
# That's it.
```

---

## Questions for You

To help finalize this decision, I need to understand:

### 1. Your Vision

**What's the 2-year vision for this framework?**
- "The go-to framework for Claude developers"
- "A flexible LLM workflow engine"
- "The best way to build AI agents"

### 2. Your Users

**Who are your primary users?**
- Solo developers using Claude Code
- Teams with Anthropic enterprise accounts
- Open-source contributors
- Companies with multi-vendor LLM strategies

### 3. Your Resources

**Can you maintain 4 providers?**
- Do you have community contributors for OpenAI/Google?
- Or is this mostly a solo/small-team effort?

### 4. Your Constraints

**Are there technical reasons to keep multi-provider?**
- Fallback strategy for outages
- Cost optimization (use cheaper provider for cheap tier)
- Compliance requirements (some orgs require multi-vendor)

### 5. The Rename

**What new name are you considering?**
- If it includes "Claude" → Go Anthropic-only
- If it's generic → Keep multi-provider

---

## Data We Should Gather

Before deciding, let's check:

```bash
# 1. Provider usage distribution
sqlite3 .empathy/history.db "
SELECT
    provider,
    COUNT(*) as runs,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM workflow_runs), 2) as percent
FROM workflow_runs
GROUP BY provider
ORDER BY runs DESC"

# 2. Check for non-Anthropic imports in user code
grep -r "OpenAIProvider\|GoogleProvider" --include="*.py" | wc -l

# 3. Test coverage by provider
pytest --collect-only | grep -E "openai|google|local" | wc -l
```

---

## My Recommendation (TL;DR)

**Go Anthropic-only, but do it gradually:**

**v4.8.0 (Feb 2026):** Add deprecation warnings + Native Mode
**v4.9.0 (Mar 2026):** Extract plugins, gather data
**v5.0.0 (May 2026):** Remove if usage <5%

**Reasoning:**
1. You're already "Claude Code optimized" (v4.6.5)
2. Simpler codebase = faster iteration
3. Anthropic features are compelling (prompt caching!)
4. Gradual migration gives users time to adapt
5. Data-driven final decision in v5.0

**Risk mitigation:**
- Keep plugin architecture option open
- Survey users before v5.0
- Document migration path clearly

---

## Next Steps

1. **Discuss:** Share your vision, constraints, and preferences
2. **Measure:** Run the SQL queries to see actual provider usage
3. **Prototype:** Build "Native Mode" for Anthropic-specific features
4. **Decide:** Based on data + vision, choose path forward
5. **Execute:** Implement chosen approach with clear communication

---

**What do you think? Let's brainstorm together!**

Questions to explore:
- What % of your workflows use non-Anthropic providers?
- What's your ideal positioning: "Claude framework" vs "LLM framework"?
- Are there specific OpenAI/Gemini features your users depend on?
- How much does the "insurance" of multi-provider matter to you?
