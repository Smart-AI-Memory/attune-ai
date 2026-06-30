"""Empathy LLM - Core Wrapper

Main class that wraps any LLM provider with Attune AI levels.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import time
from typing import Any

# Import from consolidated memory module
from attune.memory import (
    AuditLogger,
    ClaudeMemoryConfig,
    ClaudeMemoryLoader,
    PIIScrubber,
    SecretsDetector,
    SecurityError,
)
from attune.routing import ModelRouter

# Re-export security classes so existing patch targets like
# "attune.llm.core.AuditLogger" continue to resolve.
__all__ = ["AuditLogger", "EmpathyLLM", "PIIScrubber", "SecretsDetector", "SecurityError"]

from .interaction import InteractionMixin
from .levels import EmpathyLevel
from .providers import (
    AnthropicProvider,
    BaseLLMProvider,
)
from .security import SecurityMixin
from .state import CollaborationState, UserPattern

logger = logging.getLogger(__name__)


class EmpathyLLM(SecurityMixin, InteractionMixin):
    """Wraps any LLM provider with Attune AI levels.

    Automatically progresses from Level 1 (reactive) to Level 4 (anticipatory)
    based on user collaboration state.

    Security Features (Phase 3):
        - PII Scrubbing: Automatically detect and redact PII from user inputs
        - Secrets Detection: Block requests containing API keys, passwords, etc.
        - Audit Logging: Comprehensive compliance logging (SOC2, HIPAA, GDPR)
        - Backward Compatible: Security disabled by default

    Example:
        >>> llm = EmpathyLLM(provider="anthropic", target_level=4)
        >>> response = await llm.interact(
        ...     user_id="developer_123",
        ...     user_input="Help me optimize my code",
        ...     context={"code_snippet": "..."}
        ... )
        >>> print(response["content"])

    Example with Security:
        >>> llm = EmpathyLLM(
        ...     provider="anthropic",
        ...     target_level=4,
        ...     enable_security=True,
        ...     security_config={
        ...         "audit_log_dir": "/var/log/empathy",
        ...         "block_on_secrets": True,
        ...         "enable_pii_scrubbing": True
        ...     }
        ... )
        >>> response = await llm.interact(
        ...     user_id="user@company.com",
        ...     user_input="My email is john@example.com"
        ... )
        >>> # PII automatically scrubbed, request logged

    Example with Model Routing (Cost Optimization):
        >>> llm = EmpathyLLM(
        ...     provider="anthropic",
        ...     enable_model_routing=True  # Enable smart model selection
        ... )
        >>> # Simple task -> uses Haiku (cheap)
        >>> response = await llm.interact(
        ...     user_id="dev",
        ...     user_input="Summarize this function",
        ...     task_type="summarize"
        ... )
        >>> # Complex task -> uses Opus (premium)
        >>> response = await llm.interact(
        ...     user_id="dev",
        ...     user_input="Design the architecture",
        ...     task_type="architectural_decision"
        ... )

    """

    def __init__(
        self,
        provider: str = "anthropic",
        target_level: int = 3,
        api_key: str | None = None,
        model: str | None = None,
        pattern_library: dict | None = None,
        claude_memory_config: ClaudeMemoryConfig | None = None,
        project_root: str | None = None,
        enable_security: bool | None = None,
        security_config: dict | None = None,
        enable_model_routing: bool = False,
        **kwargs: Any,
    ):
        """Initialize EmpathyLLM.

        Args:
            provider: "anthropic"
            target_level: Target empathy level (1-5)
            api_key: API key for provider (if needed)
            model: Specific model to use (overrides routing if set)
            pattern_library: Shared pattern library (Level 5)
            claude_memory_config: Configuration for Claude memory integration (v1.8.0+)
            project_root: Project root directory for loading .claude/CLAUDE.md
            enable_security: Enable Phase 2 security controls.
                - If None (default): Check ATTUNE_ENABLE_SECURITY env var
                - If env var not set: Defaults to False (disabled)
                - In production environments, a warning is logged if security is disabled
            security_config: Security configuration dictionary with options:
                - audit_log_dir: Directory for audit logs (default: "./logs")
                - block_on_secrets: Block requests with detected secrets (default: True)
                - enable_pii_scrubbing: Enable PII detection/scrubbing (default: True)
                - enable_name_detection: Enable name PII detection (default: False)
                - enable_audit_logging: Enable audit logging (default: True)
                - enable_console_logging: Log to console for debugging (default: False)
            enable_model_routing: Enable smart model routing for cost optimization.
                When enabled, uses ModelRouter to select appropriate model tier:
                - CHEAP (Haiku): summarize, classify, triage tasks
                - CAPABLE (Sonnet): code generation, bug fixes, security review
                - PREMIUM (Opus): coordination, synthesis, architectural decisions
            **kwargs: Provider-specific options

        """
        import os
        import warnings

        self.target_level = target_level
        self.pattern_library = pattern_library or {}
        self.project_root = project_root
        self._provider_name = provider
        self._explicit_model = model  # Track if user explicitly set a model

        # Resolve enable_security from env var if not explicitly set
        if enable_security is None:
            env_security = os.getenv("ATTUNE_ENABLE_SECURITY", "").lower()
            enable_security = env_security in ("1", "true", "yes", "on")

        # Production environment detection
        is_production = self._detect_production_environment()

        # Warn if security disabled in production
        if not enable_security and is_production:
            warning_msg = (
                "SECURITY WARNING: Security controls are disabled in a production environment. "
                "This exposes your application to PII leakage and credential exposure risks. "
                "Enable security by setting ATTUNE_ENABLE_SECURITY=true or passing "
                "enable_security=True."
            )
            logger.warning(warning_msg)
            warnings.warn(warning_msg, UserWarning, stacklevel=2)

        # Initialize provider
        self.provider = self._create_provider(provider, api_key, model, **kwargs)

        # Track collaboration states for different users
        self.states: dict[str, CollaborationState] = {}

        # Initialize model routing for cost optimization
        self.enable_model_routing = enable_model_routing
        self.model_router: ModelRouter | None = None
        if enable_model_routing:
            self.model_router = ModelRouter(default_provider=provider)
            logger.info(f"Model routing enabled for provider: {provider}")

        # Initialize Claude memory integration (v1.8.0+)
        self.claude_memory_config = claude_memory_config
        self.claude_memory_loader = None
        self._cached_memory = None

        if claude_memory_config and claude_memory_config.enabled:
            self.claude_memory_loader = ClaudeMemoryLoader(claude_memory_config)
            # Load memory once at initialization
            self._cached_memory = self.claude_memory_loader.load_all_memory(project_root)
            logger.info(
                f"EmpathyLLM initialized with Claude memory: "
                f"{len(self._cached_memory)} chars loaded",
            )

        # Initialize Phase 3 security controls (v1.8.0+)
        self.enable_security = enable_security
        self.security_config = security_config or {}
        self.pii_scrubber = None
        self.secrets_detector = None
        self.audit_logger = None

        if enable_security:
            self._initialize_security()

        logger.info(
            f"EmpathyLLM initialized: provider={provider}, target_level={target_level}, "
            f"security={'enabled' if enable_security else 'disabled'}, "
            f"model_routing={'enabled' if enable_model_routing else 'disabled'}",
        )

    def _create_provider(
        self,
        provider: str,
        api_key: str | None,
        model: str | None,
        **kwargs,
    ) -> BaseLLMProvider:
        """Create appropriate provider instance.

        Falls back to environment variables if api_key not provided:
        - ANTHROPIC_API_KEY for Anthropic
        """
        import os

        # Check environment variables if api_key not provided
        if api_key is None:
            if provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")

        if provider == "anthropic":
            return AnthropicProvider(
                api_key=api_key,
                model=model or "claude-sonnet-5",
                **kwargs,
            )
        raise ValueError(f"Unknown provider: {provider}")

    def _initialize_security(self) -> None:
        """Initialize Phase 3 security modules based on configuration."""
        # Extract security config options
        enable_pii_scrubbing = self.security_config.get("enable_pii_scrubbing", True)
        enable_name_detection = self.security_config.get("enable_name_detection", False)
        enable_audit_logging = self.security_config.get("enable_audit_logging", True)
        audit_log_dir = self.security_config.get("audit_log_dir", "./logs")
        enable_console_logging = self.security_config.get("enable_console_logging", False)

        # Initialize PII Scrubber
        if enable_pii_scrubbing:
            self.pii_scrubber = PIIScrubber(enable_name_detection=enable_name_detection)
            logger.info("PII Scrubber initialized")

        # Initialize Secrets Detector
        self.secrets_detector = SecretsDetector(
            enable_entropy_analysis=True,
            entropy_threshold=4.5,
            min_entropy_length=20,
        )
        logger.info("Secrets Detector initialized")

        # Initialize Audit Logger
        if enable_audit_logging:
            self.audit_logger = AuditLogger(
                log_dir=audit_log_dir,
                enable_console_logging=enable_console_logging,
            )
            logger.info(f"Audit Logger initialized: {audit_log_dir}")

    def _get_or_create_state(self, user_id: str) -> CollaborationState:
        """Get or create collaboration state for user."""
        if user_id not in self.states:
            self.states[user_id] = CollaborationState(user_id=user_id)
        return self.states[user_id]

    def _determine_level(self, state: CollaborationState) -> int:
        """Determine which empathy level to use.

        Progresses automatically based on state, up to target_level.
        """
        # Start at Level 1
        level = 1

        # Progress through levels if state allows
        for candidate_level in range(2, self.target_level + 1):
            if state.should_progress_to_level(candidate_level):
                level = candidate_level
            else:
                break

        return level

    def reload_memory(self) -> None:
        """Reload Claude memory files.

        Useful if CLAUDE.md files have been updated during runtime.
        Call this to pick up changes without restarting.
        """
        if self.claude_memory_loader:
            # Clear cache before reloading to pick up file changes
            self.claude_memory_loader.clear_cache()
            self._cached_memory = self.claude_memory_loader.load_all_memory(self.project_root)
            logger.info(f"Claude memory reloaded: {len(self._cached_memory)} chars")
        else:
            logger.warning("Claude memory not enabled, cannot reload")

    async def interact(
        self,
        user_id: str,
        user_input: str,
        context: dict[str, Any] | None = None,
        force_level: int | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        """Main interaction method.

        Automatically selects appropriate empathy level and responds.

        Phase 3 Security Pipeline (if enabled):
            1. PII Scrubbing: Detect and redact PII from user input
            2. Secrets Detection: Block requests containing secrets
            3. LLM Interaction: Process sanitized input
            4. Audit Logging: Log request details for compliance

        Model Routing (if enable_model_routing=True):
            Routes to appropriate model based on task_type:
            - CHEAP (Haiku): summarize, classify, triage, match_pattern
            - CAPABLE (Sonnet): generate_code, fix_bug, review_security, write_tests
            - PREMIUM (Opus): coordinate, synthesize_results, architectural_decision

        Args:
            user_id: Unique user identifier
            user_input: User's input/question
            context: Optional context dictionary
            force_level: Force specific level (for testing/demos)
            task_type: Type of task for model routing (e.g., "summarize", "fix_bug").
                If not provided with routing enabled, defaults to "capable" tier.

        Returns:
            Dictionary with:
                - content: LLM response
                - level_used: Which empathy level was used
                - proactive: Whether action was proactive
                - metadata: Additional information (includes routed_model if routing enabled)
                - security: Security details (if enabled)

        Raises:
            SecurityError: If secrets detected and block_on_secrets=True

        """
        start_time = time.time()
        state = self._get_or_create_state(user_id)
        context = context or {}

        # Model routing: determine which model to use for this request
        routed_model: str | None = None
        routing_metadata: dict[str, Any] = {}

        if self.enable_model_routing and self.model_router and not self._explicit_model:
            # Route based on task_type (default to "generate_code" if not specified)
            effective_task = task_type or "generate_code"
            routed_model = self.model_router.route(effective_task, self._provider_name)
            tier = self.model_router.get_tier(effective_task)

            routing_metadata = {
                "model_routing_enabled": True,
                "task_type": effective_task,
                "routed_model": routed_model,
                "routed_tier": tier.value,
            }
            logger.info(
                f"Model routing: task={effective_task} -> model={routed_model} "
                f"(tier={tier.value})",
            )

        # Security input pipeline (PII scrubbing + secrets detection)
        sanitized_input, pii_detections, secrets_detections, security_metadata = (
            self._run_security_input_pipeline(user_id, user_input)
        )

        # Determine level to use
        level = force_level if force_level is not None else self._determine_level(state)

        logger.info(f"User {user_id}: Level {level} interaction")

        # Record user input (sanitized version if security enabled)
        state.add_interaction("user", sanitized_input, level)

        # Route to appropriate level handler using sanitized input
        # Pass routed_model for cost-optimized model selection
        if level == 1:
            result = await self._level_1_reactive(sanitized_input, state, context, routed_model)
        elif level == 2:
            result = await self._level_2_guided(sanitized_input, state, context, routed_model)
        elif level == 3:
            result = await self._level_3_proactive(sanitized_input, state, context, routed_model)
        elif level == 4:
            result = await self._level_4_anticipatory(sanitized_input, state, context, routed_model)
        elif level == 5:
            result = await self._level_5_systems(sanitized_input, state, context, routed_model)
        else:
            raise ValueError(f"Invalid level: {level}")

        # Record assistant response
        state.add_interaction("assistant", result["content"], level, result.get("metadata"))

        # Add level info to result
        result["level_used"] = level
        result["level_description"] = EmpathyLevel.get_description(level)

        # Add security metadata to result
        if self.enable_security:
            result["security"] = security_metadata

        # Add model routing metadata to result
        if routing_metadata:
            result["metadata"].update(routing_metadata)

        # Security audit logging
        self._run_security_audit_log(
            user_id=user_id,
            user_input=user_input,
            result=result,
            level=level,
            pii_detections=pii_detections,
            secrets_detections=secrets_detections,
            start_time=start_time,
        )

        return result

    def update_trust(self, user_id: str, outcome: str, magnitude: float = 1.0) -> None:
        """Update trust level based on interaction outcome.

        Args:
            user_id: User identifier
            outcome: "success" or "failure"
            magnitude: How much to adjust (0.0 to 1.0)

        """
        state = self._get_or_create_state(user_id)
        state.update_trust(outcome, magnitude)

        logger.info(f"Trust updated for {user_id}: {outcome} -> {state.trust_level:.2f}")

    def add_pattern(self, user_id: str, pattern: UserPattern) -> None:
        """Manually add a detected pattern.

        Args:
            user_id: User identifier
            pattern: UserPattern instance

        """
        state = self._get_or_create_state(user_id)
        state.add_pattern(pattern)

        logger.info(f"Pattern added for {user_id}: {pattern.pattern_type.value}")

    def get_statistics(self, user_id: str) -> dict[str, Any]:
        """Get collaboration statistics for user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with stats

        """
        state = self._get_or_create_state(user_id)
        return state.get_statistics()

    def reset_state(self, user_id: str) -> None:
        """Reset collaboration state for user."""
        if user_id in self.states:
            del self.states[user_id]
            logger.info(f"State reset for {user_id}")
