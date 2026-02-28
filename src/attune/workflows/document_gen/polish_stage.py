"""Polish stage mixin for document generation workflow.

Handles the third and final stage: reviewing, polishing, and
adding structured API reference sections to the documentation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import Any

from ..base import ModelTier
from .config import DOC_GEN_STEPS
from .report_formatter import format_doc_gen_report

logger = logging.getLogger(__name__)


class PolishStageMixin:
    """Mixin providing the polish (final review) stage.

    Requires the host class to provide:
    - ``self.max_write_tokens``: int
    - ``self._accumulated_cost``: float
    - ``self._auth_mode_used``: str | None
    - ``self.export_path``: Path | None
    - ``self._executor``: executor or None
    - ``self._api_key``: str or None
    - ``self._call_llm()``: LLM call method
    - ``self._is_xml_enabled()``: XML prompt check
    - ``self._render_xml_prompt()``: XML prompt renderer
    - ``self._parse_xml_response()``: XML response parser
    - ``self._polish_chunked()``: chunked polish method
    - ``self._add_api_reference_sections()``: API ref method
    - ``self._export_document()``: export method
    - ``self._chunk_output_for_display()``: display chunker
    - ``self.run_step_with_executor()``: executor runner
    """

    async def _polish(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Final review and consistency polish using LLM.

        Enterprise-safe: chunks large documents to avoid truncation.
        Supports XML-enhanced prompts when enabled in workflow config.
        """
        draft_document = input_data.get("draft_document", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")

        # Check if document is too large and needs chunked polishing
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

        system, user_message = self._build_polish_prompts(
            input_payload,
            doc_type,
            audience,
        )

        # Calculate polish tokens based on draft size
        polish_max_tokens = max(self.max_write_tokens, 20000)

        response, input_tokens, output_tokens = await self._execute_polish_llm(
            tier,
            system,
            user_message,
            polish_max_tokens,
        )

        # Parse XML response if enforcement is enabled
        parsed_data = self._parse_xml_response(response)

        # Add structured API reference sections
        source_code = input_data.get("source_code", "")
        if source_code:
            logger.info("Adding structured API reference sections to polished document...")
            response = await self._add_api_reference_sections(
                narrative_doc=response,
                source_code=source_code,
                tier=ModelTier.CHEAP,
            )
        else:
            logger.warning("No source code available for API reference generation")

        result = self._build_polish_result(
            response,
            doc_type,
            audience,
            tier,
            input_data,
            parsed_data,
        )

        return (result, input_tokens, output_tokens)

    def _build_polish_prompts(
        self,
        input_payload: str,
        doc_type: str,
        audience: str,
    ) -> tuple[str | None, str]:
        """Build system and user prompts for the polish stage.

        Args:
            input_payload: Formatted input with draft document.
            doc_type: Documentation type.
            audience: Target audience.

        Returns:
            Tuple of (system_prompt, user_message).

        """
        if self._is_xml_enabled():
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
            return None, user_message

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

        return system, user_message

    async def _execute_polish_llm(
        self,
        tier: ModelTier,
        system: str | None,
        user_message: str,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        """Execute the polish LLM call with executor fallback.

        Args:
            tier: Model tier to use.
            system: System prompt (None for XML mode).
            user_message: User message prompt.
            max_tokens: Maximum output tokens.

        Returns:
            Tuple of (response, input_tokens, output_tokens).

        """
        if self._executor is not None or self._api_key:
            try:
                step = DOC_GEN_STEPS["polish"]
                step.max_tokens = max_tokens
                response, input_tokens, output_tokens, cost = await self.run_step_with_executor(
                    step=step,
                    prompt=user_message,
                    system=system,
                )
                return response, input_tokens, output_tokens
            except Exception:
                pass  # Fall through to legacy path

        response, input_tokens, output_tokens = await self._call_llm(
            tier,
            system or "",
            user_message,
            max_tokens=max_tokens,
        )
        return response, input_tokens, output_tokens

    def _build_polish_result(
        self,
        response: str,
        doc_type: str,
        audience: str,
        tier: ModelTier,
        input_data: dict,
        parsed_data: dict,
    ) -> dict[str, Any]:
        """Build the final result dict from the polish stage.

        Args:
            response: Polished document text.
            doc_type: Documentation type.
            audience: Target audience.
            tier: Model tier used.
            input_data: Original input data.
            parsed_data: Parsed XML response data.

        Returns:
            Result dictionary with document and metadata.

        """
        result: dict[str, Any] = {
            "document": response,
            "doc_type": doc_type,
            "audience": audience,
            "model_tier_used": tier.value,
            "accumulated_cost": self._accumulated_cost,
            "auth_mode_used": self._auth_mode_used,
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

        # Add formatted report
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

        return result
