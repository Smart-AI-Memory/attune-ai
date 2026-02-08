"""Document Generation Workflow.

Main workflow orchestration for documentation generation.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import logging
from pathlib import Path
from typing import Any

from ..base import BaseWorkflow, ModelTier
from .api_reference import APIReferenceMixin
from .chunked_generation import ChunkedGenerationMixin
from .config import DOC_GEN_STEPS, TOKEN_COSTS  # noqa: F401  # re-export
from .cost_management import DocGenCostMixin
from .report_formatter import format_doc_gen_report

logger = logging.getLogger(__name__)


class DocumentGenerationWorkflow(
    DocGenCostMixin,
    ChunkedGenerationMixin,
    APIReferenceMixin,
    BaseWorkflow,
):
    """Multi-tier document generation workflow.

    Uses cheap models for outlining, capable models for content
    generation, and premium models for final polish and consistency
    review.

    Usage:
        workflow = DocumentGenerationWorkflow()
        result = await workflow.execute(
            source_code="...",
            doc_type="api_reference",
            audience="developers"
        )
    """

    name = "doc-gen"
    description = "Cost-optimized documentation generation pipeline"
    stages = ["outline", "write", "polish"]
    tier_map = {
        "outline": ModelTier.CHEAP,
        "write": ModelTier.CAPABLE,
        "polish": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        skip_polish_threshold: int = 1000,
        max_sections: int = 10,
        max_write_tokens: int | None = None,  # Auto-scaled if None
        section_focus: list[str] | None = None,
        chunked_generation: bool = True,
        sections_per_chunk: int = 3,
        max_cost: float = 5.0,  # Cost guardrail in USD
        cost_warning_threshold: float = 0.8,  # Warn at 80% of max_cost
        graceful_degradation: bool = True,  # Return partial results on error
        export_path: str | Path | None = None,  # Export docs to file (e.g., "docs/generated")
        max_display_chars: int = 45000,  # Max chars before chunking output
        enable_auth_strategy: bool = True,  # Enable intelligent auth routing
        **kwargs: Any,
    ):
        """Initialize workflow with enterprise-safe defaults.

        Args:
            skip_polish_threshold: Skip premium polish for docs under this
                token count (they're already good enough).
            max_sections: Maximum number of sections to generate.
            max_write_tokens: Maximum tokens for content generation.
                If None, auto-scales based on section count (recommended).
            section_focus: Optional list of specific sections to generate
                (e.g., ["Testing Guide", "API Reference"]).
            chunked_generation: If True, generates large docs in chunks to avoid
                truncation (default True).
            sections_per_chunk: Number of sections to generate per chunk (default 3).
            max_cost: Maximum cost in USD before stopping (default $5).
                Set to 0 to disable cost limits.
            cost_warning_threshold: Percentage of max_cost to trigger warning (default 0.8).
            graceful_degradation: If True, return partial results on errors
                instead of failing completely (default True).
            export_path: Optional directory to export generated docs (e.g., "docs/generated").
                If provided, documentation will be saved to a file automatically.
            max_display_chars: Maximum characters before splitting output into chunks
                for display (default 45000). Helps avoid terminal/UI truncation.
            enable_auth_strategy: If True, use intelligent subscription vs API routing
                based on module size (default True).

        """
        super().__init__(**kwargs)
        self.tier_map = dict(self.__class__.tier_map)  # Instance copy to avoid mutating class
        self.skip_polish_threshold = skip_polish_threshold
        self.max_sections = max_sections
        self._user_max_write_tokens = max_write_tokens  # Store user preference
        self.max_write_tokens = max_write_tokens or 16000  # Will be auto-scaled
        self.section_focus = section_focus
        self.chunked_generation = chunked_generation
        self.sections_per_chunk = sections_per_chunk
        self.max_cost = max_cost
        self.cost_warning_threshold = cost_warning_threshold
        self.graceful_degradation = graceful_degradation
        self.export_path = Path(export_path) if export_path else None
        self.max_display_chars = max_display_chars
        self.enable_auth_strategy = enable_auth_strategy
        self._total_content_tokens: int = 0
        self._accumulated_cost: float = 0.0
        self._cost_warning_issued: bool = False
        self._partial_results: dict = {}
        self._auth_mode_used: str | None = None  # Track which auth was recommended

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip polish for short documents."""
        if stage_name == "polish":
            if self._total_content_tokens < self.skip_polish_threshold:
                self.tier_map["polish"] = ModelTier.CAPABLE
                return False, None
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a document generation stage."""
        if stage_name == "outline":
            return await self._outline(input_data, tier)
        if stage_name == "write":
            return await self._write(input_data, tier)
        if stage_name == "polish":
            return await self._polish(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _outline(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate document outline from source."""
        from pathlib import Path

        source_code = input_data.get("source_code", "")
        target = input_data.get("target", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")

        # Use target if source_code not provided
        content_to_document = source_code or target

        # If target looks like a file path and source_code wasn't provided, read the file
        if not source_code and target:
            target_path = Path(target)
            if target_path.exists() and target_path.is_file():
                try:
                    content_to_document = target_path.read_text(encoding="utf-8")
                    # Prepend file info for context
                    content_to_document = f"# File: {target}\n\n{content_to_document}"
                except Exception as e:
                    # If we can't read the file, log and use the path as-is
                    import logging

                    logging.getLogger(__name__).warning(f"Could not read file {target}: {e}")
            elif target_path.suffix in (
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".java",
                ".go",
                ".rs",
                ".md",
                ".txt",
            ):
                # Looks like a file path but doesn't exist - warn
                import logging

                logging.getLogger(__name__).warning(
                    f"Target appears to be a file path but doesn't exist: {target}",
                )

        # === AUTH STRATEGY INTEGRATION ===
        # Detect module size and recommend auth mode (first stage only)
        if self.enable_auth_strategy:
            try:
                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                # Calculate module size
                module_lines = 0
                if target and Path(target).exists():
                    module_lines = count_lines_of_code(target)
                elif content_to_document:
                    # Count from source code content
                    module_lines = len(
                        [
                            line
                            for line in content_to_document.split("\n")
                            if line.strip() and not line.strip().startswith("#")
                        ]
                    )

                if module_lines > 0:
                    # Get auth strategy (first-time setup if needed)
                    strategy = get_auth_strategy()

                    # Get recommended auth mode
                    recommended_mode = strategy.get_recommended_mode(module_lines)
                    self._auth_mode_used = recommended_mode.value

                    # Get size category
                    size_category = get_module_size_category(module_lines)

                    # Log recommendation
                    logger.info(
                        f"Module: {target or 'source'} ({module_lines} LOC, {size_category})"
                    )
                    logger.info(f"Recommended auth mode: {recommended_mode.value}")

                    # Get cost estimate
                    cost_estimate = strategy.estimate_cost(module_lines, recommended_mode)

                    if recommended_mode.value == "subscription":
                        logger.info(
                            f"Cost: {cost_estimate['quota_cost']} "
                            f"(fits in {cost_estimate['fits_in_context']} context)"
                        )
                    else:  # API
                        logger.info(
                            f"Cost: ~${cost_estimate['monetary_cost']:.4f} " f"(1M context window)"
                        )

            except Exception as e:
                # Don't fail workflow if auth strategy fails
                logger.warning(f"Auth strategy detection failed: {e}")

        system = """You are an expert technical writer specializing in API Reference documentation.

IMPORTANT: This is API REFERENCE documentation, not a tutorial. Focus on documenting EVERY function/class with structured Args/Returns/Raises format.

Create a detailed, structured outline for API Reference documentation:

1. **Logical Section Structure** (emphasize API reference sections):
   - Overview/Introduction (brief)
   - Quick Start (1 complete example)
   - API Reference - Functions (one subsection per function with Args/Returns/Raises)
   - API Reference - Classes (one subsection per class with Args/Returns/Raises for methods)
   - Usage Examples (showing how to combine multiple functions)
   - Additional reference sections as needed

2. **For Each Section**:
   - Clear purpose and what readers will learn
   - Specific topics to cover
   - Types of examples to include (with actual code)

3. **Key Requirements**:
   - Include sections for real, copy-paste ready code examples
   - Plan for comprehensive API documentation with all parameters
   - Include edge cases and error handling examples
   - Add best practices and common patterns

Format as a numbered list with section titles and detailed descriptions."""

        user_message = f"""Create a comprehensive documentation outline:

Document Type: {doc_type}
Target Audience: {audience}

IMPORTANT: This documentation should be production-ready with:
- Real, executable code examples (not placeholders)
- Complete API reference with parameter types and descriptions
- Usage guides showing common patterns
- Edge case handling and error scenarios
- Best practices for the target audience

Content to document:
{content_to_document[:4000]}

Generate an outline that covers all these aspects comprehensively."""

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=1000,
        )

        return (
            {
                "outline": response,
                "doc_type": doc_type,
                "audience": audience,
                "content_to_document": content_to_document,
            },
            input_tokens,
            output_tokens,
        )

    def _parse_outline_sections(self, outline: str) -> list[str]:
        """Parse top-level section titles from the outline.

        Only matches main sections like "1. Introduction", "2. Setup", etc.
        Ignores sub-sections like "2.1 Prerequisites" or nested items.
        """
        import re

        sections = []
        # Match only top-level sections: digit followed by period and space/letter
        # e.g., "1. Introduction" but NOT "1.1 Sub-section" or "2.1.3 Deep"
        top_level_pattern = re.compile(r"^(\d+)\.\s+([A-Za-z].*)")

        for line in outline.split("\n"):
            stripped = line.strip()
            match = top_level_pattern.match(stripped)
            if match:
                # section_num = match.group(1) - not needed, only extracting title
                title = match.group(2).strip()
                # Remove any trailing description after " - "
                if " - " in title:
                    title = title.split(" - ")[0].strip()
                sections.append(title)

        return sections

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
{content_to_document[:5000]}

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
                "source_code": content_to_document,  # Pass through for API reference generation
            },
            input_tokens,
            output_tokens,
        )

    async def _polish(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Final review and consistency polish using LLM.

        Enterprise-safe: chunks large documents to avoid truncation.
        Supports XML-enhanced prompts when enabled in workflow config.
        """
        draft_document = input_data.get("draft_document", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")

        # Check if document is too large and needs chunked polishing
        # Rough estimate: 4 chars per token, 10k tokens threshold for chunking
        estimated_tokens = len(draft_document) // 4
        needs_chunked_polish = estimated_tokens > 10000

        if needs_chunked_polish:
            logger.info(
                f"Large document detected (~{estimated_tokens} tokens). "
                "Using chunked polish for enterprise safety.",
            )
            return await self._polish_chunked(input_data, tier)

        # Build input payload for prompt
        input_payload = f"""Document Type: {doc_type}
Target Audience: {audience}

Draft:
{draft_document}"""

        # Check if XML prompts are enabled
        if self._is_xml_enabled():
            # Use XML-enhanced prompt
            user_message = self._render_xml_prompt(
                role="senior technical editor",
                goal="Polish and improve the documentation for consistency and quality",
                instructions=[
                    "Standardize terminology and formatting",
                    "Improve clarity and flow",
                    "Add missing cross-references",
                    "Fix grammatical issues",
                    "Identify gaps and add helpful notes",
                    "Ensure examples are complete and accurate",
                ],
                constraints=[
                    "Maintain the original structure and intent",
                    "Keep content appropriate for the target audience",
                    "Preserve code examples while improving explanations",
                ],
                input_type="documentation_draft",
                input_payload=input_payload,
                extra={
                    "doc_type": doc_type,
                    "audience": audience,
                },
            )
            system = None  # XML prompt includes all context
        else:
            # Use legacy plain text prompts
            system = """You are a senior technical editor specializing in developer documentation.

Polish and improve this documentation. The writer was asked to complete TWO PHASES:
- Phase 1: Comprehensive content with real examples
- Phase 2: Structured API reference sections with **Args:**, **Returns:**, **Raises:**

Your job is to verify BOTH phases are complete and polish to production quality.

═══════════════════════════════════════════════════════════════
CRITICAL: Verify Phase 2 Completion
═══════════════════════════════════════════════════════════════

1. **Check for Missing API Reference Sections**:
   - Scan the entire document for all functions and methods
   - EVERY function MUST have these sections:
     - **Args:** (write "None" if no parameters)
     - **Returns:** (write "None" if void)
     - **Raises:** (write "None" if no exceptions)
   - If ANY function is missing these sections, ADD them now
   - Format: **Args:**, **Returns:**, **Raises:** (bold headers with colons)

2. **Polish API Reference Sections**:
   - Verify all parameters have types in backticks: `param` (`type`)
   - Ensure return values are clearly described
   - Check exception documentation is complete
   - Validate code examples in each function section

3. **Polish General Content**:
   - Verify code examples are complete and runnable
   - Ensure proper imports and setup code
   - Replace any placeholders with real code
   - Standardize terminology throughout
   - Fix formatting inconsistencies
   - Improve clarity and flow
   - Add cross-references between sections

4. **Production Readiness**:
   - Remove any TODO or placeholder comments
   - Ensure professional tone
   - Add helpful notes, tips, and warnings
   - Verify edge cases are covered

═══════════════════════════════════════════════════════════════
Return the complete, polished document. Add a brief "## Polish Notes" section at the end summarizing improvements made."""

            user_message = f"""Polish this documentation to production quality.

The writer was asked to complete TWO PHASES:
1. Comprehensive content with real examples
2. Structured API reference with **Args:**, **Returns:**, **Raises:** for every function

Verify BOTH phases are complete, then polish:

{input_payload}

═══════════════════════════════════════════════════════════════
YOUR TASKS:
═══════════════════════════════════════════════════════════════

1. SCAN for missing API reference sections
   - Find every function/method in the document
   - Check if it has **Args:**, **Returns:**, **Raises:** sections
   - ADD these sections if missing (use "None" if no parameters/returns/exceptions)

2. POLISH existing content
   - Verify code examples are complete and runnable
   - Ensure terminology is consistent
   - Fix formatting issues
   - Improve clarity and flow

3. VALIDATE production readiness
   - Remove TODOs and placeholders
   - Add warnings and best practices
   - Ensure professional tone

Return the complete, polished documentation with all API reference sections present."""

        # Calculate polish tokens based on draft size (at least as much as write stage)
        polish_max_tokens = max(self.max_write_tokens, 20000)

        # Try executor-based execution first (Phase 3 pattern)
        if self._executor is not None or self._api_key:
            try:
                step = DOC_GEN_STEPS["polish"]
                # Override step max_tokens with dynamic value
                step.max_tokens = polish_max_tokens
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
            except Exception:
                # Fall back to legacy _call_llm if executor fails
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system or "",
                    user_message,
                    max_tokens=polish_max_tokens,
                )
        else:
            # Legacy path for backward compatibility
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system or "",
                user_message,
                max_tokens=polish_max_tokens,
            )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Add structured API reference sections (Step 4: Post-processing)
        source_code = input_data.get("source_code", "")
        if source_code:
            logger.info("Adding structured API reference sections to polished document...")
            response = await self._add_api_reference_sections(
                narrative_doc=response,
                source_code=source_code,
                tier=ModelTier.CHEAP,  # Use cheap tier for structured extraction
            )
        else:
            logger.warning("No source code available for API reference generation")

        result = {
            "document": response,
            "doc_type": doc_type,
            "audience": audience,
            "model_tier_used": tier.value,
            "accumulated_cost": self._accumulated_cost,  # Track total cost
            "auth_mode_used": self._auth_mode_used,  # Track recommended auth mode
        }

        # Merge parsed XML data if available
        if parsed_data.get("xml_parsed"):
            result.update(
                {
                    "xml_parsed": True,
                    "summary": parsed_data.get("summary"),
                    "findings": parsed_data.get("findings", []),
                    "checklist": parsed_data.get("checklist", []),
                },
            )

        # Add formatted report for human readability
        result["formatted_report"] = format_doc_gen_report(result, input_data)

        # Export documentation if export_path is configured
        doc_path, report_path = self._export_document(
            document=response,
            doc_type=doc_type,
            report=result["formatted_report"],
        )
        if doc_path:
            result["export_path"] = str(doc_path)
            result["report_path"] = str(report_path) if report_path else None
            logger.info(f"Documentation saved to: {doc_path}")

        # Chunk output for display if needed
        output_chunks = self._chunk_output_for_display(
            result["formatted_report"],
            chunk_prefix="DOC OUTPUT",
        )
        if len(output_chunks) > 1:
            result["output_chunks"] = output_chunks
            result["output_chunk_count"] = len(output_chunks)
            logger.info(
                f"Report split into {len(output_chunks)} chunks for display "
                f"(total {len(result['formatted_report'])} chars)",
            )

        return (result, input_tokens, output_tokens)
