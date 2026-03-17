"""Collaboration State Persistence.

Provides save/load for CollaborationState across sessions.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from datetime import datetime
from pathlib import Path

from attune.security.path_validation import _validate_file_path

from .core import CollaborationState


class StateManager:
    """Persist collaboration state across sessions

    Enables:
    - Long-term trust tracking
    - Historical analytics
    - User personalization
    """

    def __init__(self, storage_path: str = "./attune_state"):
        """Initialize StateManager with a storage directory.

        Args:
            storage_path: Directory for persisting user state JSON files.

        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True, parents=True)

    def save_state(self, user_id: str, state: CollaborationState):
        """Save user's collaboration state to JSON

        Args:
            user_id: User identifier
            state: CollaborationState instance

        Example:
            >>> manager = StateManager()
            >>> manager.save_state("user123", empathy.collaboration_state)

        """
        filepath = self.storage_path / f"{user_id}.json"

        data = {
            "user_id": user_id,
            "trust_level": state.trust_level,
            "total_interactions": state.total_interactions,
            "successful_interventions": state.successful_interventions,
            "failed_interventions": state.failed_interventions,
            "session_start": state.session_start.isoformat(),
            "trust_trajectory": state.trust_trajectory,
            "shared_context": state.shared_context,
            "saved_at": datetime.now().isoformat(),
        }

        validated_path = _validate_file_path(str(filepath))
        with open(validated_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_state(self, user_id: str) -> CollaborationState | None:
        """Load user's previous state

        Args:
            user_id: User identifier

        Returns:
            CollaborationState if found, None otherwise

        Example:
            >>> manager = StateManager()
            >>> state = manager.load_state("user123")
            >>> if state:
            ...     empathy = EmpathyOS(user_id="user123", target_level=4)
            ...     empathy.collaboration_state = state

        """
        filepath = self.storage_path / f"{user_id}.json"
        validated_path = _validate_file_path(str(filepath), allowed_dir=str(self.storage_path))

        if not validated_path.exists():
            return None

        try:
            with open(validated_path) as f:
                data = json.load(f)

            state = CollaborationState()
            state.trust_level = data["trust_level"]
            state.total_interactions = data["total_interactions"]
            state.successful_interventions = data["successful_interventions"]
            state.failed_interventions = data["failed_interventions"]
            state.session_start = datetime.fromisoformat(data["session_start"])
            state.trust_trajectory = data.get("trust_trajectory", [])
            state.shared_context = data.get("shared_context", {})

            return state

        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - return None
            return None

    def list_users(self) -> list[str]:
        """List all users with saved state

        Returns:
            List of user IDs

        Example:
            >>> manager = StateManager()
            >>> users = manager.list_users()
            >>> print(f"Found {len(users)} users")

        """
        return [p.stem for p in self.storage_path.glob("*.json")]

    def delete_state(self, user_id: str) -> bool:
        """Delete user's saved state

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if didn't exist

        Example:
            >>> manager = StateManager()
            >>> deleted = manager.delete_state("user123")

        """
        filepath = self.storage_path / f"{user_id}.json"
        validated_path = _validate_file_path(str(filepath), allowed_dir=str(self.storage_path))

        if validated_path.exists():
            validated_path.unlink()
            return True
        return False
