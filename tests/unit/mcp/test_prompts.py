"""Unit tests for attune.mcp.prompts module.

Tests cover:
- get_prompt_list returns values from prompts dict
- get_prompt_messages raises ValueError for unknown prompts
- get_prompt_messages returns correct messages for security-scan
- get_prompt_messages returns correct messages for test-gen (batch and non-batch)
- get_prompt_messages returns correct messages for cost-report

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.mcp.prompts import get_prompt_list, get_prompt_messages

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PROMPTS: dict = {
    "security-scan": {
        "name": "security-scan",
        "description": "Run security scan",
        "arguments": [{"name": "path", "required": False}],
    },
    "test-gen": {
        "name": "test-gen",
        "description": "Generate tests",
        "arguments": [{"name": "module", "required": False}],
    },
    "cost-report": {
        "name": "cost-report",
        "description": "Cost report",
        "arguments": [{"name": "days", "required": False}],
    },
}


@pytest.mark.unit
class TestGetPromptList:
    """Tests for get_prompt_list function."""

    def test_get_prompt_list_returns_list(self) -> None:
        """Test that get_prompt_list returns a list."""
        result = get_prompt_list(SAMPLE_PROMPTS)
        assert isinstance(result, list)

    def test_get_prompt_list_length_matches_prompts(self) -> None:
        """Test that list length equals number of prompt entries."""
        result = get_prompt_list(SAMPLE_PROMPTS)
        assert len(result) == len(SAMPLE_PROMPTS)

    def test_get_prompt_list_contains_all_values(self) -> None:
        """Test that all values from the prompts dict are included."""
        result = get_prompt_list(SAMPLE_PROMPTS)
        for value in SAMPLE_PROMPTS.values():
            assert value in result

    def test_get_prompt_list_empty_dict_returns_empty_list(self) -> None:
        """Test that an empty prompts dict returns an empty list."""
        result = get_prompt_list({})
        assert result == []

    def test_get_prompt_list_single_entry(self) -> None:
        """Test with a single-entry prompts dict."""
        single = {"foo": {"name": "foo"}}
        result = get_prompt_list(single)
        assert result == [{"name": "foo"}]


@pytest.mark.unit
class TestGetPromptMessagesUnknownPrompt:
    """Tests for get_prompt_messages with unknown prompt names."""

    def test_unknown_prompt_not_in_dict_raises_value_error(self) -> None:
        """Test that a prompt name not in prompts dict raises ValueError."""
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            get_prompt_messages(SAMPLE_PROMPTS, "nonexistent", {})

    def test_unknown_prompt_error_message_contains_name(self) -> None:
        """Test that the error message includes the unknown prompt name."""
        with pytest.raises(ValueError, match="bad-name"):
            get_prompt_messages(SAMPLE_PROMPTS, "bad-name", {})

    def test_empty_prompts_dict_always_raises(self) -> None:
        """Test that an empty prompts dict raises for any name."""
        with pytest.raises(ValueError):
            get_prompt_messages({}, "security-scan", {})


@pytest.mark.unit
class TestGetPromptMessagesSecurityScan:
    """Tests for get_prompt_messages with 'security-scan' prompt."""

    def test_security_scan_returns_list(self) -> None:
        """Test that security-scan returns a list."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        assert isinstance(result, list)

    def test_security_scan_returns_one_message(self) -> None:
        """Test that security-scan returns exactly one message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        assert len(result) == 1

    def test_security_scan_default_path_is_src(self) -> None:
        """Test that the default path is 'src/' when no path argument is given."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        message_text = result[0]["content"]["text"]
        assert "src/" in message_text

    def test_security_scan_custom_path_in_message(self) -> None:
        """Test that the provided path appears in the message text."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {"path": "mydir/"})
        message_text = result[0]["content"]["text"]
        assert "mydir/" in message_text

    def test_security_scan_message_has_role_user(self) -> None:
        """Test that the returned message has role 'user'."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        assert result[0]["role"] == "user"

    def test_security_scan_message_content_type_is_text(self) -> None:
        """Test that the message content type is 'text'."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        assert result[0]["content"]["type"] == "text"

    def test_security_scan_message_mentions_eval_exec(self) -> None:
        """Test that the message mentions eval/exec security checks."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "security-scan", {})
        message_text = result[0]["content"]["text"]
        assert "eval" in message_text or "exec" in message_text


@pytest.mark.unit
class TestGetPromptMessagesTestGen:
    """Tests for get_prompt_messages with 'test-gen' prompt."""

    def test_test_gen_non_batch_returns_list(self) -> None:
        """Test that test-gen (non-batch) returns a list."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {"module": "src/foo.py"})
        assert isinstance(result, list)

    def test_test_gen_non_batch_returns_one_message(self) -> None:
        """Test that test-gen (non-batch) returns exactly one message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {"module": "src/foo.py"})
        assert len(result) == 1

    def test_test_gen_non_batch_includes_module_in_message(self) -> None:
        """Test that the module name appears in the non-batch message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {"module": "src/mymodule.py"})
        message_text = result[0]["content"]["text"]
        assert "src/mymodule.py" in message_text

    def test_test_gen_batch_false_string_is_non_batch(self) -> None:
        """Test that batch='false' (string) is treated as non-batch."""
        result = get_prompt_messages(
            SAMPLE_PROMPTS, "test-gen", {"batch": "false", "module": "src/mod.py"}
        )
        message_text = result[0]["content"]["text"]
        # non-batch message references the module path
        assert "src/mod.py" in message_text

    def test_test_gen_batch_true_string_is_batch_mode(self) -> None:
        """Test that batch='true' (string) triggers batch mode message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {"batch": "true"})
        message_text = result[0]["content"]["text"]
        assert "batch" in message_text.lower()

    def test_test_gen_batch_true_uppercase_is_batch_mode(self) -> None:
        """Test that batch='True' (capitalized) triggers batch mode."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {"batch": "True"})
        message_text = result[0]["content"]["text"]
        assert "batch" in message_text.lower()

    def test_test_gen_batch_mode_does_not_include_module_path(self) -> None:
        """Test that batch mode message does not mention a specific module path."""
        result = get_prompt_messages(
            SAMPLE_PROMPTS, "test-gen", {"batch": "true", "module": "src/foo.py"}
        )
        message_text = result[0]["content"]["text"]
        # batch message is generic, not module-specific
        assert "src/foo.py" not in message_text

    def test_test_gen_message_role_is_user(self) -> None:
        """Test that the message role is 'user'."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {})
        assert result[0]["role"] == "user"

    def test_test_gen_default_module_is_empty_string(self) -> None:
        """Test that missing module argument defaults to empty string."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "test-gen", {})
        # Should not raise; module defaults to ""
        assert isinstance(result, list)


@pytest.mark.unit
class TestGetPromptMessagesCostReport:
    """Tests for get_prompt_messages with 'cost-report' prompt."""

    def test_cost_report_returns_list(self) -> None:
        """Test that cost-report returns a list."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {})
        assert isinstance(result, list)

    def test_cost_report_returns_one_message(self) -> None:
        """Test that cost-report returns exactly one message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {})
        assert len(result) == 1

    def test_cost_report_default_days_is_30(self) -> None:
        """Test that the default days value is 30 in the message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {})
        message_text = result[0]["content"]["text"]
        assert "30" in message_text

    def test_cost_report_custom_days_in_message(self) -> None:
        """Test that custom days value appears in the message."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {"days": "7"})
        message_text = result[0]["content"]["text"]
        assert "7" in message_text

    def test_cost_report_message_role_is_user(self) -> None:
        """Test that the message role is 'user'."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {})
        assert result[0]["role"] == "user"

    def test_cost_report_content_type_is_text(self) -> None:
        """Test that content type is 'text'."""
        result = get_prompt_messages(SAMPLE_PROMPTS, "cost-report", {})
        assert result[0]["content"]["type"] == "text"
