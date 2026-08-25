"""Markdown Agent Parser

Parses Markdown files with YAML frontmatter into UnifiedAgentConfig.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import re
from pathlib import Path
from typing import Any

from attune.config.agent_config import ModelTier, Provider, UnifiedAgentConfig
from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# YAML frontmatter regex pattern
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)


class MarkdownAgentParser:
    """Parser for Markdown agent definition files.

    Parses files with YAML frontmatter containing agent configuration,
    followed by Markdown content that becomes the system prompt.

    Example file format:
        ---
        name: architect
        description: Software architecture specialist
        model: capable
        tools: Read, Grep, Glob
        ---

        You are an expert software architect...

    Example usage:
        parser = MarkdownAgentParser()
        config = parser.parse_file("agents/architect.md")
    """

    # Mapping from string model names to ModelTier
    MODEL_TIER_MAP = {
        "cheap": ModelTier.CHEAP,
        "haiku": ModelTier.CHEAP,
        "capable": ModelTier.CAPABLE,
        "sonnet": ModelTier.CAPABLE,
        "premium": ModelTier.PREMIUM,
        "opus": ModelTier.PREMIUM,
    }

    # Mapping from string provider names to Provider
    PROVIDER_MAP = {
        "anthropic": Provider.ANTHROPIC,
    }

    def __init__(self):
        """Initialize the parser."""

    def parse_file(self, file_path: str | Path) -> UnifiedAgentConfig:
        """Parse a Markdown agent file into UnifiedAgentConfig.

        Args:
            file_path: Path to the Markdown agent file

        Returns:
            UnifiedAgentConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid

        """
        validated_path = _validate_file_path(str(file_path))
        file_path = Path(validated_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Agent file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        return self.parse_content(content, source=str(file_path))

    def parse_content(
        self,
        content: str,
        source: str = "unknown",
    ) -> UnifiedAgentConfig:
        """Parse Markdown content into UnifiedAgentConfig.

        Args:
            content: Markdown content with YAML frontmatter
            source: Source identifier for error messages

        Returns:
            UnifiedAgentConfig instance

        Raises:
            ValueError: If content format is invalid

        """
        # Extract frontmatter
        match = FRONTMATTER_PATTERN.match(content)

        if not match:
            raise ValueError(f"Invalid agent file format - missing YAML frontmatter: {source}")

        frontmatter_yaml = match.group(1)
        body = content[match.end() :].strip()

        # Parse YAML
        try:
            import yaml

            frontmatter = yaml.safe_load(frontmatter_yaml) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {source}: {e}") from e

        return self._create_config(frontmatter, body, source)

    def _create_config(
        self,
        frontmatter: dict[str, Any],
        body: str,
        source: str,
    ) -> UnifiedAgentConfig:
        """Create UnifiedAgentConfig from parsed data.

        Args:
            frontmatter: Parsed YAML frontmatter
            body: Markdown body content
            source: Source identifier

        Returns:
            UnifiedAgentConfig instance

        """
        # Required field
        name = frontmatter.get("name")
        if not name:
            raise ValueError(f"Agent file missing required 'name' field: {source}")

        # Parse model tier
        model_str = frontmatter.get("model", "capable").lower()
        model_tier = self.MODEL_TIER_MAP.get(model_str, ModelTier.CAPABLE)

        # Parse provider
        provider_str = frontmatter.get("provider", "anthropic").lower()
        provider = self.PROVIDER_MAP.get(provider_str, Provider.ANTHROPIC)

        # Parse tools list
        tools_raw = frontmatter.get("tools", [])
        if isinstance(tools_raw, str):
            # Handle comma-separated string
            tools = [t.strip() for t in tools_raw.split(",")]
        else:
            tools = list(tools_raw)

        # Parse capabilities
        capabilities = frontmatter.get("capabilities", [])
        if isinstance(capabilities, str):
            capabilities = [c.strip() for c in capabilities.split(",")]

        # Build config
        config = UnifiedAgentConfig(
            name=name,
            role=frontmatter.get("role", name),
            description=frontmatter.get("description", ""),
            model_tier=model_tier,
            model_override=frontmatter.get("model_override"),
            provider=provider,
            memory_enabled=frontmatter.get("memory_enabled", True),
            pattern_learning=frontmatter.get("pattern_learning", True),
            cost_tracking=frontmatter.get("cost_tracking", True),
            use_patterns=frontmatter.get("use_patterns", True),
            temperature=float(frontmatter.get("temperature", 0.7)),
            max_tokens=int(frontmatter.get("max_tokens", 4096)),
            timeout=int(frontmatter.get("timeout", 120)),
            retry_attempts=int(frontmatter.get("retry_attempts", 3)),
            retry_delay=float(frontmatter.get("retry_delay", 1.0)),
            system_prompt=body or None,
            tools=tools,
            capabilities=capabilities,
            framework_options=frontmatter.get("framework_options", {}),
            extra={
                "source_file": source,
                "raw_frontmatter": frontmatter,
                "interaction_mode": frontmatter.get("interaction_mode", "standard"),
                "socratic_config": frontmatter.get("socratic_config", {}),
            },
        )

        logger.debug("Parsed agent config: %s from %s", name, source)
        return config

    def validate_file(self, file_path: str | Path) -> list[str]:
        """Validate a Markdown agent file without fully parsing.

        Args:
            file_path: Path to validate

        Returns:
            List of validation error messages (empty if valid)

        """
        errors = []

        try:
            validated_path = _validate_file_path(str(file_path))
            file_path = Path(validated_path)
        except ValueError as e:
            return [f"Invalid file path: {e}"]

        if not file_path.exists():
            return [f"File not found: {file_path}"]

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            return [f"Cannot read file: {e}"]

        # Check frontmatter
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            errors.append("Missing YAML frontmatter (must start with ---)")
            return errors

        # Parse YAML
        try:
            import yaml

            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML: {e}")
            return errors

        # Check required fields
        if not frontmatter.get("name"):
            errors.append("Missing required field: name")

        # Validate model tier
        model = frontmatter.get("model", "").lower()
        if model and model not in self.MODEL_TIER_MAP:
            errors.append(
                f"Invalid model '{model}'. Valid options: {', '.join(self.MODEL_TIER_MAP.keys())}",
            )

        # Validate provider
        provider = frontmatter.get("provider", "").lower()
        if provider and provider not in self.PROVIDER_MAP:
            errors.append(
                f"Invalid provider '{provider}'. "
                f"Valid options: {', '.join(self.PROVIDER_MAP.keys())}",
            )

        # Note: a legacy "empathy_level" frontmatter key is ignored, not
        # an error — pre-15.0.0 agent files still parse.

        return errors
