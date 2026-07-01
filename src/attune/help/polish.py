"""LLM polish pass for generated help templates.

After Jinja2 renders the structural skeleton, this module
sends the content through an LLM to improve writing quality:
fix generic filler, sharpen descriptions, verify accuracy
against the source info provided.

Errors are non-fatal — if the LLM call fails, the original
Jinja2 output is returned unchanged.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a technical writer following Google's developer \
documentation style guide. Your job is to polish a help \
template that was auto-generated from source code.

Rules:
- Fix generic filler like "manages core functionality" — \
  replace with specific descriptions from the source info
- Keep the existing markdown section structure exactly as-is
- Use second person ("you") and active voice
- Use bare infinitives for task headings ("Configure X", \
  not "Configuring X")
- Use noun phrases for concept and reference headings
- Keep descriptions concise — one sentence per item
- Do not invent features or capabilities not in the source
- Do not add sections, remove sections, or change headings
- Do not modify the YAML frontmatter block (--- to ---)
- For task templates: the opening line after the h1 must be \
  a single active sentence starting with "Use ... when" or \
  "Run ... when" that tells the reader WHEN and WHY they \
  would perform this procedure. Example: "Run a security \
  audit when you suspect vulnerabilities or before releasing \
  a new version." Do not describe what the code does — \
  describe what the USER accomplishes by using it.
- Return only the improved markdown, nothing else
"""


def polish_template(
    content: str,
    feature_name: str,
    source_summary: str,
) -> str:
    """Polish a generated template using an LLM.

    Args:
        content: The Jinja2-rendered markdown (with frontmatter).
        feature_name: Name of the feature being documented.
        source_summary: Summary of source info (classes,
            functions, docstrings) for accuracy checking.

    Returns:
        Polished markdown string, or the original content
        if the LLM call fails.
    """
    try:
        return _call_llm(content, feature_name, source_summary)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Polish is non-fatal — fall back to
        # Jinja2 output rather than blocking generation
        logger.warning(
            "Polish pass failed for %s, using raw template",
            feature_name,
        )
        return content


def _call_llm(
    content: str,
    feature_name: str,
    source_summary: str,
) -> str:
    """Make the LLM call for polishing.

    Args:
        content: Template content to polish.
        feature_name: Feature name for context.
        source_summary: Source code summary.

    Returns:
        Polished content from LLM.

    Raises:
        RuntimeError: If no API key is available.
        Exception: Any error from the Anthropic SDK.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    user_message = (
        f"Polish this auto-generated help template for the "
        f"'{feature_name}' feature.\n\n"
        f"## Source info (for accuracy checking)\n\n"
        f"{source_summary}\n\n"
        f"## Template to polish\n\n"
        f"{content}"
    )

    response = client.messages.create(
        # Stable alias — claude-sonnet-4-20250514 retires 2026-06-15.
        # The stable alias routes to the same checkpoint and stays
        # valid across model upgrades.
        model="claude-sonnet-5",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    if response.content:
        text = response.content[0].text
        # Anthropic API doesn't guarantee a trailing newline
        if not text.endswith("\n"):
            text += "\n"
        return text

    return content


def build_source_summary(
    public_classes: list[dict[str, str]],
    public_functions: list[dict[str, str]],
    module_docstrings: list[str],
    file_count: int,
) -> str:
    """Build a concise source summary for the polish prompt.

    Args:
        public_classes: List of class dicts with name/doc/file.
        public_functions: List of function dicts.
        module_docstrings: First lines of module docstrings.
        file_count: Total number of source files.

    Returns:
        Formatted summary string.
    """
    parts: list[str] = []

    if module_docstrings:
        parts.append("Module purposes:")
        for doc in module_docstrings[:5]:
            parts.append(f"  - {doc}")

    if public_classes:
        parts.append("Classes:")
        for cls in public_classes[:10]:
            doc = cls.get("doc", "")
            parts.append(f"  - {cls['name']}: {doc}" if doc else f"  - {cls['name']}")

    if public_functions:
        parts.append("Functions:")
        for fn in public_functions[:10]:
            doc = fn.get("doc", "")
            parts.append(f"  - {fn['name']}(): {doc}" if doc else f"  - {fn['name']}()")

    parts.append(f"Total source files: {file_count}")

    return "\n".join(parts)
