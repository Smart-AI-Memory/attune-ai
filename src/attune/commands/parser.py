"""Command Markdown Parser

Parses command markdown files with optional YAML frontmatter.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from attune.commands.models import CommandCategory, CommandConfig, CommandMetadata
from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# YAML frontmatter regex pattern (matches --- at start)
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)

# Pattern to extract title from first line (for files without frontmatter)
TITLE_PATTERN = re.compile(r"^#?\s*(.+?)(?:\s*-\s*(.+))?$")


class CommandParser:
    """Parser for command markdown files.

    Supports two formats:
    1. With YAML frontmatter (preferred for new commands)
    2. Plain markdown (legacy format, extracts name from filename/title)

    Example with frontmatter:
        ---
        name: compact
        description: Strategic context compaction
        category: context
        aliases: [comp]
        ---

        ## Overview
        This command preserves collaboration state...

    Example without frontmatter:
        Create a git commit with a well-formatted message.

        ## Execution Steps
        ...
    """

    # Category inference from command name patterns
    CATEGORY_PATTERNS: dict[str, CommandCategory] = {
        r"commit|pr|review-pr": CommandCategory.GIT,
        r"test|coverage": CommandCategory.TEST,
        r"docs|manage-docs|explain": CommandCategory.DOCS,
        r"security|scan": CommandCategory.SECURITY,
        r"bench|profile|perf": CommandCategory.PERFORMANCE,
        r"pattern|learn|evaluate": CommandCategory.LEARNING,
        r"compact|context|memory": CommandCategory.CONTEXT,
    }

    def __init__(self):
        """Initialize the parser."""

    def parse_file(self, file_path: str | Path) -> CommandConfig:
        """Parse a command markdown file.

        Args:
            file_path: Path to the command markdown file

        Returns:
            CommandConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        validated_path = _validate_file_path(str(file_path))

        if not validated_path.exists():
            raise FileNotFoundError(f"Command file not found: {validated_path}")

        with open(validated_path, encoding="utf-8") as f:
            content = f.read()

        return self.parse_content(content, source=validated_path)

    def parse_content(
        self,
        content: str,
        source: Path | str | None = None,
    ) -> CommandConfig:
        """Parse command markdown content.

        Args:
            content: Markdown content (optionally with YAML frontmatter)
            source: Source file path (used for name inference)

        Returns:
            CommandConfig instance

        """
        source_path = Path(source) if source else None
        source_str = str(source) if source else "unknown"

        # Try to extract frontmatter
        match = FRONTMATTER_PATTERN.match(content)

        if match:
            # Has frontmatter
            frontmatter_yaml = match.group(1)
            body = content[match.end() :].strip()
            metadata = self._parse_frontmatter(frontmatter_yaml, source_str)
        else:
            # No frontmatter - infer from content
            body = content.strip()
            metadata = self._infer_metadata(body, source_path)

        # Ensure name is set
        if not metadata.name:
            if source_path:
                metadata.name = source_path.stem
            else:
                raise ValueError(f"Cannot determine command name: {source_str}")

        # Extract description from first line if not set
        if not metadata.description:
            metadata.description = self._extract_description(body)

        return CommandConfig(
            name=metadata.name,
            description=metadata.description,
            body=body,
            metadata=metadata,
            source_file=source_path,
        )

    def _parse_frontmatter(
        self,
        yaml_content: str,
        source: str,
    ) -> CommandMetadata:
        """Parse YAML frontmatter into metadata.

        Args:
            yaml_content: YAML content from frontmatter
            source: Source identifier for errors

        Returns:
            CommandMetadata instance

        """
        try:
            import yaml

            data = yaml.safe_load(yaml_content) or {}
        except ImportError:
            logger.warning("PyYAML not installed, using basic parsing")
            data = self._basic_yaml_parse(yaml_content)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Invalid YAML frontmatter in {source}: {e}") from e

        return CommandMetadata.from_dict(data)

    def _basic_yaml_parse(self, yaml_content: str) -> dict[str, Any]:
        """Basic YAML parsing without PyYAML (for simple key: value pairs).

        Args:
            yaml_content: Simple YAML content

        Returns:
            Parsed dictionary

        """
        result: dict[str, Any] = {}

        for line in yaml_content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Handle simple arrays [a, b, c]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
                # Handle booleans
                elif value.lower() in ("true", "yes"):
                    value = True
                elif value.lower() in ("false", "no"):
                    value = False
                # Handle strings
                else:
                    value = value.strip("'\"")

                result[key] = value

        return result

    def _infer_metadata(
        self,
        body: str,
        source_path: Path | None,
    ) -> CommandMetadata:
        """Infer metadata from content when no frontmatter present.

        Args:
            body: Markdown body content
            source_path: Source file path

        Returns:
            CommandMetadata with inferred values

        """
        name = ""
        description = ""

        # Get name from filename
        if source_path:
            name = source_path.stem

        # Try to extract description from first line
        first_line = body.split("\n", maxsplit=1)[0].strip() if body else ""
        if first_line:
            # Remove markdown heading prefix
            if first_line.startswith("#"):
                first_line = first_line.lstrip("#").strip()

            # Check for "title - description" format
            title_match = TITLE_PATTERN.match(first_line)
            if title_match:
                if title_match.group(2):
                    description = title_match.group(2).strip()
                else:
                    description = title_match.group(1).strip()

        # Infer category from name
        category = self._infer_category(name)

        return CommandMetadata(
            name=name,
            description=description,
            category=category,
        )

    def _infer_category(self, name: str) -> CommandCategory:
        """Infer command category from name.

        Args:
            name: Command name

        Returns:
            Inferred category

        """
        name_lower = name.lower()

        for pattern, category in self.CATEGORY_PATTERNS.items():
            if re.search(pattern, name_lower):
                return category

        return CommandCategory.UTILITY

    def _extract_description(self, body: str) -> str:
        """Extract description from body content.

        Args:
            body: Markdown body

        Returns:
            Extracted description

        """
        if not body:
            return ""

        lines = body.strip().split("\n")
        first_line = lines[0].strip()

        # Remove markdown heading prefix
        if first_line.startswith("#"):
            first_line = first_line.lstrip("#").strip()

        # Check for "title - description" format
        if " - " in first_line:
            return first_line.split(" - ", 1)[1].strip()

        # Use first line if it looks like a description
        if first_line and not first_line.startswith("```"):
            return first_line[:200]  # Limit length

        return ""

    def validate_file(self, file_path: str | Path) -> list[str]:
        """Validate a command file without fully parsing.

        Args:
            file_path: Path to validate

        Returns:
            List of validation error messages (empty if valid)

        """
        errors: list[str] = []
        file_path = Path(file_path)

        if not file_path.exists():
            return [f"File not found: {file_path}"]

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            return [f"Cannot read file: {e}"]

        # Check if file has content
        if not content.strip():
            errors.append("File is empty")
            return errors

        # Check frontmatter if present
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                import yaml

                frontmatter = yaml.safe_load(match.group(1)) or {}

                # Validate name if provided
                name = frontmatter.get("name", "")
                if name and not re.match(r"^[a-z0-9][-a-z0-9]*$", name):
                    errors.append(
                        f"Invalid command name '{name}'. "
                        "Use lowercase letters, numbers, and hyphens.",
                    )

                # Validate category if provided
                category = frontmatter.get("category", "")
                if category:
                    try:
                        CommandCategory(category)
                    except ValueError:
                        valid = ", ".join(c.value for c in CommandCategory)
                        errors.append(f"Invalid category '{category}'. Valid: {valid}")

            except ImportError:
                pass  # Skip YAML validation if not installed
            except Exception as e:  # noqa: BLE001
                errors.append(f"Invalid YAML frontmatter: {e}")

        # Check body has content
        body_start = match.end() if match else 0
        body = content[body_start:].strip()

        if not body:
            errors.append("Command has no body content")

        return errors
