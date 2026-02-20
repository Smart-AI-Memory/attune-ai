"""Security Audit Configuration

Configuration dataclass for the security audit crew.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field


@dataclass
class SecurityAuditConfig:
    """Configuration for security audit crew."""

    # API Configuration
    provider: str = "anthropic"
    api_key: str | None = None

    # Scan Configuration
    scan_depth: str = "standard"  # "quick", "standard", "thorough"
    include_patterns: list[str] = field(
        default_factory=lambda: ["*.py", "*.js", "*.ts", "*.java", "*.go"],
    )
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["*test*", "*spec*", "node_modules/*", "venv/*"],
    )

    # Memory Graph
    memory_graph_enabled: bool = True
    memory_graph_path: str = "patterns/security_memory.json"

    # Agent Tiers
    lead_tier: str = "premium"
    hunter_tier: str = "capable"
    assessor_tier: str = "capable"
    remediation_tier: str = "premium"
    compliance_tier: str = "cheap"

    # Resilience
    resilience_enabled: bool = True
    timeout_seconds: float = 300.0

    # XML Prompts
    xml_prompts_enabled: bool = True
    xml_schema_version: str = "1.0"
