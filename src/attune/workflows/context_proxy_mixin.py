"""WorkflowContext proxy methods for BaseWorkflow.

When self._ctx is set and the relevant service exists, these methods
delegate to the service. Otherwise they fall back to the mixin via
super(), preserving 100% backward compatibility.

Phase 2C of the BaseWorkflow refactoring — composition-based capabilities.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

from .caching import CachedResponse


class ContextProxyMixin:
    """Proxy methods that delegate to WorkflowContext services.

    When BaseWorkflow._ctx is set, these methods route to the
    appropriate service. When _ctx is None, they fall through
    to the mixin implementations via super().
    """

    # --- Cache proxies (CachingMixin -> CacheService) ---

    def _maybe_setup_cache(self) -> None:
        """Set up cache -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            self._ctx.cache.setup()
            return
        super()._maybe_setup_cache()

    def _try_cache_lookup(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
    ) -> CachedResponse | None:
        """Try cache lookup -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.lookup(stage, system, user_message, model)
        return super()._try_cache_lookup(stage, system, user_message, model)

    def _store_in_cache(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
        response: CachedResponse,
    ) -> bool:
        """Store in cache -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.store(stage, system, user_message, model, response)
        return super()._store_in_cache(stage, system, user_message, model, response)

    def _get_cache_type(self) -> str:
        """Get cache type -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.get_cache_type()
        return super()._get_cache_type()

    def _get_cache_stats(self) -> dict[str, Any]:
        """Get cache stats -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.get_stats()
        return super()._get_cache_stats()

    # --- Cost proxies (CostTrackingMixin -> CostService) ---

    def _calculate_cost(self, tier: Any, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.calculate_cost(tier, input_tokens, output_tokens)
        return super()._calculate_cost(tier, input_tokens, output_tokens)

    def _calculate_baseline_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate baseline cost -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.calculate_baseline_cost(input_tokens, output_tokens)
        return super()._calculate_baseline_cost(input_tokens, output_tokens)

    def _generate_cost_report(self) -> Any:
        """Generate cost report -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.generate_report(self._stages_run)
        return super()._generate_cost_report()

    # --- Telemetry proxies (TelemetryMixin -> TelemetryService) ---

    def _track_telemetry(
        self,
        stage: str,
        tier: Any,
        model: str,
        cost: float,
        tokens: dict[str, int],
        cache_hit: bool,
        cache_type: str | None,
        duration_ms: int,
        prompt_cache_creation_tokens: int = 0,
        prompt_cache_read_tokens: int = 0,
    ) -> None:
        """Track telemetry -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            self._ctx.telemetry.track_call(
                stage=stage,
                tier=tier,
                model=model,
                cost=cost,
                tokens=tokens,
                cache_hit=cache_hit,
                cache_type=cache_type,
                duration_ms=duration_ms,
                prompt_cache_creation_tokens=prompt_cache_creation_tokens,
                prompt_cache_read_tokens=prompt_cache_read_tokens,
            )
            return
        super()._track_telemetry(
            stage,
            tier,
            model,
            cost,
            tokens,
            cache_hit,
            cache_type,
            duration_ms,
            prompt_cache_creation_tokens=prompt_cache_creation_tokens,
            prompt_cache_read_tokens=prompt_cache_read_tokens,
        )

    def _emit_call_telemetry(
        self,
        step_name: str,
        task_type: str,
        tier: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: str | None = None,
        fallback_used: bool = False,
    ) -> None:
        """Emit call record -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            self._ctx.telemetry.emit_call_record(
                step_name=step_name,
                task_type=task_type,
                tier=tier,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                fallback_used=fallback_used,
            )
            return
        super()._emit_call_telemetry(
            step_name,
            task_type,
            tier,
            model_id,
            input_tokens,
            output_tokens,
            cost,
            latency_ms,
            success,
            error_message,
            fallback_used,
        )

    def _emit_workflow_telemetry(
        self,
        result: Any,
        *,
        started_at: Any = None,
        completed_at: Any = None,
    ) -> None:
        """Emit workflow record -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            model_fn = self.get_model_for_tier if hasattr(self, "get_model_for_tier") else None
            self._ctx.telemetry.emit_workflow_record(
                result, model_fn, started_at=started_at, completed_at=completed_at
            )
            return
        super()._emit_workflow_telemetry(result, started_at=started_at, completed_at=completed_at)

    def _generate_run_id(self) -> str:
        """Generate run ID -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            run_id = self._ctx.telemetry.generate_run_id()
            self._run_id = run_id
            return run_id
        return super()._generate_run_id()

    # --- Prompt proxies (PromptMixin -> PromptService) ---

    def _is_xml_enabled(self) -> bool:
        """Check if XML prompts are enabled -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.xml_enabled
        return super()._is_xml_enabled()

    def _build_cached_system_prompt(
        self,
        role: str,
        guidelines: list[str] | None = None,
        documentation: str | None = None,
        examples: list[dict[str, str]] | None = None,
    ) -> str:
        """Build cached system prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.build_cached_system_prompt(
                role,
                guidelines,
                documentation,
                examples,
            )
        return super()._build_cached_system_prompt(
            role,
            guidelines,
            documentation,
            examples,
        )

    def _render_xml_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
        examples: list[dict[str, str]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Render XML prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.render_xml(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
                extra,
            )
        return super()._render_xml_prompt(
            role,
            goal,
            instructions,
            constraints,
            input_type,
            input_payload,
            examples,
            extra,
        )

    def _render_plain_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
    ) -> str:
        """Render plain prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.render_plain(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
            )
        return super()._render_plain_prompt(
            role,
            goal,
            instructions,
            constraints,
            input_type,
            input_payload,
        )

    # --- Parsing proxies (ResponseParsingMixin -> ParsingService) ---

    def _parse_xml_response(self, response: str) -> dict[str, Any]:
        """Parse XML response -- delegates to ParsingService when ctx is provided."""
        if self._ctx and self._ctx.parsing:
            return self._ctx.parsing.parse_xml_response(response)
        return super()._parse_xml_response(response)

    def _extract_findings_from_response(
        self,
        response: str,
        files_changed: list[str],
        code_context: str = "",
    ) -> list[dict[str, Any]]:
        """Extract findings -- delegates to ParsingService when ctx is provided."""
        if self._ctx and self._ctx.parsing:
            return self._ctx.parsing.extract_findings(
                response,
                files_changed,
                code_context,
            )
        return super()._extract_findings_from_response(
            response,
            files_changed,
            code_context,
        )

    # --- Tier routing proxies (TierRoutingMixin -> TierService) ---

    def _get_tier_with_routing(
        self,
        stage_name: str,
        input_data: dict[str, Any] | None = None,
        budget_remaining: float = 100.0,
    ) -> Any:
        """Get tier with routing -- delegates to TierService when ctx is provided."""
        if self._ctx and self._ctx.tier:
            return self._ctx.tier.get_tier(stage_name, input_data, budget_remaining)
        return super()._get_tier_with_routing(
            stage_name,
            input_data,
            budget_remaining,
        )

    # --- Coordination proxies (CoordinationMixin -> CoordinationService) ---

    def send_signal(
        self,
        signal_type: str,
        target_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Send signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.send_signal(
                signal_type,
                target_agent,
                payload,
                ttl_seconds,
            )
        return super().send_signal(
            signal_type,
            target_agent,
            payload,
            ttl_seconds,
        )

    def wait_for_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> Any:
        """Wait for signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.wait_for_signal(
                signal_type,
                source_agent,
                timeout,
                poll_interval,
            )
        return super().wait_for_signal(
            signal_type,
            source_agent,
            timeout,
            poll_interval,
        )

    def check_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        consume: bool = True,
    ) -> Any:
        """Check signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.check_signal(
                signal_type,
                source_agent,
                consume,
            )
        return super().check_signal(
            signal_type,
            source_agent,
            consume,
        )
