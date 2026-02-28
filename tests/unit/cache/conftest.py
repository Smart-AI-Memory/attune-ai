"""Pytest configuration for cache module tests.

Provides shared fixtures for cache testing with proper isolation.
"""

import pytest


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create isolated cache storage directory.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Returns:
        Path to isolated cache storage

    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def sample_cache_entry():
    """Sample cache entry for testing.

    Returns:
        Dict with test cache entry

    """
    return {
        "key": "test_query_hash",
        "value": "cached response",
        "ttl": 3600,
        "created_at": 1705849200.0,
        "hits": 0,
    }


@pytest.fixture
def mock_embeddings():
    """Mock embeddings for semantic cache testing.

    Returns:
        List of float values representing embeddings (384-dimensional)

    Security Note:
        Uses `random` (not `secrets`) intentionally for reproducible test data.
        This is NOT used for cryptographic operations or security tokens.
        For security-critical random generation, use `secrets` module.

    """
    import random

    # Security Note: Using random (not secrets) for deterministic test fixtures
    # Fixed seed ensures reproducible test results - NOT for cryptographic use
    random.seed(42)
    return [random.random() for _ in range(384)]
