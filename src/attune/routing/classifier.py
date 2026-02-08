"""LLM-based Request Classifier

Uses a cheap model (Haiku) to classify developer requests
and route them to appropriate workflow(s).

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from .workflow_registry import WorkflowRegistry


@dataclass
class ClassificationResult:
    """Result of classifying a developer request."""

    primary_workflow: str
    secondary_workflows: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    suggested_chain: list[str] = field(default_factory=list)
    extracted_context: dict[str, Any] = field(default_factory=dict)


class HaikuClassifier:
    """Uses Claude Haiku to classify requests to workflows.

    Why Haiku:
    - Cheapest tier model
    - Fast response times
    - Sufficient for classification tasks
    - Cost-effective for high-volume routing
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the classifier.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None
        self._registry = WorkflowRegistry()

    def _get_client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None and self._api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                pass
        return self._client

    async def classify(
        self,
        request: str,
        context: dict[str, Any] | None = None,
        available_workflows: dict[str, str] | None = None,
    ) -> ClassificationResult:
        """Classify a developer request and determine which workflow(s) to invoke.

        Args:
            request: The developer's natural language request
            context: Optional context (current file, project type, etc.)
            available_workflows: Override for available workflow descriptions

        Returns:
            ClassificationResult with primary and secondary workflow recommendations

        """
        if available_workflows is None:
            available_workflows = self._registry.get_descriptions_for_classification()

        # Build classification prompt
        workflow_list = "\n".join(f"- {name}: {desc}" for name, desc in available_workflows.items())

        context_str = ""
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"

        system_prompt = """You are a request router that classifies requests to the appropriate workflow.

Analyze the request and determine:
1. The PRIMARY workflow that best handles this request
2. Any SECONDARY workflows that could provide additional value
3. Your confidence level (0.0 - 1.0)
4. Brief reasoning for your choice

Respond in JSON format:
{
    "primary_workflow": "workflow-name",
    "secondary_workflows": ["workflow-name-2"],
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "extracted_context": {
        "file_mentioned": "auth.py",
        "issue_type": "performance"
    }
}"""

        user_prompt = f"""Available workflows:
{workflow_list}

Developer request: "{request}"{context_str}

Classify this request."""

        # Try LLM classification
        client = self._get_client()
        if client:
            try:
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                content = response.content[0].text if response.content else "{}"

                # Parse JSON response
                try:
                    # Extract JSON from response (handle markdown code blocks)
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]

                    data = json.loads(content.strip())
                    return ClassificationResult(
                        primary_workflow=data.get("primary_workflow", "code-review"),
                        secondary_workflows=data.get("secondary_workflows", []),
                        confidence=data.get("confidence", 0.5),
                        reasoning=data.get("reasoning", ""),
                        extracted_context=data.get("extracted_context", {}),
                    )
                except json.JSONDecodeError:
                    pass

            except Exception as e:
                print(f"LLM classification error: {e}")

        # Fallback to keyword-based classification
        return self._keyword_classify(request, available_workflows)

    def _keyword_classify(
        self,
        request: str,
        available_workflows: dict[str, str],
    ) -> ClassificationResult:
        """Fallback keyword-based classification."""
        request_lower = request.lower()

        # Score each workflow based on keyword matches
        scores: dict[str, float] = {}

        for workflow in self._registry.list_all():
            score = 0.0
            for keyword in workflow.keywords:
                if keyword in request_lower:
                    score += 1.0
                    # Exact word match bonus
                    if f" {keyword} " in f" {request_lower} ":
                        score += 0.5

            if score > 0:
                scores[workflow.name] = score

        if not scores:
            # Default to code-review
            return ClassificationResult(
                primary_workflow="code-review",
                confidence=0.3,
                reasoning="No keyword matches, defaulting to code-review",
            )

        # Sort by score
        sorted_workflows = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_workflows[0][0]
        primary_score = sorted_workflows[0][1]

        # Get secondary if significantly different
        secondary = []
        if len(sorted_workflows) > 1:
            for name, score in sorted_workflows[1:3]:
                if score >= primary_score * 0.5:
                    secondary.append(name)

        # Normalize confidence
        max_possible = max(len(w.keywords) for w in self._registry.list_all())
        confidence = min(primary_score / max_possible, 1.0)

        return ClassificationResult(
            primary_workflow=primary,
            secondary_workflows=secondary,
            confidence=confidence,
            reasoning=f"Keyword match score: {primary_score}",
        )

    def classify_sync(
        self,
        request: str,
        context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """Synchronous classification using keyword matching only."""
        return self._keyword_classify(
            request,
            self._registry.get_descriptions_for_classification(),
        )
