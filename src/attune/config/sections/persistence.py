"""Data persistence configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class PersistenceConfig:
    """Data persistence and memory configuration.

    Controls memory features, caching, pattern storage, and
    data import/export settings.

    Attributes:
        memory_enabled: Enable memory/learning features.
        memory_backend: Storage backend for memory data.
        memory_path: Path to memory storage directory.
        cache_enabled: Enable result caching.
        cache_path: Path to cache directory.
        cache_ttl_hours: Cache time-to-live in hours.
        patterns_file: Path to learned patterns file.
        session_history: Store session history.
        max_history_entries: Maximum history entries to retain.
        auto_save: Automatically save changes.
        save_interval_seconds: Auto-save interval in seconds.
        backup_enabled: Enable configuration backups.
        backup_count: Number of backups to retain.
        export_format: Default format for exports.
        import_merge_strategy: Strategy for importing configs.
        encryption_enabled: Enable encryption for sensitive data.
        encryption_key_env: Environment variable for encryption key.
        compress_exports: Compress exported data.
        index_patterns: Build indexes for pattern search.
        pattern_learning: Enable learning from sessions.

    """

    memory_enabled: bool = True
    memory_backend: Literal["json", "sqlite", "redis"] = "json"
    memory_path: str = "~/.attune/memory"
    cache_enabled: bool = True
    cache_path: str = "~/.attune/cache"
    cache_ttl_hours: int = 24
    patterns_file: str = "~/.attune/patterns.json"
    session_history: bool = True
    max_history_entries: int = 1000
    auto_save: bool = True
    save_interval_seconds: int = 60
    backup_enabled: bool = True
    backup_count: int = 5
    export_format: Literal["json", "yaml"] = "json"
    import_merge_strategy: Literal["overwrite", "merge"] = "merge"
    encryption_enabled: bool = False
    encryption_key_env: str = "ATTUNE_ENCRYPTION_KEY"
    compress_exports: bool = False
    index_patterns: bool = True
    pattern_learning: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "memory_enabled": self.memory_enabled,
            "memory_backend": self.memory_backend,
            "memory_path": self.memory_path,
            "cache_enabled": self.cache_enabled,
            "cache_path": self.cache_path,
            "cache_ttl_hours": self.cache_ttl_hours,
            "patterns_file": self.patterns_file,
            "session_history": self.session_history,
            "max_history_entries": self.max_history_entries,
            "auto_save": self.auto_save,
            "save_interval_seconds": self.save_interval_seconds,
            "backup_enabled": self.backup_enabled,
            "backup_count": self.backup_count,
            "export_format": self.export_format,
            "import_merge_strategy": self.import_merge_strategy,
            "encryption_enabled": self.encryption_enabled,
            "encryption_key_env": self.encryption_key_env,
            "compress_exports": self.compress_exports,
            "index_patterns": self.index_patterns,
            "pattern_learning": self.pattern_learning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistenceConfig":
        """Create from dictionary."""
        return cls(
            memory_enabled=data.get("memory_enabled", True),
            memory_backend=data.get("memory_backend", "json"),
            memory_path=data.get("memory_path", "~/.attune/memory"),
            cache_enabled=data.get("cache_enabled", True),
            cache_path=data.get("cache_path", "~/.attune/cache"),
            cache_ttl_hours=data.get("cache_ttl_hours", 24),
            patterns_file=data.get("patterns_file", "~/.attune/patterns.json"),
            session_history=data.get("session_history", True),
            max_history_entries=data.get("max_history_entries", 1000),
            auto_save=data.get("auto_save", True),
            save_interval_seconds=data.get("save_interval_seconds", 60),
            backup_enabled=data.get("backup_enabled", True),
            backup_count=data.get("backup_count", 5),
            export_format=data.get("export_format", "json"),
            import_merge_strategy=data.get("import_merge_strategy", "merge"),
            encryption_enabled=data.get("encryption_enabled", False),
            encryption_key_env=data.get("encryption_key_env", "ATTUNE_ENCRYPTION_KEY"),
            compress_exports=data.get("compress_exports", False),
            index_patterns=data.get("index_patterns", True),
            pattern_learning=data.get("pattern_learning", True),
        )
