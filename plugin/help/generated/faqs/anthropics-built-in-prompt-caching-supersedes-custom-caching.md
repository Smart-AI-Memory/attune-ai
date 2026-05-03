---
name: anthropics-built-in-prompt-caching-supersedes-custom-caching
source: .claude/CLAUDE.md
summary: This template explains that the Claude Agent SDK automatically leverages
  Anthropic's built-in prompt caching (available since December 2024) for up to 90%
  savings on input token costs, eliminating the need for custom caching implementations.
type: faq
---

# FAQ: How does Anthropic's built-in prompt caching affect the Claude Agent SDK?

## Answer

Since December 2024, the Anthropic API provides automatic server-side prompt caching, offering up to a **90% discount on input token costs**. The Claude Agent SDK takes advantage of this automatically — no additional configuration is required.

As a result, any custom caching implementations (such as those using `sentence-transformers` for semantic similarity matching) are superseded by Anthropic's built-in caching. You do not need to maintain or configure a separate caching layer.

## What This Means for You

- **No action required.** The SDK handles prompt caching transparently.
- **Custom caching is unnecessary.** If you previously implemented custom caching, it can safely be removed.
- **Cost savings are applied automatically.** Repeated or similar prompts will benefit from reduced input token pricing without any extra setup.

## Related Topics

- **Error: Anthropic's built-in prompt caching supersedes custom caching** — If you encounter this message, it indicates that a custom caching mechanism has been disabled in favor of the native Anthropic implementation. This is expected behavior and not a failure state.
