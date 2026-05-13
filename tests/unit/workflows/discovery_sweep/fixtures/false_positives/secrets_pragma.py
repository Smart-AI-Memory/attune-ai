"""False-positive fixture: pragma-allowlisted secret string.

detect-secrets and similar scanners flag the literal as a
hardcoded secret. The pragma comment is the documented escape
hatch.
"""

# Test credentials — never real.
TEST_API_KEY = "sk_live_FAKE_NOT_REAL_abc123"  # pragma: allowlist secret
