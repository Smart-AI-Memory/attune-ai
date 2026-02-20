"""Vector Embeddings for Semantic Goal Matching

Provides semantic similarity search for finding similar past goals and their
successful workflow configurations.

Supports multiple embedding backends:
1. Local: Simple TF-IDF based embeddings (no external dependencies)
2. OpenAI: OpenAI's text-embedding-3-small
3. Anthropic: Uses Claude for semantic analysis (via message API)
4. Sentence Transformers: Local neural embeddings (requires torch)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .matcher import SemanticGoalMatcher
from .models import EmbeddedGoal, SimilarityResult
from .providers import (
    AnthropicEmbeddingProvider,
    EmbeddingProvider,
    SentenceTransformerProvider,
    TFIDFEmbeddingProvider,
)
from .store import VectorStore

__all__ = [
    "AnthropicEmbeddingProvider",
    "EmbeddedGoal",
    "EmbeddingProvider",
    "SemanticGoalMatcher",
    "SentenceTransformerProvider",
    "SimilarityResult",
    "TFIDFEmbeddingProvider",
    "VectorStore",
]
