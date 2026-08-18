"""Document Generation Chunked Operations.

Chunked writing, polishing, export, and display utilities for doc generation.
Extracted from workflow.py for maintainability.

Contains:
- ChunkedGenerationMixin: Chunked write/polish, export, and display methods

Expected attributes on the host class:
    max_write_tokens: int
    sections_per_chunk: int
    max_cost: float
    graceful_degradation: bool
    export_path: Path | None
    max_display_chars: int
    _accumulated_cost: float
    _total_content_tokens: int
    _partial_results: dict

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from attune.context import TokenBudgetAllocator
from attune.security.path_validation import _validate_file_path

from ..base import ModelTier
from .report_formatter import format_doc_gen_report

logger = logging.getLogger(__name__)


class ChunkedGenerationMixin:
    """Mixin providing chunked generation and display utilities for doc generation."""

    # Class-level defaults for expected attributes
    max_write_tokens: int = 16000
    sections_per_chunk: int = 3
    graceful_degradation: bool = True
    export_path: Path | None = None
    max_display_chars: int = 45000
    _accumulated_cost: float = 0.0
    _total_content_tokens: int = 0
    _partial_results: dict = {}  # noqa: RUF012

    async def _write_chunked(
        self,
        sections: list[str],
        outline: str,
        doc_type: str,
        audience: str,
        content_to_document: str,
        tier: ModelTier,
    ) -> tuple[dict, int, int]:
        """Generate documentation in chunks to avoid truncation.

        Enterprise-safe: includes cost tracking and graceful degradation.
        """
        all_content: list[str] = []
        total_input_tokens: int = 0
        total_output_tokens: int = 0
        stopped_early: bool = False
        error_message: str | None = None

        # Split sections into chunks
        chunks = []
        for i in range(0, len(sections), self.sections_per_chunk):
            chunks.append(sections[i : i + self.sections_per_chunk])

        logger.info(f"Generating documentation in {len(chunks)} chunks")

        for chunk_idx, chunk_sections in enumerate(chunks):
            sections_list = ", ".join(chunk_sections)

            # Build context about what came before
            previous_context = ""
            if chunk_idx > 0 and all_content:
                # Include last 500 chars of previous content for continuity
                previous_context = f"""
Previous sections already written (for context/continuity):
...{all_content[-1][-500:]}

Continue with the next sections, maintaining consistent style and terminology."""

            system = f"""You are an expert technical writer creating comprehensive developer documentation.

Write ONLY these sections (part {chunk_idx + 1} of {len(chunks)}): {sections_list}

YOUR TASK FOR THESE SECTIONS (TWO PHASES):

═══════════════════════════════════════════════════════════════
PHASE 1: Comprehensive Content
═══════════════════════════════════════════════════════════════
- Write clear explanations and overviews
- Include real, executable code examples (extract from source)
- Show usage patterns and workflows
- Add best practices and common patterns
- Professional language for {audience}

═══════════════════════════════════════════════════════════════
PHASE 2: Structured API Reference
═══════════════════════════════════════════════════════════════
For EACH function/method in these sections, add:

### `function_name()`

**Function Signature:**
```python
def function_name(params) -> return_type
```

**Description:**
[Brief description]

**Args:**
- `param` (`type`): Description

**Returns:**
- `type`: Description

**Raises:**
- `Exception`: When it occurs

**Example:**
```python
# Real usage example
```

═══════════════════════════════════════════════════════════════
Complete BOTH phases for these sections.
═══════════════════════════════════════════════════════════════"""

            user_message = f"""Write comprehensive documentation for these sections in TWO PHASES:

Sections to write: {sections_list}

Document Type: {doc_type}
Target Audience: {audience}

Source code (extract actual functions/classes from here):
{TokenBudgetAllocator().fit_source(content_to_document, token_limit=750)}

Full outline (for context):
{outline}
{previous_context}

PHASE 1: Write comprehensive content with real code examples
PHASE 2: Add structured API reference sections with **Args:**, **Returns:**, **Raises:**

Generate complete sections now, ensuring both phases are complete."""

            try:
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system,
                    user_message,
                    max_tokens=self.max_write_tokens // len(chunks) + 2000,
                )

                # Track cost and check limits
                _, should_stop = self._track_cost(tier, input_tokens, output_tokens)

                all_content.append(response)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                logger.info(
                    f"Chunk {chunk_idx + 1}/{len(chunks)} complete: "
                    f"{len(response)} chars, {output_tokens} tokens, "
                    f"cost so far: ${self._accumulated_cost:.2f}",
                )

                # Check cost limit
                if should_stop:
                    stopped_early = True
                    remaining = len(chunks) - chunk_idx - 1
                    error_message = (
                        f"Cost limit reached (${self._accumulated_cost:.2f}). "
                        f"Stopped after {chunk_idx + 1}/{len(chunks)} chunks. "
                        f"{remaining} chunks not generated."
                    )
                    logger.warning(error_message)
                    break

            except Exception as e:  # noqa: BLE001
                error_message = f"Error generating chunk {chunk_idx + 1}: {e}"
                logger.error(error_message)
                if not self.graceful_degradation:
                    raise
                stopped_early = True
                break

        # Combine all chunks
        combined_document = "\n\n".join(all_content)
        self._total_content_tokens = total_output_tokens

        # Store partial results for graceful degradation
        self._partial_results = {
            "draft_document": combined_document,
            "sections_completed": len(all_content),
            "sections_total": len(chunks),
        }

        result = {
            "draft_document": combined_document,
            "doc_type": doc_type,
            "audience": audience,
            "outline": outline,
            "chunked": True,
            "chunk_count": len(chunks),
            "chunks_completed": len(all_content),
            "stopped_early": stopped_early,
            "accumulated_cost": self._accumulated_cost,
            "source_code": content_to_document,  # Pass through for API reference generation
        }

        if error_message:
            result["warning"] = error_message

        return (result, total_input_tokens, total_output_tokens)

    async def _polish_chunked(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Polish large documents in chunks to avoid truncation.

        Splits the document by section headers and polishes each chunk separately,
        then combines the results.
        """
        draft_document = input_data.get("draft_document", "")
        doc_type = input_data.get("doc_type", "general")
        audience = input_data.get("audience", "developers")

        # Split document by major section headers (## headers)
        sections = re.split(r"(?=^## )", draft_document, flags=re.MULTILINE)
        sections = [s.strip() for s in sections if s.strip()]

        if len(sections) <= 1:
            # If we can't split by sections, split by character count
            chunk_size = 15000  # ~3750 tokens per chunk
            sections = [
                draft_document[i : i + chunk_size]
                for i in range(0, len(draft_document), chunk_size)
            ]

        logger.info(f"Polishing document in {len(sections)} chunks")

        polished_chunks: list[str] = []
        total_input_tokens: int = 0
        total_output_tokens: int = 0

        for chunk_idx, section in enumerate(sections):
            system = """You are a senior technical editor specializing in developer documentation.

Polish this section to production quality. The writer was asked to complete TWO PHASES:
1. Comprehensive content with real examples
2. Structured API reference with **Args:**, **Returns:**, **Raises:** for every function

Verify both phases are complete in this section:

═══════════════════════════════════════════════════════════════
CRITICAL: Check for Missing API Reference Format
═══════════════════════════════════════════════════════════════

1. **Scan for functions/methods in this section**
   - If any function is missing **Args:**, **Returns:**, **Raises:** sections, ADD them
   - Format: **Args:**, **Returns:**, **Raises:** (bold headers with colons)
   - Write "None" if no parameters/returns/exceptions

2. **Polish API Documentation**:
   - Verify parameters documented with types in backticks
   - Ensure return values and exceptions are clear
   - Validate code examples are complete

3. **Polish General Content**:
   - Ensure all examples are runnable with proper imports
   - Standardize terminology and formatting
   - Fix grammatical issues
   - Remove TODOs and placeholders

Return ONLY the polished section. Do not add commentary about changes."""

            user_message = f"""Polish this section to production quality (part {chunk_idx + 1} of {len(sections)}):

Document Type: {doc_type}
Target Audience: {audience}

Section to polish:
{section}

Check if all functions have **Args:**, **Returns:**, **Raises:** sections - add if missing.
Make all code examples complete and executable."""

            try:
                response, input_tokens, output_tokens = await self._call_llm(
                    tier,
                    system,
                    user_message,
                    max_tokens=8000,
                )

                # Track cost
                _, should_stop = self._track_cost(tier, input_tokens, output_tokens)

                polished_chunks.append(response)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                logger.info(
                    f"Polish chunk {chunk_idx + 1}/{len(sections)} complete, "
                    f"cost so far: ${self._accumulated_cost:.2f}",
                )

                if should_stop:
                    logger.warning(
                        f"Cost limit reached during polish. "
                        f"Returning {len(polished_chunks)}/{len(sections)} polished chunks.",
                    )
                    # Add remaining sections unpolished
                    polished_chunks.extend(sections[chunk_idx + 1 :])
                    break

            except Exception as e:  # noqa: BLE001
                logger.error(f"Error polishing chunk {chunk_idx + 1}: {e}")
                if self.graceful_degradation:
                    # Keep original section on error
                    polished_chunks.append(section)
                else:
                    raise

        # Combine polished chunks
        polished_document = "\n\n".join(polished_chunks)

        # Add structured API reference sections (Step 4: Post-processing)
        source_code = input_data.get("source_code", "")
        if source_code:
            logger.info("Adding structured API reference sections to chunked polished document...")
            polished_document = await self._add_api_reference_sections(
                narrative_doc=polished_document,
                source_code=source_code,
                tier=ModelTier.CHEAP,  # Use cheap tier for structured extraction
            )
        else:
            logger.warning("No source code available for API reference generation")

        result = {
            "document": polished_document,
            "doc_type": doc_type,
            "audience": audience,
            "model_tier_used": tier.value,
            "polish_chunked": True,
            "polish_chunks": len(sections),
            "accumulated_cost": self._accumulated_cost,
        }

        # Add formatted report
        result["formatted_report"] = format_doc_gen_report(result, input_data)

        # Export documentation if export_path is configured
        doc_path, report_path = self._export_document(
            document=polished_document,
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

        return (result, total_input_tokens, total_output_tokens)

    def _export_document(
        self,
        document: str,
        doc_type: str,
        report: str | None = None,
    ) -> tuple[Path | None, Path | None]:
        """Export generated documentation to file.

        Args:
            document: The generated documentation content
            doc_type: Document type for naming
            report: Optional report to save alongside document

        Returns:
            Tuple of (doc_path, report_path) or (None, None) if export disabled

        """
        if not self.export_path:
            return None, None

        # Create export directory
        self.export_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_doc_type = doc_type.replace(" ", "_").replace("/", "-").lower()
        doc_filename = f"{safe_doc_type}_{timestamp}.md"
        report_filename = f"{safe_doc_type}_{timestamp}_report.txt"

        doc_path = self.export_path / doc_filename
        report_path = self.export_path / report_filename if report else None

        # Write document
        try:
            validated_doc_path = _validate_file_path(str(doc_path))
            validated_doc_path.write_text(document, encoding="utf-8")
            logger.info(f"Documentation exported to: {validated_doc_path}")

            # Write report if provided
            if report and report_path:
                validated_report_path = _validate_file_path(str(report_path))
                validated_report_path.write_text(report, encoding="utf-8")
                logger.info(f"Report exported to: {validated_report_path}")

            return validated_doc_path, validated_report_path if report else None
        except (OSError, ValueError) as e:
            logger.error(f"Failed to export documentation: {e}")
            return None, None

    def _chunk_output_for_display(self, content: str, chunk_prefix: str = "PART") -> list[str]:
        """Split large output into displayable chunks.

        Args:
            content: The content to chunk
            chunk_prefix: Prefix for chunk headers

        Returns:
            List of content chunks, each under max_display_chars

        """
        if len(content) <= self.max_display_chars:
            return [content]

        chunks = []
        # Try to split on section boundaries (## headers)
        sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

        current_chunk = ""
        chunk_num = 1

        for section in sections:
            # If adding this section would exceed limit, save current chunk
            if current_chunk and len(current_chunk) + len(section) > self.max_display_chars:
                chunks.append(
                    f"{'=' * 60}\n{chunk_prefix} {chunk_num} of {{total}}\n{'=' * 60}\n\n"
                    + current_chunk,
                )
                chunk_num += 1
                current_chunk = section
            else:
                current_chunk += section

        # Add final chunk
        if current_chunk:
            chunks.append(
                f"{'=' * 60}\n{chunk_prefix} {chunk_num} of {{total}}\n{'=' * 60}\n\n"
                + current_chunk,
            )

        # Update total count in all chunks
        total = len(chunks)
        chunks = [chunk.format(total=total) for chunk in chunks]

        return chunks
