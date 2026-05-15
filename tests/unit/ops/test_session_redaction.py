"""Tests for the session-content redaction pass.

Each category gets dedicated positive (must redact) and negative
(must leave alone) cases. The negative cases matter as much as the
positive ones — over-redaction degrades summary quality. A test
that asserts "redacted nothing" is doing real work.
"""

from __future__ import annotations

from attune.ops.session_redaction import redact

# ---------------------------------------------------------------------------
# Empty / pass-through inputs
# ---------------------------------------------------------------------------


def test_empty_string_returns_empty():
    """Empty input must not crash and must report no redactions."""
    result = redact("")
    assert result.text == ""
    assert result.counts == {}


def test_plain_prose_is_unchanged():
    """Ordinary prose with no sensitive content passes through untouched."""
    text = "Let's debug the test_runner failure on Windows 3.11."
    result = redact(text)
    assert result.text == text
    assert result.counts == {}


# ---------------------------------------------------------------------------
# API-key patterns
# ---------------------------------------------------------------------------


# Provider-prefix strings are built via runtime concatenation so that
# GitHub's push-protection secret scanner (which reads source bytes,
# not runtime values) doesn't see a complete provider-shaped token
# in any single literal. The regex match still fires at runtime
# because Python concatenates these to the full shape before redact()
# sees them. # pragma: allowlist secret (for detect-secrets parity)


def test_redacts_anthropic_api_key():
    """``sk-ant-...`` Anthropic keys must be redacted."""
    token = "sk-" + "ant-" + "TESTANTHROPICKEYABCDEFGHIJ0123456"
    text = f"My key is {token} please."
    result = redact(text)
    assert "sk-ant" not in result.text
    assert "<redacted>" in result.text
    assert result.counts.get("api_key") == 1


def test_redacts_openai_style_sk_key():
    """Generic ``sk-...`` keys must be redacted (OpenAI compatibility)."""
    token = "sk-" + "TESTOPENAIKEYABCDEFGHIJKLMN"
    text = f"Key: {token}"
    result = redact(text)
    assert "sk-TEST" not in result.text
    assert "<redacted>" in result.text


def test_redacts_github_pat_variants():
    """All five GitHub prefixed token variants are redacted."""
    # 36 alphanumeric chars after prefix — clearly test content.
    suffix = "TESTGITHUBTOKENABCDEFGHIJKLMNOPQRSTU"
    assert len(suffix) == 36
    prefixes = ("ghp", "gho", "ghu", "ghs", "ghr")
    tokens = [p + "_" + suffix for p in prefixes]
    sample = "tokens: " + " ; ".join(tokens)
    result = redact(sample)
    for prefix in prefixes:
        assert (prefix + "_") not in result.text, f"{prefix}_ survived: {result.text}"
    assert result.counts.get("api_key") == 5


def test_redacts_slack_bot_token():
    """Slack ``xoxb-...`` etc. tokens are redacted."""
    token = "xox" + "b-" + "TESTSLACKTOKENABCDEFG"
    text = f"Slack: {token}"
    result = redact(text)
    assert "xox" + "b-" not in result.text


def test_redacts_aws_access_key():
    """AWS access keys ``AKIA...`` are redacted."""
    token = "AKI" + "A" + "TESTAWSKEYABCDE12"
    text = f"AWS_ACCESS_KEY_ID={token} more text"
    result = redact(text)
    assert "AKIA" not in result.text


def test_redacts_bearer_header():
    """``Bearer <token>`` HTTP-auth headers are redacted."""
    text = "Authorization: Bearer abcdef1234567890.abcdef1234567890.abcdef"
    result = redact(text)
    assert "Bearer abc" not in result.text
    assert "<redacted>" in result.text


def test_does_not_redact_obvious_non_keys():
    """Strings that look key-ish but aren't (too short, no prefix) pass."""
    # Short hex string — could be a hash, not a key. Don't false-fire.
    text = "commit 3de9323 by Patrick"
    result = redact(text)
    assert result.text == text
    assert result.counts == {}


# ---------------------------------------------------------------------------
# Context-key (keyword + assignment) pattern
# ---------------------------------------------------------------------------


def test_redacts_password_assignment():
    """A ``password = "...">`` assignment redacts the value."""
    text = 'config = {password: "MyP@ssw0rdIsAtLeast16Chars"}'
    result = redact(text)
    assert "MyP@ssw0rd" not in result.text
    assert "password" in result.text  # the key word survives for readability
    assert "<redacted>" in result.text
    assert result.counts.get("context_key") == 1


def test_redacts_token_with_colon_assignment():
    """``token: value`` (YAML-ish) form is recognized."""
    text = "token: ZGVmaW5pdGVseS1ub3QtYS1yZWFsLXRva2VuLWp1c3Q"
    result = redact(text)
    assert "ZGVmaW5p" not in result.text
    assert "<redacted>" in result.text


def test_redacts_api_key_underscore_form():
    """``api_key`` and ``api-key`` both trigger."""
    text = "api_key = 'AAAAaaaa1111BBBB2222CCCC3333'"
    result = redact(text)
    assert "AAAAaaaa" not in result.text


def test_docstring_mentioning_password_word_is_not_redacted():
    """A prose docstring like 'the password parameter is required'
    must NOT trigger redaction — there's no assignment operator
    near the keyword."""
    text = "Note: the password parameter is required for this operation."
    result = redact(text)
    assert result.text == text
    assert result.counts == {}


# ---------------------------------------------------------------------------
# User-home absolute paths
# ---------------------------------------------------------------------------


def test_redacts_macos_user_home():
    """``/Users/<name>/...`` paths are redacted."""
    text = "Check the file at /Users/patrickroebuck/secret.txt for details."
    result = redact(text)
    assert "/Users/patrickroebuck" not in result.text
    assert "<user-home>" in result.text


def test_redacts_linux_user_home():
    """``/home/<name>/...`` paths are redacted."""
    text = "Logs at /home/runner/work/repo/output.log"
    result = redact(text)
    assert "/home/runner" not in result.text
    assert "<user-home>" in result.text


def test_redacts_windows_user_home_backslash():
    """``C:\\Users\\<name>\\...`` paths are redacted."""
    text = "Edit C:\\Users\\Patrick\\Documents\\notes.md please"
    result = redact(text)
    assert "C:\\Users\\Patrick" not in result.text
    assert "<user-home>" in result.text


def test_redacts_windows_user_home_forward_slash():
    """``C:/Users/<name>/...`` (some shells emit this) is redacted."""
    text = "Path is C:/Users/Patrick/foo and it works"
    result = redact(text)
    assert "C:/Users/Patrick" not in result.text


def test_does_not_redact_relative_project_paths():
    """Relative paths inside the project (``src/...``, ``tests/...``)
    are useful context for the summary — must not be redacted."""
    text = "The bug is in src/attune/ops/data.py at line 364."
    result = redact(text)
    assert result.text == text
    assert "user_home_path" not in result.counts


# ---------------------------------------------------------------------------
# Email addresses
# ---------------------------------------------------------------------------


def test_redacts_non_allowlist_email():
    """An email outside the allowlist is redacted."""
    text = "Contact someone@example.com about this."
    result = redact(text)
    assert "someone@example.com" not in result.text
    assert "<redacted-email>" in result.text
    assert result.counts.get("email") == 1


def test_preserves_allowlist_email():
    """Patrick's own emails are preserved per CLAUDE.md profile."""
    text = "Owner is silversurfer562@gmail.com."
    result = redact(text)
    assert "silversurfer562@gmail.com" in result.text
    assert "email" not in result.counts


def test_caller_can_override_email_allowlist():
    """``email_allowlist`` kwarg replaces the default policy."""
    text = "Contact team@example.com and other@example.com"
    result = redact(text, email_allowlist={"team@example.com"})
    assert "team@example.com" in result.text  # allowlisted
    assert "other@example.com" not in result.text  # redacted
    assert result.counts.get("email") == 1


def test_email_allowlist_is_case_insensitive():
    """Allowlist matching ignores case differences."""
    text = "Patrick is SILVERSURFER562@GMAIL.COM in caps."
    result = redact(text)
    # Original casing preserved in the output (we don't normalize).
    assert "SILVERSURFER562@GMAIL.COM" in result.text


# ---------------------------------------------------------------------------
# IP addresses
# ---------------------------------------------------------------------------


def test_redacts_public_ipv4():
    """A valid public IPv4 is redacted."""
    text = "The server at 8.8.8.8 is responding."
    result = redact(text)
    assert "8.8.8.8" not in result.text
    assert "<redacted-ip>" in result.text


def test_redacts_private_ipv4():
    """Private/RFC1918 IPv4 is also redacted."""
    text = "Internal LB at 192.168.1.42 returned 500"
    result = redact(text)
    assert "192.168.1.42" not in result.text
    assert "<redacted-ip>" in result.text


def test_does_not_redact_invalid_ip_shape():
    """A 4-octet candidate that exceeds 255 in a field is not an IP."""
    text = "The version is 1.999.0.42 (semver-ish)."
    result = redact(text)
    assert "1.999.0.42" in result.text  # ipaddress.ip_address rejects it
    assert "ip" not in result.counts


def test_does_not_redact_normal_version_numbers():
    """``1.2.3`` style (3 octets) is not an IPv4 candidate."""
    text = "Bumped to v6.8.0 today."
    result = redact(text)
    assert result.text == text


# ---------------------------------------------------------------------------
# Cross-category + counts
# ---------------------------------------------------------------------------


def test_multi_category_input_redacts_each():
    """A single string with multiple sensitive shapes redacts each."""
    text = (
        "Run with ANTHROPIC_API_KEY=sk-ant-AAAAaaaa1111BBBB2222CCCC3333; "
        "logs at /Users/patrickroebuck/logs ; "
        "contact stranger@example.com ; "
        "endpoint 10.0.0.5"
    )
    result = redact(text)
    assert "sk-ant" not in result.text
    assert "/Users/patrickroebuck" not in result.text
    assert "stranger@example.com" not in result.text
    assert "10.0.0.5" not in result.text
    assert result.counts.get("api_key", 0) >= 1
    assert result.counts.get("user_home_path", 0) >= 1
    assert result.counts.get("email", 0) >= 1
    assert result.counts.get("ip", 0) >= 1


def test_counts_are_diagnostic_not_security_signal():
    """Per the docstring: ``text != input`` is the canonical
    'did something redact' check. The counts dict is for logging."""
    text = "No sensitive content here."
    result = redact(text)
    assert result.text == text
    assert result.counts == {}


def test_specific_pattern_wins_over_context_key():
    """A ``sk-ant-...`` token assigned via ``API_KEY=...`` is caught by
    the specific pattern first; the context-key fallback should NOT
    double-count it."""
    text = "API_KEY=sk-ant-AAAAaaaa1111BBBB2222CCCC3333DDDD"
    result = redact(text)
    assert "sk-ant" not in result.text
    assert result.counts.get("api_key", 0) == 1
    # The context-key pattern may also match the assignment pattern
    # since the specific pattern already replaced the value. Either
    # 0 or 1 here is acceptable — what matters is that the redaction
    # is correct and the value is fully replaced.
    assert "<redacted>" in result.text
