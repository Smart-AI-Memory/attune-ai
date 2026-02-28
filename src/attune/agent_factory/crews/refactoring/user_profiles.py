"""Refactoring Crew - User Profile Management

Standalone functions for loading, saving, and updating user profiles
that track refactoring preferences over time.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from attune.security.path_validation import _validate_file_path

from .types import Impact, RefactoringFinding, UserProfile

logger = logging.getLogger(__name__)


def load_user_profile(profile_path: str) -> UserProfile:
    """Load user profile from disk.

    Args:
        profile_path: Path to the user profile JSON file.

    Returns:
        UserProfile loaded from disk, or a default UserProfile on failure.

    """
    path = Path(profile_path)
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return UserProfile.from_dict(data)
        except (OSError, PermissionError) as e:
            # File system errors reading profile
            logger.warning(f"Failed to load user profile (file system error): {e}")
        except json.JSONDecodeError as e:
            # Invalid JSON in profile file
            logger.warning(f"Failed to load user profile (invalid JSON): {e}")
        except (KeyError, ValueError, TypeError) as e:
            # Profile data validation errors
            logger.warning(f"Failed to load user profile (data error): {e}")
        except Exception:
            # INTENTIONAL: User profile is optional - start with default
            logger.exception("Unexpected error loading user profile")
    return UserProfile()


def save_user_profile(user_profile: UserProfile, profile_path: str) -> None:
    """Save user profile to disk.

    Args:
        user_profile: The UserProfile to save.
        profile_path: Path to the user profile JSON file.

    """
    path = Path(profile_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    user_profile.updated_at = datetime.now().isoformat()

    try:
        validated_path = _validate_file_path(str(path))
        with open(validated_path, "w") as f:
            json.dump(user_profile.to_dict(), f, indent=2)
    except (OSError, PermissionError) as e:
        # File system errors writing profile
        logger.warning(f"Failed to save user profile (file system error): {e}")
    except (TypeError, ValueError) as e:
        # JSON serialization errors
        logger.warning(f"Failed to save user profile (serialization error): {e}")
    except Exception:
        # INTENTIONAL: User profile save is optional - don't crash on failure
        logger.exception("Unexpected error saving user profile")


def record_decision(
    user_profile: UserProfile,
    finding: RefactoringFinding,
    accepted: bool,
    profile_path: str,
) -> None:
    """Record user decision for learning.

    Args:
        user_profile: The UserProfile to update.
        finding: The finding that was accepted or rejected.
        accepted: True if user accepted, False if rejected.
        profile_path: Path to the user profile JSON file for saving.

    """
    cat = finding.category.value

    if accepted:
        user_profile.accepted_categories[cat] = user_profile.accepted_categories.get(cat, 0) + 1
    else:
        user_profile.rejected_categories[cat] = user_profile.rejected_categories.get(cat, 0) + 1

    # Add to history
    user_profile.history.append(
        {
            "session_id": str(uuid.uuid4())[:8],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "file": finding.file_path,
            "category": cat,
            "accepted": accepted,
        },
    )

    # Keep history bounded
    if len(user_profile.history) > 100:
        user_profile.history = user_profile.history[-100:]

    save_user_profile(user_profile, profile_path)


def apply_user_preferences(
    findings: list[RefactoringFinding],
    user_profile: UserProfile,
) -> list[RefactoringFinding]:
    """Apply user preferences to prioritize findings.

    Args:
        findings: List of findings to reorder.
        user_profile: The user profile with preference data.

    Returns:
        Findings sorted by user-preference-adjusted score.

    """

    def score(finding: RefactoringFinding) -> float:
        # Base score from impact
        impact_scores = {Impact.HIGH: 3.0, Impact.MEDIUM: 2.0, Impact.LOW: 1.0}
        base = impact_scores.get(finding.estimated_impact, 2.0)

        # Adjust by user preference
        pref = user_profile.get_category_score(finding.category)
        adjusted = base * (0.5 + pref)  # Range: 0.5x to 1.5x

        # Adjust by confidence
        return adjusted * finding.confidence

    return sorted(findings, key=score, reverse=True)
