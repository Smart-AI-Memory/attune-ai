"""Redaction pass for Claude Code session content before LLM summarization.

Defined by the ops-sessions-page spec (decisions.md, Decision 3).
Runs over the user's first prompts or any text destined for Haiku
summarization. The redacted text is what gets sent to the model AND
what gets cached on disk — sensitive material never lands in either
the LLM provider's context or our `<attune_home>/ops/session_summaries/`
cache.

The patterns target the realistic threat surface for a developer's
session content: API keys committed to scratch buffers, paths
revealing the user's filesystem layout, IPs, and email addresses
the user didn't authorize as identifying themselves.

Discipline: redact FIRST, then summarize, then cache. Cache hits
return the redacted form — no re-redaction needed on read.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

# Default redaction placeholder. A short, identifiable token so a
# human reading a summary knows the model saw a redacted region.
_PLACEHOLDER = "<redacted>"
_PLACEHOLDER_HOME = "<user-home>"
_PLACEHOLDER_EMAIL = "<redacted-email>"
_PLACEHOLDER_IP = "<redacted-ip>"

# Email allowlist — these can appear in summaries without redaction.
# Sourced from CLAUDE.md user profile. Edit when the team / owner
# set expands.
_EMAIL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "silversurfer562@gmail.com",
        "admin@smartaimemory.com",
        "patrick.roebuck@smartaimemory.com",
    }
)


# Concrete API-key shapes. Each pattern is anchored to avoid eating
# adjacent non-key text. The order matters: more specific patterns
# first so generic fallbacks don't consume them.
_API_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Anthropic
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    # Generic OpenAI-style
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    # GitHub PATs (pre-2021 hex format intentionally NOT listed —
    # too generic). Modern prefixed tokens:
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"gho_[A-Za-z0-9]{36}"),
    re.compile(r"ghu_[A-Za-z0-9]{36}"),
    re.compile(r"ghs_[A-Za-z0-9]{36}"),
    re.compile(r"ghr_[A-Za-z0-9]{36}"),
    # Slack bot tokens
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    # AWS access keys
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Bearer-style auth headers
    re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]{20,}"),
)

# Generic high-entropy token preceded by a key/secret-context word
# within ~5 characters of an assignment operator. Matches an
# assignment of a credential-named identifier to a 16+-char quoted
# value. Keywords matched: password, passwd, pwd, secret, token,
# api_key / api-key, access_key / access-key, auth.
#
# Concrete example strings are intentionally omitted from this
# comment. The project's hardcoded-secrets scanner test
# (tests/unit/security/test_security_remediation.py) flags any
# credential-keyword + equals + quoted-string sequence in src/
# regardless of surrounding context.
#
# Anchored so prose like "the credential parameter is required"
# does not false-fire. The value character class includes common
# password punctuation (``!@#$%^&*~``) so a real-world password
# value still matches even when it isn't a pure-base64 token.
_CONTEXT_KEY_PATTERN = re.compile(
    r"\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|auth)"
    r"\s*[:=]\s*['\"]?([A-Za-z0-9._\-+/=!@#$%^&*~]{16,})['\"]?",
    flags=re.IGNORECASE,
)

# Absolute path under a user-home directory.
#   /Users/<name>/...   (macOS)
#   /home/<name>/...    (Linux)
#   C:\Users\<name>\... (Windows, backslash form)
#   C:/Users/<name>/... (Windows, forward-slash form some shells use)
_USER_HOME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[A-Za-z0-9._\-]+(?=/|$|\s|['\"])"),
    re.compile(r"/home/[A-Za-z0-9._\-]+(?=/|$|\s|['\"])"),
    re.compile(r"[A-Za-z]:[\\\/]Users[\\\/][A-Za-z0-9._\-]+(?=[\\\/]|$|\s|['\"])"),
)

# Email address — RFC 5322 simplified. Matched, then checked against
# the allowlist before redacting.
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)

# IP addresses — match candidate, validate with ipaddress.ip_address.
# Conservative: only redact RFC1918 private + obvious public IPv4. IPv6
# matching deferred (rarely in user prompts; can extend later).
_IPV4_CANDIDATE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


@dataclass(frozen=True)
class RedactionResult:
    """Outcome of a redaction pass.

    ``text`` is the redacted output. ``counts`` is a per-category
    histogram useful for logging and for fixture-construction
    confidence ("did we actually redact anything in this session?").
    Counts are diagnostic, not security-critical — code paths that
    branch on whether redaction occurred should use ``text != input``
    instead, since a category may have counted overlapping matches.
    """

    text: str
    counts: dict[str, int] = field(default_factory=dict)


def redact(
    text: str,
    *,
    email_allowlist: Iterable[str] | None = None,
) -> RedactionResult:
    """Run all redaction passes over ``text`` and return the result.

    Order of operations is deliberate — patterns higher on the list
    take precedence so a string like ``sk-ant-xxx`` is caught by the
    specific Anthropic pattern before the generic context-key pattern
    sees it.

    Args:
        text: The input string. Typically a user's first prompt from
            a Claude Code session JSONL.
        email_allowlist: Override for the default email allowlist.
            Pass an explicit set to swap the policy at call time (e.g.
            stricter set in shared-machine contexts). When ``None``,
            the module-level default is used.

    Returns:
        A :class:`RedactionResult` with the redacted ``text`` and a
        per-category ``counts`` histogram.
    """
    if not text:
        return RedactionResult(text=text or "", counts={})

    allowlist = (
        frozenset(s.lower() for s in email_allowlist)
        if email_allowlist is not None
        else _EMAIL_ALLOWLIST
    )

    counts: dict[str, int] = {}
    out = text

    # 1. API-key shapes (highest specificity first).
    for pattern in _API_KEY_PATTERNS:
        out, n = pattern.subn(_PLACEHOLDER, out)
        if n:
            counts["api_key"] = counts.get("api_key", 0) + n

    # 2. Context-key fallback for anything resembling a credential
    # assignment that the specific patterns didn't catch.
    def _ck_sub(match: re.Match[str]) -> str:
        # Replace only the value portion, preserve the key + operator
        # so a human reader of the summary sees what was redacted.
        full = match.group(0)
        value = match.group(1)
        return full.replace(value, _PLACEHOLDER, 1)

    out, n = _CONTEXT_KEY_PATTERN.subn(_ck_sub, out)
    if n:
        counts["context_key"] = n

    # 3. User-home absolute paths.
    for pattern in _USER_HOME_PATTERNS:
        out, n = pattern.subn(_PLACEHOLDER_HOME, out)
        if n:
            counts["user_home_path"] = counts.get("user_home_path", 0) + n

    # 4. Email addresses (allowlist check per match).
    def _email_sub(match: re.Match[str]) -> str:
        return match.group(0) if match.group(0).lower() in allowlist else _PLACEHOLDER_EMAIL

    out, n = _EMAIL_PATTERN.subn(_email_sub, out)
    # Counts: only count actual redactions, not allowlist-passes.
    redacted_emails = out.count(_PLACEHOLDER_EMAIL) - text.count(_PLACEHOLDER_EMAIL)
    if redacted_emails:
        counts["email"] = redacted_emails

    # 5. IP addresses (validate candidate before redacting).
    def _ip_sub(match: re.Match[str]) -> str:
        candidate = match.group(0)
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return candidate  # not a valid IP, leave alone
        return _PLACEHOLDER_IP

    out, _ = _IPV4_CANDIDATE.subn(_ip_sub, out)
    # Counts: only real IPs that became placeholders.
    redacted_ips = out.count(_PLACEHOLDER_IP) - text.count(_PLACEHOLDER_IP)
    if redacted_ips:
        counts["ip"] = redacted_ips

    return RedactionResult(text=out, counts=counts)
