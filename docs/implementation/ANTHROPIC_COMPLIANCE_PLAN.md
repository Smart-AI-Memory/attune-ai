# Anthropic Best Practices Compliance Plan

**Version:** 1.0
**Created:** 2026-02-07
**Branch:** feature/healthcare-cds-agents (also applies to main)
**Status:** Ready for Implementation
**Format:** XML-Enhanced Prompts (per `.claude/rules/empathy/xml-enhanced-prompts.md`)

---

## Executive Summary

Audit identified **22 compliance issues** across the attune-ai codebase. Issues exist on both `main` and `feature/healthcare-cds-agents` branches. The `main` branch has additional gaps (no hooks, no security guard). This plan provides self-contained, executable task prompts organized by severity.

| Severity | Count | Branch Impact |
|----------|-------|---------------|
| CRITICAL | 5     | Both branches |
| HIGH     | 6     | Mixed         |
| MEDIUM   | 7     | Mixed         |
| LOW      | 4     | Feature only  |

---

## Task Dependency Graph

```text
Task 1 (SDK constraint) ─┐
Task 2 (Model IDs)  ─────┼── Task 3 (Provider error handling)
Task 4 (Pricing)  ────────┘
Task 5 (Security guard) ──── standalone
Task 6 (MCP location) ────── Task 7 (MCP SDK migration)
Task 8 (Streaming) ───────── depends on Task 1
Task 9 (Thinking budget) ─── standalone
Task 10 (Duplicate rules) ── standalone
Task 11 (CLAUDE.md trim) ─── standalone
Task 12 (Provider metadata) ─ standalone
Task 13 (Vision capability) ─ part of Task 2
Task 14 (Coverage target) ── standalone
```

---

## CRITICAL Priority Tasks

### Task 1: Update Anthropic SDK Version Constraint

```xml
<task id="C1" name="sdk-version-constraint">
  <objective>
    Remove the <1.0.0 ceiling on the anthropic SDK dependency so the project
    can use the latest SDK features (streaming helpers, typed errors, Agent SDK).
    Affects both main and feature branches.
  </objective>

  <context>
    <existing-code path="pyproject.toml" lines="60">
      "anthropic>=0.25.0,<1.0.0",  # Core LLM provider (direct SDK usage)
    </existing-code>
    <existing-code path="pyproject.toml" lines="74">
      anthropic = ["anthropic>=0.25.0,<1.0.0"]
    </existing-code>
    <existing-code path="pyproject.toml" lines="80">
      "anthropic>=0.25.0,<1.0.0",
    </existing-code>
    <note>
      The anthropic Python SDK is currently at 1.x+. The <1.0.0 ceiling
      blocks access to typed error classes (RateLimitError, APIConnectionError),
      streaming helpers, and the Agent SDK. The SDK follows semver and
      maintains backward compatibility within major versions.
    </note>
  </context>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="line 60 (core dependencies)">
        BEFORE: "anthropic>=0.25.0,<1.0.0",  # Core LLM provider (direct SDK usage)
        AFTER:  "anthropic>=0.40.0",  # Core LLM provider - needs 0.40+ for typed errors
      </change>
      <change location="line 74 (optional anthropic)">
        BEFORE: anthropic = ["anthropic>=0.25.0,<1.0.0"]
        AFTER:  anthropic = ["anthropic>=0.40.0"]
      </change>
      <change location="line 80 (llm bundle)">
        BEFORE: "anthropic>=0.25.0,<1.0.0",
        AFTER:  "anthropic>=0.40.0",
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv pip install -e ".[llm]" succeeds without version conflicts</check>
    <check>python -c "import anthropic; print(anthropic.__version__)" prints 0.40+</check>
    <check>python -c "from anthropic import RateLimitError" succeeds (typed errors available)</check>
    <check>uv run pytest tests/ passes (no regressions)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Breaking API changes in newer SDK versions. Mitigate by pinning minimum
      to 0.40.0 (known stable) rather than removing floor entirely. Run full
      test suite after upgrade.
    </risk>
  </risks>
</task>
```

---

### Task 2: Update Model IDs to Claude 4.5/4.6 Family

```xml
<task id="C2" name="update-model-ids">
  <objective>
    Update the MODEL_REGISTRY to use correct, current model IDs for the
    Claude 4.5/4.6 family. Fix Haiku vision support flag. Affects both branches.
  </objective>

  <context>
    <existing-code path="src/attune/models/registry.py" lines="125-161">
      MODEL_REGISTRY: dict[str, dict[str, ModelInfo]] = {
          "anthropic": {
              "cheap": ModelInfo(
                  id="claude-3-5-haiku-20241022",      # WRONG
                  ...
                  supports_vision=False,                 # WRONG: Haiku 4.5 supports vision
              ),
              "capable": ModelInfo(
                  id="claude-sonnet-4-5",               # OK (alias works)
                  ...
              ),
              "premium": ModelInfo(
                  id="claude-opus-4-5-20251101",        # WRONG
                  ...
              ),
          },
      }
    </existing-code>
    <note>
      Current Claude model IDs (as of Feb 2026):
      - Opus 4.6:  claude-opus-4-6
      - Sonnet 4.5: claude-sonnet-4-5-20250929
      - Haiku 4.5:  claude-haiku-4-5-20251001
      All models in the 4.5/4.6 family support vision.
    </note>
  </context>

  <files-to-modify>
    <file path="src/attune/models/registry.py">
      <change location="lines 125-161 MODEL_REGISTRY">
        BEFORE:
            "cheap": ModelInfo(
                id="claude-3-5-haiku-20241022",
                provider="anthropic",
                tier="cheap",
                input_cost_per_million=0.80,
                output_cost_per_million=4.00,
                max_tokens=8192,
                supports_vision=False,
                supports_tools=True,
            ),
            "capable": ModelInfo(
                id="claude-sonnet-4-5",
                ...
            ),
            "premium": ModelInfo(
                id="claude-opus-4-5-20251101",
                provider="anthropic",
                tier="premium",
                input_cost_per_million=15.00,
                output_cost_per_million=75.00,
                max_tokens=8192,
                supports_vision=True,
                supports_tools=True,
            ),

        AFTER:
            "cheap": ModelInfo(
                id="claude-haiku-4-5-20251001",
                provider="anthropic",
                tier="cheap",
                input_cost_per_million=1.00,
                output_cost_per_million=5.00,
                max_tokens=8192,
                supports_vision=True,
                supports_tools=True,
            ),
            "capable": ModelInfo(
                id="claude-sonnet-4-5-20250929",
                provider="anthropic",
                tier="capable",
                input_cost_per_million=3.00,
                output_cost_per_million=15.00,
                max_tokens=8192,
                supports_vision=True,
                supports_tools=True,
            ),
            "premium": ModelInfo(
                id="claude-opus-4-6",
                provider="anthropic",
                tier="premium",
                input_cost_per_million=5.00,
                output_cost_per_million=25.00,
                max_tokens=8192,
                supports_vision=True,
                supports_tools=True,
            ),
      </change>
      <change location="line 128 comment">
        BEFORE: # Intelligent fallback: Sonnet 4.5 → Opus 4.5 (5x cost increase for complex tasks)
        AFTER:  # Intelligent fallback: Sonnet 4.5 → Opus 4.6 (~1.7x cost increase for complex tasks)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.models.registry import get_model; m = get_model('anthropic', 'cheap'); assert m.id == 'claude-haiku-4-5-20251001'"</check>
    <check>python -c "from attune.models.registry import get_model; m = get_model('anthropic', 'premium'); assert m.id == 'claude-opus-4-6'"</check>
    <check>python -c "from attune.models.registry import get_model; m = get_model('anthropic', 'cheap'); assert m.supports_vision is True"</check>
    <check>uv run pytest tests/ -k "registry or model" passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Tests may assert old model IDs. Search for "claude-3-5-haiku" and
      "claude-opus-4-5" in tests/ and update accordingly.
    </risk>
  </risks>
</task>
```

---

### Task 3: Update TIER_PRICING Constants

```xml
<task id="C3" name="update-tier-pricing">
  <objective>
    Update the TIER_PRICING backward-compat dict to match the new model pricing.
    Affects both branches.
  </objective>

  <context>
    <existing-code path="src/attune/models/registry.py" lines="468-472">
      TIER_PRICING: dict[str, dict[str, float]] = {
          "cheap": {"input": 0.80, "output": 4.00},  # Haiku 3.5 pricing
          "capable": {"input": 3.00, "output": 15.00},  # Sonnet 4 pricing
          "premium": {"input": 15.00, "output": 75.00},  # Opus 4.5 pricing
      }
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/models/registry.py">
      <change location="lines 468-472">
        BEFORE:
        TIER_PRICING: dict[str, dict[str, float]] = {
            "cheap": {"input": 0.80, "output": 4.00},  # Haiku 3.5 pricing
            "capable": {"input": 3.00, "output": 15.00},  # Sonnet 4 pricing
            "premium": {"input": 15.00, "output": 75.00},  # Opus 4.5 pricing
        }

        AFTER:
        TIER_PRICING: dict[str, dict[str, float]] = {
            "cheap": {"input": 1.00, "output": 5.00},  # Haiku 4.5 pricing
            "capable": {"input": 3.00, "output": 15.00},  # Sonnet 4.5 pricing
            "premium": {"input": 5.00, "output": 25.00},  # Opus 4.6 pricing
        }
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from attune.models.registry import TIER_PRICING; assert TIER_PRICING['premium']['input'] == 5.00"</check>
    <check>python -c "from attune.models.registry import TIER_PRICING; assert TIER_PRICING['cheap']['input'] == 1.00"</check>
    <check>uv run pytest tests/ -k "pricing or cost" passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Cost tracking reports may show different values. This is correct —
      the old pricing was wrong. No code change needed beyond the constants.
    </risk>
  </risks>
</task>
```

---

### Task 4: Add Anthropic-Specific Error Handling

```xml
<task id="C4" name="anthropic-error-handling">
  <objective>
    Import and handle Anthropic-specific error types (RateLimitError,
    APIConnectionError, APITimeoutError) in the provider instead of
    catching generic exceptions. Depends on Task C1 (SDK upgrade).
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="107-116">
      try:
          import anthropic
          self.client = anthropic.AsyncAnthropic(api_key=api_key)
      except ImportError as e:
          raise ImportError(
              "anthropic package required. Install with: pip install anthropic",
          ) from e
    </existing-code>
    <existing-code path="attune_llm/providers.py" lines="174">
      response = await self.client.messages.create(**api_kwargs)
    </existing-code>
    <note>
      The anthropic SDK provides typed exceptions: RateLimitError,
      APIConnectionError, APITimeoutError, APIStatusError, AuthenticationError.
      These allow targeted retry logic and better error messages.
    </note>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="imports section (after line 110 import anthropic)">
        BEFORE:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)

        AFTER:
            import anthropic
            from anthropic import (
                APIConnectionError,
                APITimeoutError,
                RateLimitError,
            )
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
      </change>
      <change location="line 174 (API call)">
        BEFORE:
        response = await self.client.messages.create(**api_kwargs)

        AFTER:
        try:
            response = await self.client.messages.create(**api_kwargs)
        except RateLimitError as e:
            logger.warning("Rate limited by Anthropic API: %s", e)
            raise
        except APITimeoutError as e:
            logger.error("Anthropic API timeout: %s", e)
            raise
        except APIConnectionError as e:
            logger.error("Anthropic API connection error: %s", e)
            raise
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -c "from anthropic import RateLimitError, APIConnectionError, APITimeoutError" succeeds</check>
    <check>uv run pytest tests/ -k "provider or anthropic" passes</check>
    <check>grep -n "RateLimitError" attune_llm/providers.py returns matches</check>
  </validation>

  <risks>
    <risk severity="medium">
      Existing retry logic in src/attune/resilience/retry.py catches generic
      exceptions. Verify these typed exceptions bubble up correctly to the
      retry decorator. May need to update retry to specifically handle
      RateLimitError with longer backoff.
    </risk>
  </risks>
</task>
```

---

### Task 5: Security Guard Fail-Closed

```xml
<task id="C5" name="security-guard-fail-closed">
  <objective>
    Change the security guard hook to fail-closed (block) when it receives
    invalid input, instead of the current fail-open behavior. Feature branch
    only (main has no security guard at all).
  </objective>

  <context>
    <existing-code path="attune_llm/hooks/scripts/security_guard.py" lines="158-187">
      def main(context: dict[str, Any]) -> dict[str, Any]:
          tool_name = context.get("tool_name", "")
          tool_input = context.get("tool_input", {})

          if not tool_name:
              # No tool info — allow by default (defensive)
              return {"allowed": True}
          ...
    </existing-code>
    <existing-code path="attune_llm/hooks/scripts/security_guard.py" lines="190-218">
      def _read_stdin_context() -> dict[str, Any]:
          if sys.stdin.isatty():
              return {}
          try:
              raw = sys.stdin.read().strip()
              if raw:
                  return json.loads(raw)
          except (json.JSONDecodeError, ValueError) as e:
              logger.debug("Could not parse stdin JSON: %s", e)
          return {}  # Returns empty dict on parse failure → main() allows

      if __name__ == "__main__":
          ...
          context = _read_stdin_context()
          result = main(context)
          if not result.get("allowed", True):  # Defaults to True on missing key
              ...
    </existing-code>
    <note>
      Security-critical code should fail-closed: if we can't parse the input
      or determine safety, BLOCK the action. The current code returns
      {"allowed": True} when stdin is empty, malformed, or missing tool_name.
      However, we need to be careful: Claude Code sends valid JSON for every
      hook invocation, so invalid JSON likely means a real problem.
    </note>
  </context>

  <files-to-modify>
    <file path="attune_llm/hooks/scripts/security_guard.py">
      <change location="lines 170-173 (no tool_name)">
        BEFORE:
          if not tool_name:
              # No tool info — allow by default (defensive)
              return {"allowed": True}

        AFTER:
          if not tool_name:
              # Fail-closed: missing tool_name means malformed input
              return {"allowed": False, "reason": "Security guard: missing tool_name in hook context"}
      </change>
      <change location="lines 196-205 (_read_stdin_context)">
        BEFORE:
          if sys.stdin.isatty():
              return {}
          try:
              raw = sys.stdin.read().strip()
              if raw:
                  return json.loads(raw)
          except (json.JSONDecodeError, ValueError) as e:
              logger.debug("Could not parse stdin JSON: %s", e)
          return {}

        AFTER:
          if sys.stdin.isatty():
              # Interactive mode (manual testing) — return sentinel
              return {"_parse_error": True}
          try:
              raw = sys.stdin.read().strip()
              if raw:
                  return json.loads(raw)
              return {"_parse_error": True}
          except (json.JSONDecodeError, ValueError) as e:
              logger.warning("Security guard: could not parse stdin JSON: %s", e)
              return {"_parse_error": True}
      </change>
      <change location="lines 208-218 (__main__ block)">
        BEFORE:
        if __name__ == "__main__":
            logging.basicConfig(level=logging.WARNING, format="%(message)s")
            context = _read_stdin_context()
            result = main(context)

            if not result.get("allowed", True):
                # Block: print reason to stderr, exit 2
                print(result["reason"], file=sys.stderr)
                sys.exit(2)

            # Allow: exit 0

        AFTER:
        if __name__ == "__main__":
            logging.basicConfig(level=logging.WARNING, format="%(message)s")
            context = _read_stdin_context()

            if context.get("_parse_error"):
                print("Security guard: failed to parse hook input — blocking", file=sys.stderr)
                sys.exit(2)

            result = main(context)

            if not result.get("allowed", False):
                # Block: print reason to stderr, exit 2
                reason = result.get("reason", "Security guard: action not explicitly allowed")
                print(reason, file=sys.stderr)
                sys.exit(2)

            # Allow: exit 0
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>echo '' | python attune_llm/hooks/scripts/security_guard.py; test $? -eq 2 (empty stdin blocks)</check>
    <check>echo 'invalid json' | python attune_llm/hooks/scripts/security_guard.py; test $? -eq 2 (bad JSON blocks)</check>
    <check>echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python attune_llm/hooks/scripts/security_guard.py; test $? -eq 0 (valid command allowed)</check>
    <check>echo '{"tool_name":"Bash","tool_input":{"command":"eval(x)"}}' | python attune_llm/hooks/scripts/security_guard.py; test $? -eq 2 (eval blocked)</check>
  </validation>

  <risks>
    <risk severity="high">
      Fail-closed may block legitimate tool calls if Claude Code changes its
      hook protocol. Mitigate by logging blocked actions clearly to stderr so
      users can diagnose. Add a SECURITY_GUARD_PERMISSIVE=1 env var escape
      hatch for debugging only.
    </risk>
  </risks>
</task>
```

---

## HIGH Priority Tasks

### Task 6: Move MCP Config to Project Root

```xml
<task id="H1" name="mcp-config-location">
  <objective>
    Move MCP server configuration from .claude/mcp.json to .mcp.json at
    project root, per Anthropic best practices. Affects both branches.
  </objective>

  <context>
    <existing-code path=".claude/mcp.json">
      {
        "mcpServers": {
          "empathy": {
            "command": "python",
            "args": ["-m", "attune.mcp.server"],
            "env": {
              "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
              "PYTHONPATH": "${workspaceFolder}/src"
            },
            "disabled": false
          }
        }
      }
    </existing-code>
    <note>
      Claude Code looks for .mcp.json at the project root for MCP server
      configuration. The .claude/mcp.json location may work in some versions
      but .mcp.json is the documented standard.
    </note>
  </context>

  <files-to-create>
    <file path=".mcp.json">
      Same content as .claude/mcp.json (copy and verify)
    </file>
  </files-to-create>

  <files-to-modify>
    <file path=".claude/mcp.json">
      DELETE this file after creating .mcp.json
    </file>
    <file path=".gitignore">
      <change location="add near MCP/Claude section">
        Ensure .mcp.json is NOT in .gitignore (it should be committed)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>test -f .mcp.json (file exists at root)</check>
    <check>test ! -f .claude/mcp.json (old file removed)</check>
    <check>python -m json.tool .mcp.json (valid JSON)</check>
  </validation>

  <risks>
    <risk severity="low">
      If Claude Code in some versions only reads .claude/mcp.json, the MCP
      server won't auto-start. Test with actual Claude Code after migration.
    </risk>
  </risks>
</task>
```

---

### Task 7: Add Streaming Support

```xml
<task id="H2" name="streaming-support">
  <objective>
    Add a streaming generation method to AnthropicProvider using the SDK's
    messages.stream() helper for real-time output in workflows.
    Depends on Task C1 (SDK upgrade).
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="124-174">
      async def generate(self, messages, system_prompt, temperature, max_tokens, **kwargs) -> LLMResponse:
          # ... builds api_kwargs ...
          response = await self.client.messages.create(**api_kwargs)
    </existing-code>
    <note>
      The Anthropic SDK provides client.messages.stream() which yields
      events as they arrive. This is critical for long-running workflows
      where users need to see progress. The stream context manager handles
      SSE parsing automatically.
    </note>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="after generate() method (~line 220)">
        ADD new method:

        async def generate_stream(
            self,
            messages: list[dict[str, str]],
            system_prompt: str | None = None,
            temperature: float = 0.7,
            max_tokens: int = 1024,
            **kwargs,
        ) -> AsyncIterator[str]:
            """Stream response tokens from Anthropic API.

            Yields text chunks as they arrive for real-time output.

            Args:
                messages: Conversation messages.
                system_prompt: Optional system prompt.
                temperature: Sampling temperature.
                max_tokens: Maximum output tokens.

            Yields:
                Text chunks as they are generated.
            """
            api_kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt and self.use_prompt_caching:
                api_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    },
                ]
            elif system_prompt:
                api_kwargs["system"] = system_prompt

            api_kwargs.update(kwargs)

            async with self.client.messages.stream(**api_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -n "generate_stream" attune_llm/providers.py returns matches</check>
    <check>grep -n "messages.stream" attune_llm/providers.py returns matches</check>
    <check>uv run pytest tests/ -k "provider" passes</check>
  </validation>

  <risks>
    <risk severity="medium">
      Streaming changes the response pattern. Callers expect LLMResponse,
      but streaming yields text chunks. Keep both methods — generate() for
      structured responses, generate_stream() for real-time output.
    </risk>
  </risks>
</task>
```

---

### Task 8: Fix Provider Metadata

```xml
<task id="H3" name="fix-provider-metadata">
  <objective>
    Fix hardcoded "claude-3" model_family in provider metadata to be
    dynamically derived from the actual model ID being used.
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="190-195">
      metadata = {
          "input_tokens": response.usage.input_tokens,
          "output_tokens": response.usage.output_tokens,
          "provider": "anthropic",
          "model_family": "claude-3",
      }
    </existing-code>
    <note>
      With models like claude-opus-4-6 and claude-sonnet-4-5, hardcoding
      "claude-3" is wrong and will confuse cost tracking and analytics.
    </note>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="lines 190-195">
        BEFORE:
        metadata = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "provider": "anthropic",
            "model_family": "claude-3",
        }

        AFTER:
        metadata = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "provider": "anthropic",
            "model": self.model,
        }
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -n "model_family.*claude-3" attune_llm/providers.py returns NO matches</check>
    <check>uv run pytest tests/ -k "provider" passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Code that reads metadata["model_family"] will break. Search for
      "model_family" across the codebase and update consumers to use
      metadata["model"] instead.
    </risk>
  </risks>
</task>
```

---

### Task 9: Fix Provider Docstring

```xml
<task id="H4" name="fix-provider-docstring">
  <objective>
    Update the AnthropicProvider docstring from "Claude 3 family" to
    reflect the current Claude 4.5/4.6 model family.
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="75-83">
      class AnthropicProvider(BaseLLMProvider):
          """Anthropic (Claude) provider with enhanced features.

          Supports Claude 3 family models with advanced capabilities:
          - Extended context windows (200K tokens)
          - Prompt caching for faster repeated queries
          - Thinking mode for complex reasoning
          - Batch processing for cost optimization
          """
    </existing-code>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="lines 76-83">
        BEFORE:
          """Anthropic (Claude) provider with enhanced features.

          Supports Claude 3 family models with advanced capabilities:
          - Extended context windows (200K tokens)
          - Prompt caching for faster repeated queries
          - Thinking mode for complex reasoning
          - Batch processing for cost optimization
          """

        AFTER:
          """Anthropic (Claude) provider with enhanced features.

          Supports Claude 4.5/4.6 family models with advanced capabilities:
          - Extended context windows (200K tokens)
          - Prompt caching for faster repeated queries
          - Extended thinking for complex reasoning
          - Batch processing for cost optimization
          - Streaming output for real-time workflows
          """
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -n "Claude 3 family" attune_llm/providers.py returns NO matches</check>
  </validation>

  <risks>
    <risk severity="none">Documentation-only change, no runtime impact.</risk>
  </risks>
</task>
```

---

### Task 10: Remove Duplicate Rules Directories

```xml
<task id="H5" name="remove-duplicate-rules">
  <objective>
    Remove the duplicate .claude/rules/attune/ directory which is an exact
    copy of .claude/rules/empathy/. Feature branch only (main doesn't have it).
  </objective>

  <context>
    <note>
      The feature branch has two identical rule directories:
      - .claude/rules/empathy/ (original, 15 files)
      - .claude/rules/attune/ (copy, 15 identical files)
      Both are loaded by Claude Code, doubling the context window usage.
      Main branch only has empathy/ — the attune/ copy was introduced
      on the feature branch.
    </note>
  </context>

  <files-to-modify>
    <file path=".claude/rules/attune/">
      DELETE entire directory (all 15 files are duplicates of empathy/)
    </file>
  </files-to-modify>

  <validation>
    <check>test ! -d .claude/rules/attune (directory removed)</check>
    <check>test -d .claude/rules/empathy (original still exists)</check>
    <check>ls .claude/rules/empathy/*.md | wc -l returns 15+ (all rules intact)</check>
  </validation>

  <risks>
    <risk severity="low">
      If any code references .claude/rules/attune/ paths specifically,
      those references need updating. Search for "rules/attune" in the
      codebase before deleting.
    </risk>
  </risks>
</task>
```

---

### Task 11: Backport Hooks to Main Branch

```xml
<task id="H6" name="backport-hooks-to-main">
  <objective>
    When merging feature branch to main, ensure .claude/settings.json and
    attune_llm/hooks/scripts/ are included. Main currently has NO hooks.
  </objective>

  <context>
    <note>
      The main branch (commit 9d398fe4) is missing:
      - .claude/settings.json (no hook configuration at all)
      - attune_llm/hooks/scripts/security_guard.py
      - attune_llm/hooks/scripts/session_start.py
      - attune_llm/hooks/scripts/session_end.py
      These are all present on the feature branch. A normal merge will
      carry them over, but this task documents what main is missing so
      reviewers verify the merge includes these files.
    </note>
  </context>

  <validation>
    <check>After merge: test -f .claude/settings.json on main</check>
    <check>After merge: test -f attune_llm/hooks/scripts/security_guard.py on main</check>
    <check>git diff main -- .claude/settings.json shows the file was added</check>
  </validation>

  <risks>
    <risk severity="low">
      Merge conflict if main independently adds settings.json.
      Unlikely given main's current state.
    </risk>
  </risks>
</task>
```

---

## MEDIUM Priority Tasks

### Task 12: Make Extended Thinking Budget Configurable

```xml
<task id="M1" name="configurable-thinking-budget">
  <objective>
    Replace the hardcoded 2000-token thinking budget with a configurable
    parameter that allows callers to set appropriate budgets per task.
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="90-91">
      use_thinking: bool = False,
    </existing-code>
    <existing-code path="attune_llm/providers.py" lines="164-168">
      if self.use_thinking:
          api_kwargs["thinking"] = {
              "type": "enabled",
              "budget_tokens": 2000,
          }
    </existing-code>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="line 90-91 __init__ params">
        BEFORE:
        use_thinking: bool = False,

        AFTER:
        use_thinking: bool = False,
        thinking_budget: int = 10000,
      </change>
      <change location="line 94+ __init__ body">
        ADD after self.use_batch:
        self.thinking_budget = thinking_budget
      </change>
      <change location="lines 164-168">
        BEFORE:
        if self.use_thinking:
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 2000,
            }

        AFTER:
        if self.use_thinking:
            api_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep -n "budget_tokens.*2000" attune_llm/providers.py returns NO matches</check>
    <check>grep -n "thinking_budget" attune_llm/providers.py returns matches in __init__ and generate</check>
    <check>uv run pytest tests/ -k "provider or thinking" passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Higher budgets increase cost. The default of 10000 is reasonable for
      most tasks. Complex tasks may need 50000+. Document in docstring.
    </risk>
  </risks>
</task>
```

---

### Task 13: Trim CLAUDE.md

```xml
<task id="M2" name="trim-claude-md">
  <objective>
    Reduce CLAUDE.md to essential, actionable content per Anthropic best
    practice: CLAUDE.md should be short commands and rules, not verbose
    documentation. Move detailed content to referenced docs.
  </objective>

  <context>
    <note>
      Current .claude/CLAUDE.md is ~150 lines and includes detailed
      explanations, examples, and documentation links. Anthropic recommends
      keeping CLAUDE.md concise — it's loaded into every conversation's
      context window. Detailed standards already exist in .claude/rules/.
      The @./python-standards.md include is good (short file).
      The @./rules/empathy/coding-standards-index.md include pulls in
      850+ lines of coding standards on every conversation — too much.
    </note>
  </context>

  <files-to-modify>
    <file path=".claude/CLAUDE.md">
      <change location="entire file">
        Trim to essentials:
        1. Keep: Quick Start section (shortened)
        2. Keep: Command Hubs table
        3. Keep: @./python-standards.md include
        4. REMOVE: @./rules/empathy/coding-standards-index.md include
           (rules/ files are auto-loaded by Claude Code)
        5. Keep: Critical rules summary (5 lines max)
        6. Keep: Project Structure (shortened)
        7. REMOVE: Lifecycle Hooks detail (in settings.json already)
        8. REMOVE: Documentation links section
        Target: ~60 lines
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>wc -l .claude/CLAUDE.md shows ~60-80 lines (down from ~150)</check>
    <check>grep "@./rules/empathy/coding-standards-index.md" .claude/CLAUDE.md returns NO matches</check>
    <check>grep "@./python-standards.md" .claude/CLAUDE.md returns match (kept)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Removing the coding-standards-index.md include means Claude won't see
      those rules in CLAUDE.md context. However, .claude/rules/ files are
      auto-loaded by Claude Code, so the rules are still available. Verify
      by checking Claude Code loads rules/ directory contents.
    </risk>
  </risks>
</task>
```

---

### Task 14: Update Test Coverage Target

```xml
<task id="M3" name="coverage-target">
  <objective>
    Update pytest coverage fail_under from 55 to 80 to match the project's
    stated 80% minimum coverage requirement.
  </objective>

  <context>
    <note>
      The coding standards (in .claude/rules/) state "Minimum 80% Test
      Coverage" but pyproject.toml has fail_under = 55. This inconsistency
      means CI passes with coverage well below the stated standard.
    </note>
  </context>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="[tool.coverage.report] section">
        BEFORE: fail_under = 55
        AFTER:  fail_under = 80
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep "fail_under" pyproject.toml shows 80</check>
    <check>uv run pytest --cov=src --cov-report=term-missing to verify current coverage meets 80%</check>
  </validation>

  <risks>
    <risk severity="high">
      If current coverage is below 80%, this will break CI immediately.
      Check actual coverage BEFORE making this change. If below 80%,
      either increase coverage first or set an intermediate target (e.g., 70%)
      with a plan to reach 80%.
    </risk>
  </risks>
</task>
```

---

### Task 15: Add Missing Hook Events

```xml
<task id="M4" name="additional-hook-events">
  <objective>
    Add PostToolUse hook for logging/telemetry and UserPromptSubmit
    hook for session tracking. Feature branch only.
  </objective>

  <context>
    <existing-code path=".claude/settings.json">
      Current hooks: SessionStart, Stop, PreToolUse (Bash, Edit|Write)
      Missing: PostToolUse, UserPromptSubmit
    </existing-code>
    <note>
      PostToolUse can log tool execution results for telemetry.
      UserPromptSubmit can track session activity for learning evaluation.
      These are non-blocking (informational) hooks.
    </note>
  </context>

  <files-to-create>
    <file path="attune_llm/hooks/scripts/post_tool_log.py">
      Read stdin JSON, log tool_name and execution status to
      .attune/hook_telemetry.jsonl for session analytics.
      Always exit 0 (non-blocking).
    </file>
  </files-to-create>

  <files-to-modify>
    <file path=".claude/settings.json">
      <change location="after PreToolUse section">
        ADD PostToolUse hook:
        "PostToolUse": [
          {
            "hooks": [
              {
                "type": "command",
                "command": "python attune_llm/hooks/scripts/post_tool_log.py",
                "timeout": 3,
                "statusMessage": "Logging tool execution..."
              }
            ]
          }
        ]
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>python -m json.tool .claude/settings.json (valid JSON)</check>
    <check>echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | python attune_llm/hooks/scripts/post_tool_log.py; test $? -eq 0</check>
  </validation>

  <risks>
    <risk severity="low">
      PostToolUse hooks run after every tool call. Keep timeout low (3s)
      and ensure the script is lightweight to avoid slowing down sessions.
    </risk>
  </risks>
</task>
```

---

### Task 16: MCP Server — Consider Official SDK

```xml
<task id="M5" name="mcp-sdk-evaluation">
  <objective>
    Evaluate migrating the custom stdio MCP server to the official mcp
    Python SDK for better protocol compliance and maintainability.
    This is a research/planning task, not an immediate code change.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py" lines="1-27">
      Custom implementation using raw JSON-RPC over stdio.
      Not using the official mcp package from Anthropic.
    </existing-code>
    <note>
      The official MCP Python SDK (pip install mcp) provides:
      - Correct JSON-RPC 2.0 protocol handling
      - Built-in tool/resource/prompt registration
      - SSE and stdio transports
      - Type-safe request/response handling
      Migration would replace ~200 lines of custom protocol code.
    </note>
  </context>

  <validation>
    <check>Document findings in docs/implementation/MCP_SDK_MIGRATION.md</check>
    <check>Include: effort estimate, breaking changes, and migration path</check>
  </validation>

  <risks>
    <risk severity="medium">
      Full migration is significant effort (1-2 days). May introduce
      regressions in tool registration. Recommend as a separate PR.
    </risk>
  </risks>
</task>
```

---

### Task 17: Update Cache Savings Calculation

```xml
<task id="M6" name="cache-savings-calculation">
  <objective>
    Fix the hardcoded Sonnet 4.5 pricing in the cache savings calculation
    to use the model's actual pricing from the registry.
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="211-213">
      if cache_read > 0:
          # Sonnet 4.5 input: $3/M tokens, cache read: $0.30/M tokens (90% discount)
          savings_per_token = 0.003 / 1000 * 0.9  # 90% of regular cost
    </existing-code>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="lines 211-213">
        BEFORE:
        if cache_read > 0:
            # Sonnet 4.5 input: $3/M tokens, cache read: $0.30/M tokens (90% discount)
            savings_per_token = 0.003 / 1000 * 0.9  # 90% of regular cost

        AFTER:
        if cache_read > 0:
            # Cache reads cost 90% less than regular input tokens
            input_cost_per_token = 3.00 / 1_000_000  # Default Sonnet 4.5 rate
            savings_per_token = input_cost_per_token * 0.9
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv run pytest tests/ -k "cache or provider" passes</check>
  </validation>

  <risks>
    <risk severity="none">Logging-only change, no runtime behavior impact.</risk>
  </risks>
</task>
```

---

### Task 18: Agent SDK Evaluation

```xml
<task id="M7" name="agent-sdk-evaluation">
  <objective>
    Evaluate adopting the Anthropic Agent SDK (claude-agent-sdk) for the
    project's multi-agent orchestration layer. Research task only.
  </objective>

  <context>
    <note>
      The project currently uses custom orchestration in
      src/attune/orchestration/. The Anthropic Agent SDK provides
      standardized agent patterns. This task evaluates whether adoption
      would simplify the codebase or add unnecessary coupling.
    </note>
  </context>

  <validation>
    <check>Document findings in docs/implementation/AGENT_SDK_EVALUATION.md</check>
    <check>Include: compatibility assessment, migration effort, pros/cons</check>
  </validation>

  <risks>
    <risk severity="low">Research only, no code changes.</risk>
  </risks>
</task>
```

---

## LOW Priority Tasks

### Task 19: Add settings.local.json Documentation

```xml
<task id="L1" name="settings-local-docs">
  <objective>
    Document that developers should use .claude/settings.local.json for
    personal overrides (not committed to git) per Claude Code best practice.
  </objective>

  <files-to-modify>
    <file path=".gitignore">
      <change location="Claude Code section">
        Ensure .claude/settings.local.json is listed in .gitignore
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>grep "settings.local.json" .gitignore returns match</check>
  </validation>

  <risks>
    <risk severity="none">Documentation/config only.</risk>
  </risks>
</task>
```

---

### Task 20: Add Subagent Hooks (Future)

```xml
<task id="L2" name="subagent-hooks">
  <objective>
    Plan for SubagentStart/SubagentStop hooks when the project adopts
    multi-agent patterns in Claude Code. Placeholder for future work.
  </objective>

  <context>
    <note>
      Claude Code supports SubagentStart and SubagentStop hook events.
      These are relevant if the project uses Task tool subagents.
      Not needed immediately but worth tracking.
    </note>
  </context>

  <validation>
    <check>Add TODO item to .attune/roadmap or project backlog</check>
  </validation>

  <risks>
    <risk severity="none">Planning only.</risk>
  </risks>
</task>
```

---

### Task 21: Pre-commit Hook for Model ID Validation

```xml
<task id="L3" name="model-id-precommit">
  <objective>
    Add a pre-commit hook that validates model IDs in registry.py match
    known Anthropic model patterns, preventing stale IDs from being committed.
  </objective>

  <context>
    <note>
      A lightweight script that checks MODEL_REGISTRY entries against
      a known pattern (claude-{family}-{version}) would catch future
      model ID staleness at commit time rather than at runtime.
    </note>
  </context>

  <files-to-create>
    <file path="scripts/validate_model_ids.py">
      Parse registry.py, extract model IDs, validate against pattern.
      Exit 1 if any ID doesn't match expected format.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path=".pre-commit-config.yaml">
      <change location="add local hook">
        - repo: local
          hooks:
            - id: validate-model-ids
              name: Validate Anthropic model IDs
              entry: python scripts/validate_model_ids.py
              language: python
              files: registry\.py$
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pre-commit run validate-model-ids --all-files passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Pattern may be too strict and reject valid new model formats.
      Use a permissive regex that catches obvious mistakes.
    </risk>
  </risks>
</task>
```

---

### Task 22: Anthropic API Key Validation Pattern

```xml
<task id="L4" name="api-key-validation">
  <objective>
    Improve API key validation in the provider to check key format
    (sk-ant-* prefix) before making network calls.
  </objective>

  <context>
    <existing-code path="attune_llm/providers.py" lines="100-105">
      if not api_key or not api_key.strip():
          raise ValueError(
              "API key is required for Anthropic provider. "
              "Provide via api_key parameter or ANTHROPIC_API_KEY environment variable",
          )
    </existing-code>
  </context>

  <files-to-modify>
    <file path="attune_llm/providers.py">
      <change location="lines 100-105">
        BEFORE:
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for Anthropic provider. "
                "Provide via api_key parameter or ANTHROPIC_API_KEY environment variable",
            )

        AFTER:
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for Anthropic provider. "
                "Provide via api_key parameter or ANTHROPIC_API_KEY environment variable",
            )
        if not api_key.startswith("sk-ant-"):
            logger.warning(
                "API key does not start with 'sk-ant-' — may not be a valid Anthropic key"
            )
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv run pytest tests/ -k "provider" passes</check>
  </validation>

  <risks>
    <risk severity="low">
      Anthropic may change key format in the future. Use a warning (not
      error) so valid keys with new prefixes still work.
    </risk>
  </risks>
</task>
```

---

## Implementation Order

Recommended execution sequence:

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1     | C1    | SDK version constraint (unblocks C4, H2) |
| 2     | C2, C3 | Model IDs and pricing (parallel) |
| 3     | C4    | Error handling (needs SDK upgrade) |
| 4     | C5    | Security guard fail-closed |
| 5     | H1, H3, H4, H5 | MCP location, metadata, docstring, duplicate rules (parallel) |
| 6     | H2    | Streaming support (needs SDK upgrade) |
| 7     | M1-M4 | Thinking budget, CLAUDE.md, coverage, hooks (parallel) |
| 8     | M5-M7 | Research tasks (parallel) |
| 9     | L1-L4 | Low priority items (as convenient) |
| 10    | H6    | Backport hooks to main (at merge time) |

---

## Main Branch vs Feature Branch Summary

| Issue | Main | Feature |
|-------|------|---------|
| Outdated model IDs | Yes | Yes |
| Wrong pricing | Yes | Yes |
| SDK version ceiling | Yes | Yes |
| No typed error handling | Yes | Yes |
| MCP in wrong location | Yes | Yes |
| No hooks at all | **Yes** | No (has hooks) |
| No security guard | **Yes** | No (has guard) |
| Security guard fails open | N/A | **Yes** |
| Duplicate rules dirs | No | **Yes** |
| Provider metadata hardcoded | Yes | Yes |

**Key takeaway:** Main branch inherits all shared issues AND is missing the entire hooks/security infrastructure that the feature branch added.

---

**Total estimated effort:** 2-3 days for Critical + High, 1-2 days for Medium, opportunistic for Low.
