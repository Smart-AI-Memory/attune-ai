"""Embedding providers for vector generation.

Supports multiple backends:
1. Local: Simple TF-IDF based embeddings (no external dependencies)
2. Anthropic: Uses Claude for semantic analysis (via message API)
3. Sentence Transformers: Local neural embeddings (requires torch)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class TFIDFEmbeddingProvider(EmbeddingProvider):
    """Simple TF-IDF based embeddings (no external dependencies).

    Uses term frequency-inverse document frequency to create sparse
    embeddings that are then normalized to fixed dimension.
    """

    def __init__(self, dimension: int = 256, vocabulary_size: int = 10000):
        """Initialize TF-IDF provider.

        Args:
            dimension: Output embedding dimension
            vocabulary_size: Maximum vocabulary size
        """
        self._dimension = dimension
        self._vocabulary_size = vocabulary_size
        self._vocabulary: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._document_count = 0

    @property
    def dimension(self) -> int:
        return self._dimension

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        text = text.lower()
        tokens = re.findall(r"\b[a-z][a-z0-9_]*\b", text)
        return tokens

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """Compute term frequency."""
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        total = len(tokens) or 1
        return {k: v / total for k, v in tf.items()}

    def _hash_to_bucket(self, term: str) -> int:
        """Hash term to fixed bucket for dimensionality reduction."""
        h = int(hashlib.md5(term.encode(), usedforsecurity=False).hexdigest(), 16)
        return h % self._dimension

    def embed(self, text: str) -> list[float]:
        """Generate TF-IDF based embedding.

        Uses feature hashing to project sparse TF-IDF vector
        to fixed dimension.
        """
        tokens = self._tokenize(text)
        tf = self._compute_tf(tokens)

        vector = [0.0] * self._dimension

        for term, freq in tf.items():
            bucket = self._hash_to_bucket(term)
            sign = 1 if int(hashlib.sha256(term.encode()).hexdigest(), 16) % 2 == 0 else -1
            idf = self._idf.get(term, 1.0)
            vector[bucket] += sign * freq * idf

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]

    def fit(self, documents: list[str]):
        """Fit IDF weights on document corpus.

        Args:
            documents: List of documents to compute IDF from
        """
        self._document_count = len(documents)
        doc_freq: dict[str, int] = {}

        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        for term, df in doc_freq.items():
            self._idf[term] = math.log((self._document_count + 1) / (df + 1)) + 1


class AnthropicEmbeddingProvider(EmbeddingProvider):
    """Use Claude for semantic embeddings via similarity scoring.

    Note: Anthropic doesn't have a dedicated embedding API, so we use
    Claude to generate semantic feature vectors based on predefined
    aspects relevant to workflow generation.
    """

    ASPECTS = [
        "code review and quality",
        "security and vulnerability",
        "testing and coverage",
        "documentation and comments",
        "performance and optimization",
        "refactoring and cleanup",
        "deployment and CI/CD",
        "debugging and troubleshooting",
        "architecture and design",
        "data processing and ETL",
    ]

    def __init__(self, api_key: str | None = None, dimension: int = 64):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            dimension: Number of semantic aspects to score
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._dimension = min(dimension, len(self.ASPECTS))
        self._client = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None and self.api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate semantic embedding by scoring relevance to aspects."""
        client = self._get_client()
        if not client:
            fallback = TFIDFEmbeddingProvider(dimension=self._dimension)
            return fallback.embed(text)

        aspects = self.ASPECTS[: self._dimension]
        prompt = f"""Rate how relevant this goal is to each aspect on a scale of 0.0 to 1.0.

Goal: "{text}"

Aspects to rate:
{chr(10).join(f"{i + 1}. {aspect}" for i, aspect in enumerate(aspects))}

Respond with ONLY a JSON array of numbers, one per aspect, in order.
Example: [0.8, 0.2, 0.5, ...]"""

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text if response.content else "[]"

            scores = json.loads(content.strip())
            if isinstance(scores, list) and len(scores) >= self._dimension:
                return [float(s) for s in scores[: self._dimension]]

        except Exception as e:
            logger.warning(f"Anthropic embedding failed: {e}")

        fallback = TFIDFEmbeddingProvider(dimension=self._dimension)
        return fallback.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]


class SentenceTransformerProvider(EmbeddingProvider):
    """Use sentence-transformers for local neural embeddings.

    Requires: pip install sentence-transformers
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize sentence transformer.

        Args:
            model_name: HuggingFace model name
        """
        self.model_name = model_name
        self._model = None
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension or 384

    def _load_model(self):
        """Lazy-load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.warning("sentence-transformers not installed")
                self._dimension = 384

    def embed(self, text: str) -> list[float]:
        """Generate embedding using sentence transformer."""
        self._load_model()
        if self._model is None:
            fallback = TFIDFEmbeddingProvider(dimension=384)
            return fallback.embed(text)

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        self._load_model()
        if self._model is None:
            fallback = TFIDFEmbeddingProvider(dimension=384)
            return [fallback.embed(t) for t in texts]

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]
