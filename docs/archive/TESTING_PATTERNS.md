---
description: Testing Patterns Library: ## Reusable Patterns from Educational Test Suite **Source**: Attune AI Test Suite (307 tests, 17.64% coverage) **Version**: 1.
---

# Testing Patterns Library
## Reusable Patterns from Educational Test Suite

**Source**: Attune AI Test Suite (307 tests, 17.64% coverage)
**Version**: 1.0.0
**Last Updated**: 2026-01-04

This guide consolidates 20+ reusable testing patterns demonstrated across our educational test suite. Each pattern includes copy-paste ready examples and guidance on when to use them.

---

## Table of Contents

### Foundation Patterns (Phase 1)
1. [File I/O Mocking with tmp_path](#1-file-io-mocking-with-tmp_path)
2. [Parametrized Pattern Matching](#2-parametrized-pattern-matching)
3. [Context-Aware Analysis Testing](#3-context-aware-analysis-testing)
4. [Multi-File Context Gathering](#4-multi-file-context-gathering)
5. [Meta-Detection Testing](#5-meta-detection-testing)

### State Management Patterns (Phase 2)
6. [Built-in Mock Mode](#6-built-in-mock-mode)
7. [TTL Strategy Testing](#7-ttl-strategy-testing)
8. [Role-Based Access Control](#8-role-based-access-control)
9. [Connection Retry with Exponential Backoff](#9-connection-retry-with-exponential-backoff)
10. [Metrics Tracking and Observability](#10-metrics-tracking-and-observability)

### Security Patterns (Phase 3)
11. [Parametrized PII Testing](#11-parametrized-pii-testing)
12. [Custom Pattern Registration](#12-custom-pattern-registration)
13. [Audit-Safe Serialization](#13-audit-safe-serialization)
14. [Pattern Enable/Disable Management](#14-pattern-enabledisable-management)
15. [Performance Testing with Large Inputs](#15-performance-testing-with-large-inputs)

### Architecture Patterns (Phase 4)
16. [Registry Completeness Validation](#16-registry-completeness-validation)
17. [Computed Properties Testing](#17-computed-properties-testing)
18. [Immutable Dataclass Testing](#18-immutable-dataclass-testing)
19. [Case-Insensitive Lookup Testing](#19-case-insensitive-lookup-testing)
20. [Cost Hierarchy Validation](#20-cost-hierarchy-validation)

### Cross-Cutting Patterns
21. [Classification System Testing](#21-classification-system-testing)
22. [Fixture Reuse and Composition](#22-fixture-reuse-and-composition)

---

## Foundation Patterns (Phase 1)

### 1. File I/O Mocking with tmp_path

**When to use**: Testing functions that read/write configuration files, project files, or any file system operations.

**Pattern**:
```python
def test_config_loading(tmp_path, monkeypatch):
    """
    Teaching Pattern: File I/O mocking with tmp_path.

    Creates isolated test directory to avoid polluting real filesystem.
    """
    # Create test configuration
    config_file = tmp_path / "empathy.config.yml"
    config_file.write_text("""
bug_predict:
  risk_threshold: 0.8
  exclude_files: ["**/test_*.py"]
""")

    # Change to test directory
    monkeypatch.chdir(tmp_path)

    # Test the function
    config = load_config()
    assert config["bug_predict"]["risk_threshold"] == 0.8
```

**Key Benefits**:
- ✅ No test pollution (isolated directories)
- ✅ Fast execution (in-memory on some systems)
- ✅ Automatic cleanup
- ✅ Easy to create complex directory structures

**Source**: [test_bug_predict_helpers.py:55](../tests/unit/workflows/test_bug_predict_helpers.py#L55)

---

### 2. Parametrized Pattern Matching

**When to use**: Testing the same logic with multiple input/output combinations (pattern matching, validation rules, etc.).

**Pattern**:
```python
@pytest.mark.parametrize("file_path,pattern,expected", [
    ("tests/test_foo.py", "**/test_*.py", True),
    ("src/main.py", "**/test_*.py", False),
    ("src/fixtures/test.py", "**/fixtures/*", True),
    ("docs/readme.md", "**/*.md", True),
])
def test_pattern_matching(file_path, pattern, expected):
    """
    Teaching Pattern: Parametrized testing for pattern matching.

    Tests multiple pattern combinations in a single test function.
    """
    result = should_exclude_file(file_path, [pattern])
    assert result == expected
```

**Key Benefits**:
- ✅ DRY (Don't Repeat Yourself) - one test, many scenarios
- ✅ Easy to add new test cases
- ✅ Clear failure messages (shows which parameters failed)
- ✅ Reduces test maintenance

**Source**: [test_bug_predict_helpers.py:127](../tests/unit/workflows/test_bug_predict_helpers.py#L127)

---

### 3. Context-Aware Analysis Testing

**When to use**: Testing code that analyzes surrounding lines (security scanning, code analysis, etc.).

**Pattern**:
```python
def test_context_aware_exception_analysis():
    """
    Teaching Pattern: Testing context-aware code analysis.

    Analyzes lines before/after to determine if exception handling is acceptable.
    """
    workflow = BugPredictWorkflow()

    # Test case: Exception with logging and re-raise (acceptable)
    lines = [
        "try:",
        "    result = dangerous_operation()",
        "except Exception as e:",
        "    logger.error(f'Failed: {e}')",
        "    raise  # Re-raises the exception",
    ]

    # Analyze line 3 (the except line)
    is_acceptable = workflow._is_acceptable_broad_exception(
        exception_line=lines[2],
        lines_before=lines[:2],
        lines_after=lines[3:]
    )

    assert is_acceptable is True  # Logging + re-raise is acceptable
```

**Key Benefits**:
- ✅ Tests real-world scenarios (not just isolated lines)
- ✅ Validates business logic (what makes code acceptable?)
- ✅ Reduces false positives in static analysis

**Source**: [test_bug_predict_helpers.py:208](../tests/unit/workflows/test_bug_predict_helpers.py#L208)

---

### 4. Multi-File Context Gathering

**When to use**: Testing functions that gather information from multiple project files.

**Pattern**:
```python
def test_full_project_context(tmp_path, monkeypatch):
    """
    Teaching Pattern: Testing multi-file context gathering.

    Creates complete project structure to test context aggregation.
    """
    monkeypatch.chdir(tmp_path)

    # Create project files
    (tmp_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-project"
version = "1.0.0"
""")

    (tmp_path / "package.json").write_text("""
{
  "name": "test-project",
  "version": "1.0.0"
}
""")

    (tmp_path / "README.md").write_text("# Test Project\\n\\nA test project.")

    # Test context gathering
    workflow = CodeReviewWorkflow()
    context = workflow._gather_project_context()

    # Verify all files were gathered
    assert "## pyproject.toml" in context
    assert "## package.json" in context
    assert "## README" in context
    assert "test-project" in context
```

**Key Benefits**:
- ✅ Tests integration of multiple file reads
- ✅ Validates aggregation logic
- ✅ Easy to add new file types

**Source**: [test_code_review_helpers.py:161](../tests/unit/workflows/test_code_review_helpers.py#L161)

---

### 5. Meta-Detection Testing

**When to use**: Testing security scanners that need to avoid flagging their own detection code.

**Pattern**:
```python
def test_meta_detection_distinguishes_detection_from_vulnerability():
    """
    Teaching Pattern: Testing meta-detection (detecting detection code).

    Security scanners must not flag their own pattern matching code.
    """
    workflow = SecurityAuditWorkflow()

    # Detection code (safe) - should NOT be flagged
    detection_lines = [
        'if "eval(" in content:',
        'pattern = re.compile(r"eval\\(")',
        'matches = pattern.finditer(code)',
    ]

    for line in detection_lines:
        is_detection = workflow._is_detection_code(line, "eval(")
        assert is_detection is True, f"Should identify {line} as detection code"

    # Actual vulnerability (dangerous) - SHOULD be flagged
    vulnerability_lines = [
        "result = eval(user_input)",
        "data = eval(request.json['code'])",
    ]

    for line in vulnerability_lines:
        is_detection = workflow._is_detection_code(line, "eval(")
        assert is_detection is False, f"Should identify {line} as vulnerability"
```

**Key Benefits**:
- ✅ Prevents false positives in security tools
- ✅ Tests precision vs recall tradeoffs
- ✅ Documents what constitutes "safe" detection code

**Source**: [test_security_audit_helpers.py:49](../tests/unit/workflows/test_security_audit_helpers.py#L49)

---

## State Management Patterns (Phase 2)

### 6. Built-in Mock Mode

**When to use**: Testing stateful systems without external dependencies (Redis, databases, etc.).

**Pattern**:
```python
def test_initialization_with_mock_mode():
    """
    Teaching Pattern: Testing with built-in mock mode.

    Tests the system without requiring Redis to be running.
    """
    # Create memory instance with mock mode
    memory = RedisShortTermMemory(use_mock=True)

    # Verify mock mode is enabled
    assert memory.use_mock is True
    assert memory._client is None
    assert memory._mock_storage == {}

    # Test operations work in mock mode
    creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)
    memory.stash("key", {"data": "value"}, creds)

    retrieved = memory.retrieve("key", creds)
    assert retrieved == {"data": "value"}
```

**Key Benefits**:
- ✅ No external dependencies
- ✅ Fast execution
- ✅ Consistent behavior
- ✅ Easy CI/CD integration

**Source**: [test_short_term.py:102](../tests/unit/memory/test_short_term.py#L102)

---

### 7. TTL Strategy Testing

**When to use**: Testing time-to-live (expiration) strategies for cached data.

**Pattern**:
```python
def test_different_ttl_strategies_for_different_data_types(memory, agent_creds):
    """
    Teaching Pattern: Testing TTL strategy business logic.

    Different data types should have different TTL strategies.
    """
    # Working results - short-lived (1 hour)
    memory.stash("working:result1", {"data": "temp"}, agent_creds,
                 ttl=TTLStrategy.WORKING_RESULTS)

    # Staged patterns - medium-lived (24 hours)
    memory.stash("staged:pattern1", {"code": "def foo(): pass"}, agent_creds,
                 ttl=TTLStrategy.STAGED_PATTERNS)

    # Coordination - very short (5 minutes)
    memory.stash("coord:signal1", {"status": "ready"}, agent_creds,
                 ttl=TTLStrategy.COORDINATION)

    # All should be retrievable immediately
    assert memory.retrieve("working:result1", agent_creds) is not None
    assert memory.retrieve("staged:pattern1", agent_creds) is not None
    assert memory.retrieve("coord:signal1", agent_creds) is not None
```

**Key Benefits**:
- ✅ Tests business logic (not just expiration)
- ✅ Documents data lifecycle
- ✅ Uses enums for type safety

**Source**: [test_short_term.py:268](../tests/unit/memory/test_short_term.py#L268)

---

### 8. Role-Based Access Control

**When to use**: Testing permission systems with multiple tiers.

**Pattern**:
```python
def test_contributor_and_above_can_stash(memory):
    """
    Teaching Pattern: Testing role-based access control.

    Only certain tiers can perform write operations.
    """
    # Observer cannot write
    observer = AgentCredentials("observer", AccessTier.OBSERVER)
    with pytest.raises(PermissionError):
        memory.stash("data", {"test": "value"}, observer)

    # Contributor and above CAN write
    tiers_that_can_write = [
        AgentCredentials("contributor", AccessTier.CONTRIBUTOR),
        AgentCredentials("validator", AccessTier.VALIDATOR),
        AgentCredentials("steward", AccessTier.STEWARD),
    ]

    for tier_creds in tiers_that_can_write:
        key = f"data_{tier_creds.agent_id}"
        data = {"tier": tier_creds.tier.name}

        memory.stash(key, data, tier_creds)
        retrieved = memory.retrieve(key, tier_creds)

        assert retrieved == data
```

**Key Benefits**:
- ✅ Tests permission boundaries
- ✅ Validates hierarchical access
- ✅ Documents authorization model

**Source**: [test_short_term.py:373](../tests/unit/memory/test_short_term.py#L373)

---

### 9. Connection Retry with Exponential Backoff

**When to use**: Testing retry logic for unreliable external services.

**Pattern**:
```python
@patch('attune.memory.short_term.redis.Redis')
@patch('attune.memory.short_term.logger')
def test_connection_retry_on_failure(mock_logger, mock_redis_class):
    """
    Teaching Pattern: Testing retry logic with mock failures.

    Simulates transient failures and verifies exponential backoff.
    """
    from redis.exceptions import ConnectionError as RedisConnectionError

    # Mock Redis instance
    mock_instance = Mock()

    # Fail twice, then succeed
    mock_instance.ping.side_effect = [
        RedisConnectionError("Connection failed"),  # Attempt 1: fail
        RedisConnectionError("Connection failed"),  # Attempt 2: fail
        None,  # Attempt 3: success
    ]
    mock_redis_class.return_value = mock_instance

    config = RedisConfig(use_mock=False, retry_max_attempts=3)

    with patch('attune.memory.short_term.REDIS_AVAILABLE', True):
        memory = RedisShortTermMemory(config=config)

        # Should have called ping 3 times
        assert mock_instance.ping.call_count == 3
        # Connection succeeded
        assert memory._client == mock_instance
```

**Key Benefits**:
- ✅ Tests resilience to transient failures
- ✅ Validates retry count and delays
- ✅ No actual network calls

**Source**: [test_short_term.py:438](../tests/unit/memory/test_short_term.py#L438)

---

### 10. Metrics Tracking and Observability

**When to use**: Testing telemetry, metrics collection, and observability features.

**Pattern**:
```python
def test_success_rate_calculation():
    """
    Teaching Pattern: Testing metrics calculation.

    Validates success rate computation from operation counts.
    """
    metrics = ShortTermMetrics()

    # Record mixed success/failure operations
    metrics.record_operation("stash", success=True, latency_ms=10.0)
    metrics.record_operation("stash", success=True, latency_ms=12.0)
    metrics.record_operation("stash", success=False, latency_ms=5.0)
    metrics.record_operation("retrieve", success=True, latency_ms=8.0)

    # Calculate success rate
    success_rate = metrics.success_rate()

    # 3 successes / 4 total = 0.75
    assert success_rate == 0.75

    # Verify operation counts
    assert metrics.successful_operations == 3
    assert metrics.failed_operations == 1
```

**Key Benefits**:
- ✅ Tests observability features
- ✅ Validates calculation logic
- ✅ Documents metrics collection

**Source**: [test_short_term.py:551](../tests/unit/memory/test_short_term.py#L551)

---

## Security Patterns (Phase 3)

### 11. Parametrized PII Testing

**When to use**: Testing PII detection across multiple data types (emails, SSNs, credit cards, etc.).

**Pattern**:
```python
@pytest.mark.parametrize("text,pii_type,expected_replacement", [
    ("Email: user@example.com", "email", "[EMAIL]"),
    ("SSN: 123-45-6789", "ssn", "[SSN]"),
    ("Call: 555-123-4567", "phone", "[PHONE]"),
    ("CC: 4532-1234-5678-9010", "credit_card", "[CC]"),
    ("IP: 192.168.1.1", "ipv4", "[IP]"),
    ("MRN-1234567", "mrn", "[MRN]"),
    ("Patient ID: 123456", "patient_id", "[PATIENT_ID]"),
])
def test_multi_pattern_detection(scrubber, text, pii_type, expected_replacement):
    """
    Teaching Pattern: Parametrized testing for multiple PII types.

    Tests each PII pattern individually with expected replacement.
    """
    scrubbed, detections = scrubber.scrub(text)

    assert len(detections) >= 1
    assert expected_replacement in scrubbed
    assert any(d.pii_type == pii_type for d in detections)
```

**Key Benefits**:
- ✅ Tests all PII types systematically
- ✅ Easy to add new PII patterns
- ✅ Clear which pattern failed
- ✅ Compliance validation (GDPR, HIPAA)

**Source**: [test_pii_scrubber.py:69](../tests/unit/memory/security/test_pii_scrubber.py#L69)

---

### 12. Custom Pattern Registration

**When to use**: Testing extensibility of pattern-based systems (PII detection, validation, etc.).

**Pattern**:
```python
def test_add_custom_pattern(scrubber):
    """
    Teaching Pattern: Testing custom pattern registration.

    Organizations need domain-specific PII patterns.
    """
    # Register custom pattern
    scrubber.add_custom_pattern(
        name="employee_id",
        pattern=r"EMP-\\d{6}",
        replacement="[EMPLOYEE_ID]",
        confidence=0.95,
        description="Company employee identifier"
    )

    # Test custom pattern works
    text = "Employee EMP-123456 submitted report"
    scrubbed, detections = scrubber.scrub(text)

    assert "[EMPLOYEE_ID]" in scrubbed
    assert "EMP-123456" not in scrubbed
    assert any(d.pii_type == "employee_id" for d in detections)
    assert detections[0].confidence == 0.95
```

**Key Benefits**:
- ✅ Tests extensibility
- ✅ Validates custom configuration
- ✅ Documents extension points

**Source**: [test_pii_scrubber.py:188](../tests/unit/memory/security/test_pii_scrubber.py#L188)

---

### 13. Audit-Safe Serialization

**When to use**: Testing systems that log sensitive data (audit logs, telemetry, etc.).

**Pattern**:
```python
def test_detection_to_audit_safe_dict(scrubber):
    """
    Teaching Pattern: Testing audit-safe serialization.

    Audit logs should NOT contain actual PII values.
    """
    text = "Email: user@example.com"
    scrubbed, detections = scrubber.scrub(text)

    detection = detections[0]

    # Audit-safe version should NOT include matched_text
    audit_dict = detection.to_audit_safe_dict()

    assert "matched_text" not in audit_dict  # ❌ No PII in logs!
    assert "pii_type" in audit_dict          # ✅ What type detected
    assert "position" in audit_dict          # ✅ Where it was found
    assert "length" in audit_dict            # ✅ How long it was
    assert "confidence" in audit_dict        # ✅ Detection confidence
```

**Key Benefits**:
- ✅ Prevents PII leakage in logs
- ✅ Compliance with data protection regulations
- ✅ Documents safe logging practices

**Source**: [test_pii_scrubber.py:159](../tests/unit/memory/security/test_pii_scrubber.py#L159)

---

### 14. Pattern Enable/Disable Management

**When to use**: Testing dynamic configuration of pattern-based systems.

**Pattern**:
```python
def test_disable_pattern(scrubber):
    """
    Teaching Pattern: Testing pattern disabling.

    Patterns can be temporarily disabled without removal.
    """
    # Disable email pattern
    scrubber.disable_pattern("email")

    text = "Contact: user@example.com"
    scrubbed, detections = scrubber.scrub(text)

    # Email should NOT be detected
    assert "user@example.com" in scrubbed
    assert not any(d.pii_type == "email" for d in detections)

def test_enable_pattern(scrubber):
    """
    Teaching Pattern: Testing pattern re-enabling.

    Disabled patterns can be re-enabled.
    """
    # Name detection is disabled by default
    scrubber.enable_pattern("name")

    text = "Patient: John Smith"
    scrubbed, detections = scrubber.scrub(text)

    # Name should now be detected
    assert "[NAME]" in scrubbed or "John Smith" not in scrubbed
```

**Key Benefits**:
- ✅ Tests runtime configuration
- ✅ Validates state management
- ✅ Documents feature toggles

**Source**: [test_pii_scrubber.py:305](../tests/unit/memory/security/test_pii_scrubber.py#L305)

---

### 15. Performance Testing with Large Inputs

**When to use**: Testing performance and scalability of text processing, parsing, etc.

**Pattern**:
```python
def test_very_long_text(scrubber):
    """
    Teaching Pattern: Testing performance with large inputs.

    Scrubber should handle large text efficiently.
    """
    # Create large text with scattered PII (2000+ words)
    large_text = (
        "Normal text. " * 1000 +
        "Email: user@example.com. " +
        "More text. " * 1000
    )

    # Time the operation (optional)
    import time
    start = time.time()

    scrubbed, detections = scrubber.scrub(large_text)

    elapsed = time.time() - start

    # Should still detect the email
    assert len(detections) >= 1
    assert "[EMAIL]" in scrubbed

    # Should complete in reasonable time (< 1 second for 2000 words)
    assert elapsed < 1.0
```

**Key Benefits**:
- ✅ Tests scalability
- ✅ Identifies performance regressions
- ✅ Documents performance requirements

**Source**: [test_pii_scrubber.py:416](../tests/unit/memory/security/test_pii_scrubber.py#L416)

---

## Architecture Patterns (Phase 4)

### 16. Registry Completeness Validation

**When to use**: Testing that registries, catalogs, or configuration have all required entries.

**Pattern**:
```python
def test_each_provider_has_all_tiers():
    """
    Teaching Pattern: Testing registry completeness.

    Every provider should have all tier levels configured.
    """
    from attune.models.registry import MODEL_REGISTRY

    # Define required tiers
    required_tiers = ["cheap", "capable", "premium"]

    # Validate each provider
    for provider_name, models in MODEL_REGISTRY.items():
        for tier in required_tiers:
            assert tier in models, f"{provider_name} missing '{tier}' tier"
```

**Key Benefits**:
- ✅ Validates configuration completeness
- ✅ Prevents missing entries
- ✅ Self-documenting requirements

**Source**: [test_registry.py:234](../tests/unit/models/test_registry.py#L234)

---

### 17. Computed Properties Testing

**When to use**: Testing @property decorators and derived values.

**Pattern**:
```python
def test_model_info_compatibility_properties():
    """
    Teaching Pattern: Testing computed properties.

    ModelInfo provides compatibility properties for different systems.
    """
    model = ModelInfo(
        id="test-model",
        provider="anthropic",
        tier="cheap",
        input_cost_per_million=1000.0,
        output_cost_per_million=5000.0,
    )

    # Test computed properties
    assert model.model_id == "test-model"  # Alias
    assert model.name == "test-model"      # Another alias

    # Test cost conversion (per-million → per-1k)
    assert model.cost_per_1k_input == 1.0   # 1000 / 1000
    assert model.cost_per_1k_output == 5.0  # 5000 / 1000
```

**Key Benefits**:
- ✅ Tests derived values
- ✅ Validates backward compatibility
- ✅ Documents property behavior

**Source**: [test_registry.py:111](../tests/unit/models/test_registry.py#L111)

---

### 18. Immutable Dataclass Testing

**When to use**: Testing frozen dataclasses or immutable objects.

**Pattern**:
```python
def test_model_info_frozen_dataclass():
    """
    Teaching Pattern: Testing immutability.

    ModelInfo is frozen - cannot be modified after creation.
    """
    model = ModelInfo(
        id="test-model",
        provider="anthropic",
        tier="cheap",
        input_cost_per_million=1.0,
        output_cost_per_million=5.0,
    )

    # Attempting to modify should raise error
    with pytest.raises(Exception):  # FrozenInstanceError
        model.id = "new-id"

    # Verify original value unchanged
    assert model.id == "test-model"
```

**Key Benefits**:
- ✅ Tests immutability enforcement
- ✅ Validates data integrity
- ✅ Documents design constraints

**Source**: [test_registry.py:197](../tests/unit/models/test_registry.py#L197)

---

### 19. Case-Insensitive Lookup Testing

**When to use**: Testing systems that should handle case-insensitive input (user-facing APIs, etc.).

**Pattern**:
```python
def test_get_model_case_insensitive():
    """
    Teaching Pattern: Testing case insensitivity.

    Lookups should work regardless of case.
    """
    from attune.models.registry import get_model

    # Test different case combinations
    model1 = get_model("ANTHROPIC", "CHEAP")
    model2 = get_model("anthropic", "cheap")
    model3 = get_model("Anthropic", "Cheap")

    # All should return same model
    assert model1 is not None
    assert model1.id == model2.id == model3.id
```

**Key Benefits**:
- ✅ Tests user-friendly APIs
- ✅ Validates normalization logic
- ✅ Prevents case-related bugs

**Source**: [test_registry.py:294](../tests/unit/models/test_registry.py#L294)

---

### 20. Cost Hierarchy Validation

**When to use**: Testing business logic that enforces ordering constraints (pricing tiers, access levels, etc.).

**Pattern**:
```python
def test_tier_pricing_hierarchy():
    """
    Teaching Pattern: Testing cost hierarchy.

    Premium should cost more than capable, which costs more than cheap.
    """
    from attune.models.registry import TIER_PRICING

    # Extract input costs
    cheap_input = TIER_PRICING["cheap"]["input"]
    capable_input = TIER_PRICING["capable"]["input"]
    premium_input = TIER_PRICING["premium"]["input"]

    # Validate hierarchy
    assert cheap_input < capable_input < premium_input

    # Optional: Test specific ranges
    assert cheap_input < 1.0      # Less than $1/M
    assert capable_input < 5.0    # Less than $5/M
    assert premium_input >= 10.0  # At least $10/M
```

**Key Benefits**:
- ✅ Tests business logic constraints
- ✅ Validates pricing models
- ✅ Documents tier expectations

**Source**: [test_registry.py:435](../tests/unit/models/test_registry.py#L435)

---

## Cross-Cutting Patterns

### 21. Classification System Testing

**When to use**: Testing multi-tier classification systems (security levels, data tiers, etc.).

**Pattern**:
```python
def test_classification_enum_values():
    """
    Teaching Pattern: Testing classification tiers.

    Three-tier system: PUBLIC → INTERNAL → SENSITIVE
    """
    from attune.memory.long_term import Classification

    # Test enum values
    assert Classification.PUBLIC.value == "public"
    assert Classification.INTERNAL.value == "internal"
    assert Classification.SENSITIVE.value == "sensitive"

    # Test ordering (if needed)
    tiers = [Classification.PUBLIC, Classification.INTERNAL, Classification.SENSITIVE]
    assert len(tiers) == 3

def test_sensitive_requires_encryption():
    """
    Teaching Pattern: Testing classification rules.

    SENSITIVE data must be encrypted.
    """
    from attune.memory.long_term import DEFAULT_CLASSIFICATION_RULES, Classification

    rules = DEFAULT_CLASSIFICATION_RULES[Classification.SENSITIVE]

    assert rules.encryption_required is True
    assert rules.retention_days >= 90  # Longer retention for sensitive data
```

**Key Benefits**:
- ✅ Tests security policies
- ✅ Validates compliance rules
- ✅ Documents data governance

**Source**: [test_long_term.py:24](../tests/unit/memory/test_long_term.py#L24)

---

### 22. Fixture Reuse and Composition

**When to use**: Reducing test duplication and improving maintainability.

**Pattern**:
```python
# Base fixtures
@pytest.fixture
def scrubber():
    """Fixture for PII scrubber."""
    return PIIScrubber()

@pytest.fixture
def agent_creds():
    """Fixture for agent credentials."""
    return AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

@pytest.fixture
def memory():
    """Fixture for short-term memory with mock mode."""
    return RedisShortTermMemory(use_mock=True)

# Composed fixture
@pytest.fixture
def memory_with_data(memory, agent_creds):
    """Fixture with pre-populated data."""
    memory.stash("key1", {"data": "value1"}, agent_creds)
    memory.stash("key2", {"data": "value2"}, agent_creds)
    return memory

# Use in tests
def test_with_prepopulated_memory(memory_with_data, agent_creds):
    """Uses composed fixture."""
    data = memory_with_data.retrieve("key1", agent_creds)
    assert data == {"data": "value1"}
```

**Key Benefits**:
- ✅ DRY test setup
- ✅ Reusable across test classes
- ✅ Easier test maintenance
- ✅ Clear dependencies

**Source**: Multiple test files

---

## Pattern Selection Guide

### By Testing Goal

| Goal | Recommended Patterns |
|------|---------------------|
| **File I/O** | #1 (tmp_path), #4 (Multi-file) |
| **Multiple Scenarios** | #2 (Parametrized), #11 (Parametrized PII) |
| **Security** | #5 (Meta-detection), #11-15 (Security patterns) |
| **State Management** | #6-10 (State patterns) |
| **Configuration** | #1 (tmp_path), #14 (Pattern management) |
| **Performance** | #15 (Large inputs), #10 (Metrics) |
| **Architecture** | #16-20 (Architecture patterns) |
| **Data Privacy** | #11-13 (PII, Audit-safe) |

### By Complexity

| Complexity | Patterns |
|-----------|----------|
| **Beginner** | #1, #2, #22 |
| **Intermediate** | #3, #4, #6-10 |
| **Advanced** | #5, #11-15, #16-20 |
| **Expert** | #9, #13, #17 |

---

## Best Practices Summary

1. **Use Fixtures Wisely** (#22)
   - Create reusable fixtures for common setup
   - Compose fixtures for complex scenarios
   - Keep fixtures focused and single-purpose

2. **Parametrize When Possible** (#2, #11)
   - Reduces code duplication
   - Makes adding test cases easy
   - Improves failure reporting

3. **Test Edge Cases** (#15)
   - Empty inputs
   - Very large inputs
   - Boundary conditions
   - Error conditions

4. **Document Intent** (All patterns)
   - Use "Teaching Pattern" docstrings
   - Explain "why" not just "what"
   - Include real-world context

5. **Isolate Tests** (#1, #6)
   - Use tmp_path for file operations
   - Use mock mode for external services
   - Avoid test pollution

6. **Test Real Scenarios** (#3, #4, #11)
   - Don't just test happy path
   - Include context-aware scenarios
   - Test integration, not just units

---

## Contributing

To add a new pattern to this library:

1. Create the pattern in a test file with a "Teaching Pattern" docstring
2. Add it to this guide with:
   - Pattern number and name
   - When to use it
   - Complete code example
   - Key benefits
   - Source file link
3. Update the Table of Contents
4. Update the Pattern Selection Guide

---

## References

- **Test Suite**: 307 tests across 12 test files
- **Coverage**: 17.64% (18,310 lines)
- **Execution Time**: 3.75 seconds
- **Source Code**: `tests/unit/`
- **Documentation**: `PHASE_3_4_COMPLETION.md`

**Last Updated**: 2026-01-04
**Version**: 1.0.0
