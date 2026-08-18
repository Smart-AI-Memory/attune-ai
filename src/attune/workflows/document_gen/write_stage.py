"""Write stage mixin for document generation workflow.

Handles the second stage: generating full documentation content
from the outline produced in the outline stage.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging

from attune.context import TokenBudgetAllocator

from ..base import ModelTier

logger = logging.getLogger(__name__)


class WriteStageMixin:
    """Mixin providing the write (content generation) stage.

    Requires the host class to provide:
    - ``self.max_write_tokens``: int
    - ``self.chunked_generation``: bool
    - ``self.sections_per_chunk``: int
    - ``self.section_focus``: list[str] | None
    - ``self._auto_scale_tokens()``: token scaling method
    - ``self._write_chunked()``: chunked write method
    - ``self._call_llm()``: LLM call method
    - ``self._parse_outline_sections()``: outline parser
    - ``self._total_content_tokens``: int (written to)
    """

    async def _write(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Write content based on the outline."""
        outline = input_data.get("outline", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")
        content_to_document = input_data.get("content_to_document", "")

        # Parse sections from outline
        sections = self._parse_outline_sections(outline)

        # Auto-scale tokens based on section count
        self.max_write_tokens = self._auto_scale_tokens(len(sections))

        # Use chunked generation for large outlines (more than sections_per_chunk * 2)
        use_chunking = (
            self.chunked_generation
            and len(sections) > self.sections_per_chunk * 2
            and not self.section_focus  # Don't chunk if already focused
        )

        if use_chunking:
            return await self._write_chunked(
                sections,
                outline,
                doc_type,
                audience,
                content_to_document,
                tier,
            )

        # Handle section_focus for targeted generation
        section_instruction = ""
        if self.section_focus:
            sections_list = ", ".join(self.section_focus)
            section_instruction = f"""
IMPORTANT: Focus ONLY on generating these specific sections:
{sections_list}

Generate comprehensive, detailed content for each of these sections."""

        system = f"""You are an expert technical writer creating comprehensive developer documentation.

YOUR TASK HAS TWO CRITICAL PHASES - YOU MUST COMPLETE BOTH:

═══════════════════════════════════════════════════════════════
PHASE 1: Write Comprehensive Documentation
═══════════════════════════════════════════════════════════════

Write clear, helpful documentation with:
- Overview and introduction explaining what this code does
- Real, executable code examples (NOT placeholders - use actual code from source)
- Usage guides showing how to use the code in real scenarios
- Best practices and common patterns
- Step-by-step instructions where helpful
- Tables, diagrams, and visual aids as appropriate
- Clear explanations appropriate for {audience}

Do this naturally - write the kind of documentation that helps developers understand and use the code effectively.

═══════════════════════════════════════════════════════════════
PHASE 2: Add Structured API Reference Sections (MANDATORY)
═══════════════════════════════════════════════════════════════

After writing the comprehensive documentation above, you MUST add structured API reference sections for EVERY function and class method.

For EACH function/method in the source code, add this EXACT structure:

---
### `function_name()`

**Function Signature:**
```python
def function_name(param1: type, param2: type = default) -> return_type
```

**Description:**
[Brief description of what the function does - 1-2 sentences]

**Args:**
- `param1` (`type`): Clear description of this parameter
- `param2` (`type`, optional): Description. Defaults to `default`.

**Returns:**
- `return_type`: Description of the return value

**Raises:**
- `ExceptionType`: Description of when and why this exception occurs
- `AnotherException`: Another exception case

**Example:**
```python
from module import function_name

# Show real usage with actual code
result = function_name(actual_value, param2=123)
print(result)
```
---

CRITICAL RULES FOR PHASE 2:
- Include **Args:** header for ALL functions (write "None" if no parameters)
- Include **Returns:** header for ALL functions (write "None" if void/no return)
- Include **Raises:** header for ALL functions (write "None" if no exceptions)
- Use backticks for code: `param_name` (`type`)
- Document EVERY public function and method you see in the source code

{section_instruction}

═══════════════════════════════════════════════════════════════
REMINDER: BOTH PHASES ARE MANDATORY
═══════════════════════════════════════════════════════════════

1. Write comprehensive documentation (Phase 1) - what you do naturally
2. Add structured API reference sections (Phase 2) - for every function/method

Do NOT skip Phase 2 after completing Phase 1. Both phases are required for complete documentation."""

        user_message = f"""Write comprehensive, production-ready documentation in TWO PHASES:

Document Type: {doc_type}
Target Audience: {audience}

Outline to follow:
{outline}

Source code to document (extract actual class names, function signatures, parameters):
{TokenBudgetAllocator().fit_source(content_to_document, token_limit=1250)}

═══════════════════════════════════════════════════════════════
YOUR TASK:
═══════════════════════════════════════════════════════════════

PHASE 1: Write comprehensive documentation
- Use the outline above as your guide
- Include real, executable code examples from the source
- Show usage patterns, best practices, common workflows
- Write clear explanations that help developers understand the code

PHASE 2: Add structured API reference sections
- For EACH function/method in the source code, add:
  - Function signature
  - Description
  - **Args:** section (every parameter with type and description)
  - **Returns:** section (return type and description)
  - **Raises:** section (exceptions that can occur)
  - Example code snippet

═══════════════════════════════════════════════════════════════
IMPORTANT: Complete BOTH phases. Don't stop after Phase 1.
═══════════════════════════════════════════════════════════════

Generate the complete documentation now, ensuring both comprehensive content AND structured API reference sections."""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=self.max_write_tokens,
        )

        self._total_content_tokens = output_tokens

        return (
            {
                "draft_document": response,
                "doc_type": doc_type,
                "audience": audience,
                "outline": outline,
                "chunked": False,
                "source_code": content_to_document,
            },
            input_tokens,
            output_tokens,
        )
