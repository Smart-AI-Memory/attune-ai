"""Condition types and evaluator for conditional execution strategies.

This module implements the conditional grammar (Pattern 7) for agent workflows:
- JSON predicates: MongoDB-style fast, deterministic conditions
- Natural language: LLM-interpreted semantic conditions
- Composite: Logical combinations (AND/OR/NOT)

Security:
    - No eval() or exec() - all operators are whitelisted
    - JSON predicates use safe comparison operators
    - Natural language uses LLM API (no code execution)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agent_templates import AgentTemplate

logger = logging.getLogger(__name__)


# =============================================================================
# Conditional Grammar Types (Pattern 7)
# =============================================================================


class ConditionType(Enum):
    """Type of condition for gate evaluation.

    Attributes:
        JSON_PREDICATE: MongoDB-style JSON predicate ({"field": {"$op": value}})
        NATURAL_LANGUAGE: LLM-interpreted natural language condition
        COMPOSITE: Logical combination of conditions (AND/OR)

    """

    JSON_PREDICATE = "json"
    NATURAL_LANGUAGE = "natural"
    COMPOSITE = "composite"


@dataclass
class Condition:
    """A conditional gate for branching in agent workflows.

    Supports hybrid syntax: JSON predicates for simple conditions,
    natural language for complex semantic conditions.

    Attributes:
        predicate: JSON predicate dict or natural language string
        condition_type: How to evaluate the condition
        description: Human-readable description of the condition
        source_field: Which field(s) in context to evaluate

    JSON Predicate Operators:
        $eq: Equal to value
        $ne: Not equal to value
        $gt: Greater than value
        $gte: Greater than or equal to value
        $lt: Less than value
        $lte: Less than or equal to value
        $in: Value is in list
        $nin: Value is not in list
        $exists: Field exists (or not)
        $regex: Matches regex pattern

    Example (JSON):
        >>> # Low confidence triggers expert review
        >>> cond = Condition(
        ...     predicate={"confidence": {"$lt": 0.8}},
        ...     description="Confidence is below threshold"
        ... )

    Example (Natural Language):
        >>> # LLM interprets complex semantic condition
        >>> cond = Condition(
        ...     predicate="The security audit found critical vulnerabilities",
        ...     condition_type=ConditionType.NATURAL_LANGUAGE,
        ...     description="Security issues detected"
        ... )

    """

    predicate: dict[str, Any] | str
    condition_type: ConditionType = ConditionType.JSON_PREDICATE
    description: str = ""
    source_field: str = ""  # Empty means evaluate whole context

    def __post_init__(self):
        """Validate condition and auto-detect type."""
        if isinstance(self.predicate, str):
            # Auto-detect: if it looks like prose, it's natural language
            if " " in self.predicate and not self.predicate.startswith("{"):
                object.__setattr__(self, "condition_type", ConditionType.NATURAL_LANGUAGE)
        elif isinstance(self.predicate, dict):
            # Validate JSON predicate structure
            self._validate_predicate(self.predicate)
        else:
            raise ValueError(f"predicate must be dict or str, got {type(self.predicate)}")

    def _validate_predicate(self, predicate: dict[str, Any]) -> None:
        """Validate JSON predicate structure (no code execution).

        Args:
            predicate: The predicate dict to validate

        Raises:
            ValueError: If predicate contains invalid operators

        """
        valid_operators = {
            "$eq",
            "$ne",
            "$gt",
            "$gte",
            "$lt",
            "$lte",
            "$in",
            "$nin",
            "$exists",
            "$regex",
            "$and",
            "$or",
            "$not",
        }

        for key, value in predicate.items():
            if key.startswith("$"):
                if key not in valid_operators:
                    raise ValueError(f"Invalid operator: {key}")
            if isinstance(value, dict):
                self._validate_predicate(value)


@dataclass
class Branch:
    """A branch in conditional execution.

    Attributes:
        agents: Agents to execute in this branch
        strategy: Strategy to use for executing agents (default: sequential)
        label: Human-readable branch label

    """

    agents: list[AgentTemplate]
    strategy: str = "sequential"
    label: str = ""


# =============================================================================
# Condition Evaluator
# =============================================================================


class ConditionEvaluator:
    """Evaluates conditions against execution context.

    Supports both JSON predicates (fast, deterministic) and
    natural language conditions (LLM-interpreted, semantic).

    Security:
        - No eval() or exec() - all operators are whitelisted
        - JSON predicates use safe comparison operators
        - Natural language uses LLM API (no code execution)
    """

    # Mapping of JSON operators to Python comparison functions
    OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
        "$eq": operator.eq,
        "$ne": operator.ne,
        "$gt": operator.gt,
        "$gte": operator.ge,
        "$lt": operator.lt,
        "$lte": operator.le,
        "$in": lambda val, lst: val in lst,
        "$nin": lambda val, lst: val not in lst,
        "$exists": lambda val, exists: (val is not None) == exists,
        "$regex": lambda val, pattern: bool(re.match(pattern, str(val))) if val else False,
    }

    def evaluate(self, condition: Condition, context: dict[str, Any]) -> bool:
        """Evaluate a condition against the current context.

        Args:
            condition: The condition to evaluate
            context: Execution context with agent results

        Returns:
            True if condition is met, False otherwise

        Example:
            >>> evaluator = ConditionEvaluator()
            >>> context = {"confidence": 0.6, "errors": 0}
            >>> cond = Condition(predicate={"confidence": {"$lt": 0.8}})
            >>> evaluator.evaluate(cond, context)
            True

        """
        if condition.condition_type == ConditionType.JSON_PREDICATE:
            return self._evaluate_json(condition.predicate, context)
        if condition.condition_type == ConditionType.NATURAL_LANGUAGE:
            return self._evaluate_natural_language(condition.predicate, context)
        if condition.condition_type == ConditionType.COMPOSITE:
            return self._evaluate_composite(condition.predicate, context)
        raise ValueError(f"Unknown condition type: {condition.condition_type}")

    def _evaluate_json(self, predicate: dict[str, Any], context: dict[str, Any]) -> bool:
        """Evaluate JSON predicate against context.

        Args:
            predicate: MongoDB-style predicate dict
            context: Context to evaluate against

        Returns:
            True if all conditions match

        """
        for field_name, condition_spec in predicate.items():
            # Handle logical operators
            if field_name == "$and":
                return all(self._evaluate_json(sub, context) for sub in condition_spec)
            if field_name == "$or":
                return any(self._evaluate_json(sub, context) for sub in condition_spec)
            if field_name == "$not":
                return not self._evaluate_json(condition_spec, context)

            # Get value from context (supports nested paths like "result.confidence")
            value = self._get_nested_value(context, field_name)

            # Evaluate condition
            if isinstance(condition_spec, dict):
                for op, target in condition_spec.items():
                    if op not in self.OPERATORS:
                        raise ValueError(f"Unknown operator: {op}")
                    if not self.OPERATORS[op](value, target):
                        return False
            # Direct equality check
            elif value != condition_spec:
                return False

        return True

    def _get_nested_value(self, context: dict[str, Any], path: str) -> Any:
        """Get nested value from context using dot notation.

        Args:
            context: Context dict
            path: Dot-separated path (e.g., "result.confidence")

        Returns:
            Value at path or None if not found

        """
        parts = path.split(".")
        current = context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def _evaluate_natural_language(self, condition_text: str, context: dict[str, Any]) -> bool:
        """Evaluate natural language condition using LLM.

        Args:
            condition_text: Natural language condition
            context: Context to evaluate against

        Returns:
            True if LLM determines condition is met

        Note:
            Falls back to keyword matching if LLM unavailable.

        """
        logger.info(f"Evaluating natural language condition: {condition_text}")

        # Try LLM evaluation first
        try:
            return self._evaluate_with_llm(condition_text, context)
        except Exception as e:
            # INTENTIONAL: Fallback to keyword matching if any LLM error
            logger.warning(f"LLM evaluation failed, using keyword fallback: {e}")
            return self._keyword_fallback(condition_text, context)

    def _evaluate_with_llm(self, condition_text: str, context: dict[str, Any]) -> bool:
        """Use LLM to evaluate natural language condition.

        Args:
            condition_text: The condition in natural language
            context: Execution context

        Returns:
            LLM's determination (True/False)

        """
        # Import LLM client lazily to avoid circular imports
        try:
            from ..llm import get_cheap_tier_client
        except ImportError:
            logger.warning("LLM client not available for natural language conditions")
            raise

        # Prepare context summary for LLM
        context_summary = json.dumps(context, indent=2, default=str)[:2000]

        prompt = f"""Evaluate whether the following condition is TRUE or FALSE based on the context.

Condition: {condition_text}

Context:
{context_summary}

Respond with ONLY "TRUE" or "FALSE" (no explanation)."""

        client = get_cheap_tier_client()
        response = client.complete(prompt, max_tokens=10)

        result = response.strip().upper()
        return result == "TRUE"

    def _keyword_fallback(self, condition_text: str, context: dict[str, Any]) -> bool:
        """Fallback keyword-based evaluation for natural language.

        Args:
            condition_text: The condition text
            context: Execution context

        Returns:
            True if keywords suggest condition is likely met

        """
        # Simple keyword matching as fallback
        condition_lower = condition_text.lower()
        context_str = json.dumps(context, default=str).lower()

        # Check for negation
        is_negated = any(neg in condition_lower for neg in ["not ", "no ", "without "])

        # Extract key terms
        terms = re.findall(r"\b\w{4,}\b", condition_lower)
        terms = [t for t in terms if t not in {"the", "that", "this", "with", "from"}]

        # Count matching terms
        matches = sum(1 for term in terms if term in context_str)
        match_ratio = matches / len(terms) if terms else 0

        result = match_ratio > 0.5
        return not result if is_negated else result

    def _evaluate_composite(self, predicate: dict[str, Any], context: dict[str, Any]) -> bool:
        """Evaluate composite condition (AND/OR of other conditions).

        Args:
            predicate: Composite predicate with $and/$or
            context: Context to evaluate against

        Returns:
            Result of logical combination

        """
        return self._evaluate_json(predicate, context)
