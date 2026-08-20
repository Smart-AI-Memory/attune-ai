"""Document Generation API Reference Extraction.

AST-based function extraction and structured API reference generation.
Extracted from workflow.py for maintainability.

Contains:
- APIReferenceMixin: Source code parsing and API section generation

Expected attributes on the host class: (none beyond _call_llm, _track_cost from base/mixins)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ast
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import ModelTier

logger = logging.getLogger(__name__)


class APIReferenceMixin:
    """Mixin providing API reference extraction and generation for doc generation."""

    def _extract_functions_from_source(self, source_code: str) -> list[dict]:
        """Extract function information from source code using AST.

        Args:
            source_code: Python source code to parse

        Returns:
            List of dicts with function information (name, args, returns, docstring)

        """
        functions = []

        try:
            tree = ast.parse(source_code)
        except (
            SyntaxError,
            ValueError,
        ) as e:  # ast.parse: null bytes -> ValueError, not SyntaxError
            logger.warning(f"Failed to parse source code: {e}")
            return functions

        for node in ast.walk(tree):
            # Extract top-level functions and class methods
            if isinstance(node, ast.FunctionDef):
                # Skip private functions (starting with _)
                if node.name.startswith("_"):
                    continue

                # Extract function signature
                args_list = []
                for arg in node.args.args:
                    arg_name = arg.arg
                    # Get type annotation if available
                    arg_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
                    args_list.append({"name": arg_name, "type": arg_type})

                # Extract return type
                return_type = ast.unparse(node.returns) if node.returns else "Any"

                # Extract docstring
                docstring = ast.get_docstring(node) or ""

                functions.append(
                    {
                        "name": node.name,
                        "args": args_list,
                        "return_type": return_type,
                        "docstring": docstring,
                        "lineno": node.lineno,
                    },
                )

        return functions

    async def _generate_api_section_for_function(
        self,
        func_info: dict,
        tier: ModelTier,
    ) -> str:
        """Generate structured API reference section for a single function.

        This is a focused prompt that ONLY asks for Args/Returns/Raises format,
        not narrative documentation.

        Args:
            func_info: Function information from AST extraction
            tier: Model tier to use for generation

        Returns:
            Markdown formatted API reference section

        """
        func_name = func_info["name"]
        args_list = func_info["args"]
        return_type = func_info["return_type"]
        docstring = func_info["docstring"]

        # Build function signature
        args_str = ", ".join([f"{arg['name']}: {arg['type']}" for arg in args_list])
        signature = f"def {func_name}({args_str}) -> {return_type}"

        system = """You are an API documentation generator. Output ONLY structured API reference sections in the EXACT format specified below.

CRITICAL: Do NOT write explanatory text, questions, or narrative. Output ONLY the formatted section.

REQUIRED FORMAT (copy this structure EXACTLY, replace bracketed content):

### `function_name()`

**Function Signature:**
```python
def function_name(param: type) -> return_type
```

**Description:**
Brief 1-2 sentence description.

**Args:**
- `param_name` (`type`): Parameter description

**Returns:**
- `return_type`: Return value description

**Raises:**
- `ExceptionType`: When this exception occurs

IMPORTANT:
- Use "**Args:**" (NOT "Parameters" or "params")
- Write "None" if no Args/Returns/Raises
- NO conversational text - just the formatted section"""

        user_message = f"""Generate API reference section using EXACT format specified in system prompt.

Function:
```python
{signature}
```

Docstring:
{docstring or "No docstring"}

Output the formatted section EXACTLY as shown in system prompt. Use **Args:** (not Parameters). NO conversational text."""

        try:
            response, input_tokens, output_tokens = await self._call_llm(
                tier,
                system,
                user_message,
                max_tokens=1000,  # Small response - just the structured section
            )

            # Track cost
            self._track_cost(tier, input_tokens, output_tokens)

            return response

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to generate API section for {func_name}: {e}")
            # Return minimal fallback
            return f"""### `{func_name}()`

**Function Signature:**
```python
{signature}
```

**Description:**
{docstring.split('.')[0] if docstring else "No description available."}

**Args:**
None

**Returns:**
- `{return_type}`: Return value

**Raises:**
None
"""

    async def _add_api_reference_sections(
        self,
        narrative_doc: str,
        source_code: str,
        tier: ModelTier,
    ) -> str:
        """Add structured API reference sections to narrative documentation.

        This is Step 4 of the pipeline: after outline, write, and polish,
        we add structured API reference sections extracted from source code.

        Args:
            narrative_doc: The polished narrative documentation
            source_code: Original source code to extract functions from
            tier: Model tier to use for API section generation

        Returns:
            Complete documentation with API reference appendix

        """
        logger.info("Adding structured API reference sections...")

        # Extract functions from source code
        functions = self._extract_functions_from_source(source_code)

        if not functions:
            logger.warning("No public functions found in source code")
            return narrative_doc

        logger.info(f"Found {len(functions)} public functions to document")

        # Generate API section for each function
        api_sections = []
        for func_info in functions:
            func_name = func_info["name"]
            logger.debug(f"Generating API reference for {func_name}()")

            api_section = await self._generate_api_section_for_function(func_info, tier)
            api_sections.append(api_section)

        # Append API reference section to narrative doc
        full_doc = narrative_doc
        full_doc += "\n\n---\n\n"
        full_doc += "## API Reference\n\n"
        full_doc += "Complete structured reference for all public functions:\n\n"
        full_doc += "\n\n".join(api_sections)

        logger.info(f"Added {len(api_sections)} API reference sections")

        return full_doc
