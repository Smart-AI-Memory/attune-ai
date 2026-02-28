"""Semantic goal matcher for workflow suggestion.

High-level API that integrates with the Socratic workflow builder
to find similar past goals and their successful configurations.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .providers import (
    AnthropicEmbeddingProvider,
    SentenceTransformerProvider,
    TFIDFEmbeddingProvider,
)
from .store import VectorStore


class SemanticGoalMatcher:
    """High-level API for semantic goal matching.

    Integrates with the Socratic workflow builder to find similar
    past goals and their successful workflow configurations.
    """

    def __init__(
        self,
        provider: str = "tfidf",
        storage_path: Path | str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the matcher.

        Args:
            provider: Embedding provider ("tfidf", "anthropic", "sentence-transformer")
            storage_path: Path to persist vectors
            api_key: API key for cloud providers

        """
        if storage_path is None:
            storage_path = Path.home() / ".attune" / "socratic" / "embeddings.json"

        if provider == "anthropic":
            embedding_provider = AnthropicEmbeddingProvider(api_key=api_key)
        elif provider == "sentence-transformer":
            embedding_provider = SentenceTransformerProvider()
        else:
            embedding_provider = TFIDFEmbeddingProvider()

        self.store = VectorStore(
            provider=embedding_provider,
            storage_path=storage_path,
        )

    def index_goal(
        self,
        goal_text: str,
        workflow_id: str | None = None,
        domains: list[str] | None = None,
        success_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Index a goal for future similarity search.

        Args:
            goal_text: The goal text
            workflow_id: ID of the generated workflow
            domains: Detected domains
            success_score: Success score from execution
            metadata: Additional metadata

        Returns:
            Goal ID

        """
        goal = self.store.add(
            goal_text=goal_text,
            domains=domains,
            workflow_id=workflow_id,
            success_score=success_score,
            metadata=metadata or {},
        )
        return goal.goal_id

    def find_similar(
        self,
        goal_text: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        min_success_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Find similar past goals.

        Args:
            goal_text: The goal to search for
            top_k: Number of results
            min_similarity: Minimum similarity threshold
            min_success_score: Minimum success score filter

        Returns:
            List of similar goals with their workflows

        """
        results = self.store.search(
            query=goal_text,
            top_k=top_k * 2,
            min_similarity=min_similarity,
        )

        formatted = []
        for result in results:
            if result.goal.success_score >= min_success_score:
                formatted.append(
                    {
                        "goal_id": result.goal.goal_id,
                        "goal_text": result.goal.goal_text,
                        "similarity": round(result.similarity, 3),
                        "workflow_id": result.goal.workflow_id,
                        "domains": result.goal.domains,
                        "success_score": result.goal.success_score,
                        "metadata": result.goal.metadata,
                    },
                )

            if len(formatted) >= top_k:
                break

        return formatted

    def suggest_workflow(
        self,
        goal_text: str,
        min_similarity: float = 0.5,
        min_success_score: float = 0.7,
    ) -> dict[str, Any] | None:
        """Suggest a workflow based on similar successful goals.

        Args:
            goal_text: The goal to find workflow for
            min_similarity: Minimum similarity required
            min_success_score: Minimum success score required

        Returns:
            Best matching workflow suggestion or None

        """
        similar = self.find_similar(
            goal_text=goal_text,
            top_k=1,
            min_similarity=min_similarity,
            min_success_score=min_success_score,
        )

        if similar:
            return similar[0]
        return None

    def update_success(self, goal_id: str, success_score: float):
        """Update success score after workflow execution.

        Args:
            goal_id: Goal ID to update
            success_score: New success score (0.0-1.0)

        """
        self.store.update_success_score(goal_id, success_score)

    @property
    def indexed_count(self) -> int:
        """Number of indexed goals."""
        return len(self.store)
