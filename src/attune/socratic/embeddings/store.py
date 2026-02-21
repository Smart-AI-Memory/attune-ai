"""In-memory vector store with similarity search.

Supports persistence to JSON files.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .models import EmbeddedGoal, SimilarityResult
from .providers import EmbeddingProvider, TFIDFEmbeddingProvider

logger = logging.getLogger(__name__)


class VectorStore:
    """In-memory vector store with similarity search.

    Supports persistence to JSON files.
    """

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        storage_path: Path | str | None = None,
    ):
        """Initialize vector store.

        Args:
            provider: Embedding provider to use
            storage_path: Path to persist vectors
        """
        self.provider = provider or TFIDFEmbeddingProvider()
        self.storage_path = Path(storage_path) if storage_path else None
        self._goals: dict[str, EmbeddedGoal] = {}

        # Load from storage if exists
        if self.storage_path and self.storage_path.exists():
            self._load()

    def add(
        self,
        goal_text: str,
        goal_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        domains: list[str] | None = None,
        workflow_id: str | None = None,
        success_score: float = 0.0,
    ) -> EmbeddedGoal:
        """Add a goal to the store.

        Args:
            goal_text: The goal text
            goal_id: Optional ID (generated if not provided)
            metadata: Optional metadata
            domains: Optional domain tags
            workflow_id: Optional linked workflow ID
            success_score: Success score (0.0-1.0)

        Returns:
            The embedded goal
        """
        if goal_id is None:
            goal_id = hashlib.sha256(goal_text.encode()).hexdigest()[:12]

        embedding = self.provider.embed(goal_text)

        goal = EmbeddedGoal(
            goal_id=goal_id,
            goal_text=goal_text,
            embedding=embedding,
            metadata=metadata or {},
            domains=domains or [],
            workflow_id=workflow_id,
            success_score=success_score,
        )

        self._goals[goal_id] = goal

        if self.storage_path:
            self._save()

        return goal

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
        domain_filter: str | None = None,
    ) -> list[SimilarityResult]:
        """Search for similar goals.

        Args:
            query: Query text
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            domain_filter: Optional domain to filter by

        Returns:
            List of similarity results sorted by relevance
        """
        if not self._goals:
            return []

        query_embedding = self.provider.embed(query)

        results: list[tuple[float, EmbeddedGoal]] = []

        for goal in self._goals.values():
            if domain_filter and domain_filter not in goal.domains:
                continue

            similarity = self._cosine_similarity(query_embedding, goal.embedding)
            if similarity >= min_similarity:
                results.append((similarity, goal))

        results.sort(key=lambda x: x[0], reverse=True)

        return [
            SimilarityResult(goal=goal, similarity=sim, rank=i + 1)
            for i, (sim, goal) in enumerate(results[:top_k])
        ]

    def search_by_embedding(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SimilarityResult]:
        """Search using pre-computed embedding.

        Args:
            embedding: Pre-computed embedding vector
            top_k: Number of results
            min_similarity: Minimum threshold

        Returns:
            List of similarity results
        """
        results: list[tuple[float, EmbeddedGoal]] = []

        for goal in self._goals.values():
            similarity = self._cosine_similarity(embedding, goal.embedding)
            if similarity >= min_similarity:
                results.append((similarity, goal))

        results.sort(key=lambda x: x[0], reverse=True)

        return [
            SimilarityResult(goal=goal, similarity=sim, rank=i + 1)
            for i, (sim, goal) in enumerate(results[:top_k])
        ]

    def get(self, goal_id: str) -> EmbeddedGoal | None:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def remove(self, goal_id: str) -> bool:
        """Remove a goal by ID."""
        if goal_id in self._goals:
            del self._goals[goal_id]
            if self.storage_path:
                self._save()
            return True
        return False

    def update_success_score(self, goal_id: str, score: float):
        """Update the success score for a goal."""
        if goal_id in self._goals:
            self._goals[goal_id].success_score = score
            if self.storage_path:
                self._save()

    def __len__(self) -> int:
        return len(self._goals)

    def __iter__(self) -> Iterator[EmbeddedGoal]:
        return iter(self._goals.values())

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def _save(self):
        """Save to storage."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "goals": [g.to_dict() for g in self._goals.values()],
        }

        validated_path = _validate_file_path(str(self.storage_path))
        with validated_path.open("w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with self.storage_path.open("r") as f:
                data = json.load(f)

            for goal_data in data.get("goals", []):
                goal = EmbeddedGoal.from_dict(goal_data)
                self._goals[goal.goal_id] = goal

        except Exception as e:
            logger.warning(f"Failed to load vector store: {e}")
