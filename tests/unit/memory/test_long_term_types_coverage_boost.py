"""Comprehensive tests for long-term memory type definitions.

Tests for Classification enum, ClassificationRules dataclass, PatternMetadata
dataclass, SecurePattern dataclass, and security exceptions.

Module: memory/long_term_types.py (99 lines)
"""

import pytest

from attune.memory.long_term_types import (
    DEFAULT_CLASSIFICATION_RULES,
    Classification,
    ClassificationRules,
    PatternMetadata,
    PermissionError,
    SecurePattern,
    SecurityError,
)

# ============================================================================
# Classification Enum Tests
# ============================================================================


@pytest.mark.unit
class TestClassification:
    """Test suite for Classification enum."""

    def test_classification_has_public(self):
        """Test that Classification has PUBLIC value."""
        assert Classification.PUBLIC.value == "PUBLIC"

    def test_classification_has_internal(self):
        """Test that Classification has INTERNAL value."""
        assert Classification.INTERNAL.value == "INTERNAL"

    def test_classification_has_sensitive(self):
        """Test that Classification has SENSITIVE value."""
        assert Classification.SENSITIVE.value == "SENSITIVE"

    def test_classification_values_are_unique(self):
        """Test that all Classification values are unique."""
        values = [c.value for c in Classification]
        assert len(values) == len(set(values))

    def test_classification_count(self):
        """Test that Classification has exactly 3 levels."""
        assert len(list(Classification)) == 3


# ============================================================================
# ClassificationRules Dataclass Tests
# ============================================================================


@pytest.mark.unit
class TestClassificationRules:
    """Test suite for ClassificationRules dataclass."""

    def test_create_classification_rules_with_all_fields(self):
        """Test creating ClassificationRules with all fields."""
        rules = ClassificationRules(
            classification=Classification.PUBLIC,
            encryption_required=False,
            retention_days=365,
            access_level="all_users",
            audit_all_access=False,
        )

        assert rules.classification == Classification.PUBLIC
        assert rules.encryption_required is False
        assert rules.retention_days == 365
        assert rules.access_level == "all_users"
        assert rules.audit_all_access is False

    def test_create_classification_rules_with_defaults(self):
        """Test creating ClassificationRules with default audit_all_access."""
        rules = ClassificationRules(
            classification=Classification.INTERNAL,
            encryption_required=False,
            retention_days=180,
            access_level="project_team",
        )

        assert rules.classification == Classification.INTERNAL
        assert rules.audit_all_access is False  # Default value

    def test_classification_rules_for_public(self):
        """Test ClassificationRules for PUBLIC classification."""
        rules = ClassificationRules(
            classification=Classification.PUBLIC,
            encryption_required=False,
            retention_days=365,
            access_level="all_users",
        )

        assert rules.classification == Classification.PUBLIC
        assert rules.encryption_required is False
        assert rules.retention_days == 365
        assert rules.access_level == "all_users"

    def test_classification_rules_for_sensitive(self):
        """Test ClassificationRules for SENSITIVE classification."""
        rules = ClassificationRules(
            classification=Classification.SENSITIVE,
            encryption_required=True,
            retention_days=90,
            access_level="explicit_permission",
            audit_all_access=True,
        )

        assert rules.classification == Classification.SENSITIVE
        assert rules.encryption_required is True
        assert rules.retention_days == 90
        assert rules.access_level == "explicit_permission"
        assert rules.audit_all_access is True


# ============================================================================
# DEFAULT_CLASSIFICATION_RULES Tests
# ============================================================================


@pytest.mark.unit
class TestDefaultClassificationRules:
    """Test suite for DEFAULT_CLASSIFICATION_RULES constant."""

    def test_default_rules_has_all_classifications(self):
        """Test that default rules exist for all classifications."""
        for classification in Classification:
            assert classification in DEFAULT_CLASSIFICATION_RULES

    def test_default_rules_count(self):
        """Test that default rules has exactly 3 entries."""
        assert len(DEFAULT_CLASSIFICATION_RULES) == 3

    def test_default_public_rules(self):
        """Test default rules for PUBLIC classification."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.PUBLIC]

        assert rules.classification == Classification.PUBLIC
        assert rules.encryption_required is False
        assert rules.retention_days == 365
        assert rules.access_level == "all_users"
        assert rules.audit_all_access is False

    def test_default_internal_rules(self):
        """Test default rules for INTERNAL classification."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.INTERNAL]

        assert rules.classification == Classification.INTERNAL
        assert rules.encryption_required is False
        assert rules.retention_days == 180
        assert rules.access_level == "project_team"
        assert rules.audit_all_access is False

    def test_default_sensitive_rules(self):
        """Test default rules for SENSITIVE classification."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.SENSITIVE]

        assert rules.classification == Classification.SENSITIVE
        assert rules.encryption_required is True
        assert rules.retention_days == 90
        assert rules.access_level == "explicit_permission"
        assert rules.audit_all_access is True

    def test_sensitive_requires_encryption(self):
        """Test that SENSITIVE classification requires encryption."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.SENSITIVE]
        assert rules.encryption_required is True

    def test_sensitive_requires_audit(self):
        """Test that SENSITIVE classification requires audit."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.SENSITIVE]
        assert rules.audit_all_access is True


# ============================================================================
# PatternMetadata Dataclass Tests
# ============================================================================


@pytest.mark.unit
class TestPatternMetadata:
    """Test suite for PatternMetadata dataclass."""

    def test_create_pattern_metadata_with_all_fields(self):
        """Test creating PatternMetadata with all fields."""
        metadata = PatternMetadata(
            pattern_id="pat_123",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="INTERNAL",
            retention_days=180,
            encrypted=False,
            pattern_type="workflow_pattern",
            sanitization_applied=True,
            pii_removed=2,
            secrets_detected=0,
            access_control={"team": "engineering"},
            custom_metadata={"source": "session_123"},
        )

        assert metadata.pattern_id == "pat_123"
        assert metadata.created_by == "user@example.com"
        assert metadata.created_at == "2025-01-31T10:00:00Z"
        assert metadata.classification == "INTERNAL"
        assert metadata.retention_days == 180
        assert metadata.encrypted is False
        assert metadata.pattern_type == "workflow_pattern"
        assert metadata.sanitization_applied is True
        assert metadata.pii_removed == 2
        assert metadata.secrets_detected == 0
        assert metadata.access_control == {"team": "engineering"}
        assert metadata.custom_metadata == {"source": "session_123"}

    def test_create_pattern_metadata_with_defaults(self):
        """Test creating PatternMetadata with default dicts."""
        metadata = PatternMetadata(
            pattern_id="pat_456",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="PUBLIC",
            retention_days=365,
            encrypted=False,
            pattern_type="debugging_pattern",
            sanitization_applied=False,
            pii_removed=0,
            secrets_detected=0,
        )

        assert metadata.access_control == {}
        assert metadata.custom_metadata == {}

    def test_pattern_metadata_for_sensitive_data(self):
        """Test PatternMetadata for SENSITIVE classification."""
        metadata = PatternMetadata(
            pattern_id="pat_sensitive",
            created_by="admin@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="SENSITIVE",
            retention_days=90,
            encrypted=True,
            pattern_type="user_data",
            sanitization_applied=True,
            pii_removed=5,
            secrets_detected=1,
            access_control={"access_level": "explicit_permission"},
        )

        assert metadata.classification == "SENSITIVE"
        assert metadata.encrypted is True
        assert metadata.pii_removed == 5
        assert metadata.secrets_detected == 1
        assert metadata.access_control["access_level"] == "explicit_permission"

    def test_pattern_metadata_tracks_sanitization(self):
        """Test that PatternMetadata tracks sanitization metrics."""
        metadata = PatternMetadata(
            pattern_id="pat_sanitized",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="INTERNAL",
            retention_days=180,
            encrypted=False,
            pattern_type="code_pattern",
            sanitization_applied=True,
            pii_removed=3,
            secrets_detected=2,
        )

        assert metadata.sanitization_applied is True
        assert metadata.pii_removed == 3
        assert metadata.secrets_detected == 2


# ============================================================================
# SecurePattern Dataclass Tests
# ============================================================================


@pytest.mark.unit
class TestSecurePattern:
    """Test suite for SecurePattern dataclass."""

    def test_create_secure_pattern_with_all_fields(self):
        """Test creating SecurePattern with all fields."""
        metadata = PatternMetadata(
            pattern_id="pat_123",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="INTERNAL",
            retention_days=180,
            encrypted=False,
            pattern_type="workflow_pattern",
            sanitization_applied=True,
            pii_removed=0,
            secrets_detected=0,
        )

        pattern = SecurePattern(
            pattern_id="pat_123",
            content="Pattern content here",
            metadata=metadata,
        )

        assert pattern.pattern_id == "pat_123"
        assert pattern.content == "Pattern content here"
        assert pattern.metadata == metadata

    def test_secure_pattern_contains_metadata(self):
        """Test that SecurePattern contains PatternMetadata."""
        metadata = PatternMetadata(
            pattern_id="pat_456",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="PUBLIC",
            retention_days=365,
            encrypted=False,
            pattern_type="debugging_pattern",
            sanitization_applied=False,
            pii_removed=0,
            secrets_detected=0,
        )

        pattern = SecurePattern(pattern_id="pat_456", content="Debug pattern", metadata=metadata)

        assert pattern.metadata.classification == "PUBLIC"
        assert pattern.metadata.pattern_type == "debugging_pattern"

    def test_secure_pattern_with_encrypted_content(self):
        """Test SecurePattern with encrypted flag in metadata."""
        metadata = PatternMetadata(
            pattern_id="pat_encrypted",
            created_by="admin@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification="SENSITIVE",
            retention_days=90,
            encrypted=True,
            pattern_type="user_data",
            sanitization_applied=True,
            pii_removed=5,
            secrets_detected=0,
        )

        pattern = SecurePattern(
            pattern_id="pat_encrypted",
            content="<encrypted data>",
            metadata=metadata,
        )

        assert pattern.metadata.encrypted is True
        assert pattern.content == "<encrypted data>"


# ============================================================================
# Exception Tests
# ============================================================================


@pytest.mark.unit
class TestSecurityExceptions:
    """Test suite for security exception types."""

    def test_security_error_can_be_raised(self):
        """Test that SecurityError can be raised."""
        with pytest.raises(SecurityError, match="Policy violated"):
            raise SecurityError("Policy violated")

    def test_security_error_is_exception(self):
        """Test that SecurityError is an Exception subclass."""
        error = SecurityError("Test error")
        assert isinstance(error, Exception)

    def test_permission_error_can_be_raised(self):
        """Test that PermissionError can be raised."""
        with pytest.raises(PermissionError, match="Access denied"):
            raise PermissionError("Access denied")

    def test_permission_error_is_exception(self):
        """Test that PermissionError is an Exception subclass."""
        error = PermissionError("Test error")
        assert isinstance(error, Exception)

    def test_security_error_with_custom_message(self):
        """Test SecurityError with custom message."""
        message = "Encryption required for SENSITIVE classification"
        with pytest.raises(SecurityError, match=message):
            raise SecurityError(message)

    def test_permission_error_with_custom_message(self):
        """Test PermissionError with custom message."""
        message = "User lacks explicit_permission for SENSITIVE data"
        with pytest.raises(PermissionError, match=message):
            raise PermissionError(message)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestIntegration:
    """Integration tests for type definitions working together."""

    def test_secure_pattern_with_default_rules(self):
        """Test creating SecurePattern using default classification rules."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.INTERNAL]

        metadata = PatternMetadata(
            pattern_id="pat_integration",
            created_by="user@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification=rules.classification.value,
            retention_days=rules.retention_days,
            encrypted=rules.encryption_required,
            pattern_type="integration_test",
            sanitization_applied=False,
            pii_removed=0,
            secrets_detected=0,
        )

        pattern = SecurePattern(
            pattern_id="pat_integration",
            content="Integration test content",
            metadata=metadata,
        )

        assert pattern.metadata.classification == "INTERNAL"
        assert pattern.metadata.retention_days == 180
        assert pattern.metadata.encrypted is False

    def test_sensitive_pattern_enforces_encryption(self):
        """Test that SENSITIVE patterns use encryption rules."""
        rules = DEFAULT_CLASSIFICATION_RULES[Classification.SENSITIVE]

        # Verify that sensitive classification requires encryption
        assert rules.encryption_required is True

        metadata = PatternMetadata(
            pattern_id="pat_sensitive_test",
            created_by="admin@example.com",
            created_at="2025-01-31T10:00:00Z",
            classification=rules.classification.value,
            retention_days=rules.retention_days,
            encrypted=rules.encryption_required,
            pattern_type="sensitive_data",
            sanitization_applied=True,
            pii_removed=10,
            secrets_detected=2,
        )

        pattern = SecurePattern(
            pattern_id="pat_sensitive_test",
            content="<encrypted>",
            metadata=metadata,
        )

        assert pattern.metadata.encrypted is True
        assert pattern.metadata.classification == "SENSITIVE"
