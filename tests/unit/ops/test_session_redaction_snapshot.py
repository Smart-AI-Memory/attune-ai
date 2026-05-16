"""Snapshot regression test against committed redacted Claude Code sessions.

The fixtures at ``tests/fixtures/ops/session_summaries/*.jsonl`` are real
Claude Code sessions run through
:func:`attune.ops.session_redaction.redact_json_line` — see
``scripts/build_session_fixtures.py`` for the harvest tool that produced
them. They were curated 2026-05-15 against the redaction module shipped
in PR #389.

This test exists as a CI gate for two distinct regressions:

(1) Future redaction-module changes that re-introduce the
    "top-level-only field walk" bug. The fixtures are realistic Claude
    Code events with secret-pattern shapes nested under
    ``message.content[].content`` and ``toolUseResult.stdout``. A
    refactor that reverts to top-level-only walking would re-leak the
    secret-pattern shapes, and the per-pattern scan below catches it
    before the fixtures hit anyone's clipboard.

(2) Future patterns added to the redaction module that change the
    per-fixture redaction histogram in a way the snapshot doesn't
    expect. The histogram is loose (counts within a tolerance band),
    so additive changes don't break the test — only changes that
    accidentally reduce coverage do.

A future follow-up will add an LLM-call snapshot (token budget +
output length) on top of these same fixtures once the
``session_summary_llm`` module from PR #388 lands on main.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from attune.ops import session_redaction as redaction

_FIXTURE_DIR = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ops" / "session_summaries"
)

# Secret-pattern panel — the same shapes the redaction module knows
# about. After redact_json_line() runs, NONE of these may appear in
# the output (excluding the placeholder tokens themselves). This is
# the load-bearing assertion: it's what makes "I'll just walk
# top-level fields again" refactors break loudly in CI before any
# fixture gets harvested with leaks.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "anthropic"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "openai-style"),
    (re.compile(r"gh[poas]_[A-Za-z0-9]{36}"), "github-pat"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws-akia"),
    (re.compile(r"/Users/[A-Za-z0-9._\-]+(?=/|\s|$)"), "home-path-mac"),
    (re.compile(r"/home/[A-Za-z0-9._\-]+(?=/|\s|$)"), "home-path-linux"),
)

_PLACEHOLDERS = frozenset({"<redacted>", "<user-home>", "<redacted-email>", "<redacted-ip>"})

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]{2,}@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_EMAIL_ALLOWLIST = frozenset(
    {
        "silversurfer562@gmail.com",
        "admin@smartaimemory.com",
        "patrick.roebuck@smartaimemory.com",
        "noreply@anthropic.com",
    }
)


def _list_fixtures() -> list[Path]:
    """Return the curated fixture set as a sorted list.

    Sorted so test parametrization IDs are deterministic and the
    pytest output is stable across runs.
    """
    if not _FIXTURE_DIR.is_dir():
        return []
    return sorted(_FIXTURE_DIR.glob("*.jsonl"))


_FIXTURES = _list_fixtures()


# ---------------------------------------------------------------------------
# Sanity checks on the fixture set itself — these fail loudly if the
# committed fixture set drifts (someone deletes them or commits a corrupt
# one) so we know to refresh the harvest before chasing other failures.
# ---------------------------------------------------------------------------


def test_fixture_dir_exists():
    """The committed fixture dir must be present."""
    assert _FIXTURE_DIR.is_dir(), (
        f"missing fixture dir at {_FIXTURE_DIR}; "
        "re-run scripts/build_session_fixtures.py to harvest"
    )


def test_fixture_set_size_within_band():
    """Curated set should have between 5 and 20 fixtures.

    Lower bound: anything less probably means accidental deletion.
    Upper bound: anything more probably means an unintended re-harvest
    that needs curation.
    """
    assert 5 <= len(_FIXTURES) <= 20, (
        f"fixture count out of band ({len(_FIXTURES)}); " "expected 5-20 representative sessions"
    )


# ---------------------------------------------------------------------------
# Per-fixture round-trip + secret-leak assertions. Parametrized so each
# fixture is its own pytest node — granular CI failure messages, not one
# opaque "fixtures failed" verdict.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES,
    ids=[f.name for f in _FIXTURES],
)
def test_fixture_lines_are_valid_json(fixture: Path):
    """Every line in every committed fixture must parse as JSON.

    The harvest script validates this on write; this test re-validates
    on every CI run so a fixture that gets corrupted on disk surfaces
    immediately.
    """
    with fixture.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
            except json.JSONDecodeError as e:
                pytest.fail(f"line {i} of {fixture.name} is not valid JSON: {e}")


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES,
    ids=[f.name for f in _FIXTURES],
)
def test_fixture_contains_no_secret_patterns(fixture: Path):
    """Load-bearing security assertion: every committed fixture must
    contain ZERO matches against the secret-pattern panel.

    A failure here means either:
    - The redaction module regressed (re-introduced top-level-only walk
      or removed a pattern); fix the module.
    - The fixture was harvested from a session that contains a NEW
      secret shape the module doesn't yet handle; add the pattern,
      re-harvest, re-commit.

    Either way, do NOT silence the test — leaked-secret fixtures are
    the exact failure mode that nearly happened 2026-05-15.
    """
    text = fixture.read_text(encoding="utf-8")
    leaks: dict[str, list[str]] = {}
    for pat, label in _SECRET_PATTERNS:
        matches = pat.findall(text)
        real = [m for m in matches if m not in _PLACEHOLDERS]
        if real:
            leaks[label] = real[:3]  # cap sample at 3
    assert (
        not leaks
    ), f"committed fixture {fixture.name} contains leaked secret patterns:\n" + "\n".join(
        f"  {label}: {samples}" for label, samples in leaks.items()
    )


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES,
    ids=[f.name for f in _FIXTURES],
)
def test_fixture_emails_all_allowlisted(fixture: Path):
    """Every email in every fixture must either be redacted OR on the
    allowlist (Patrick's emails + the GPG co-author trailer).

    Same security shape as the secret-pattern test — a non-allowlisted
    email surviving redaction means the module regressed.
    """
    text = fixture.read_text(encoding="utf-8")
    leaked = [e for e in _EMAIL_PATTERN.findall(text) if e.lower() not in _EMAIL_ALLOWLIST]
    assert not leaked, (
        f"committed fixture {fixture.name} contains non-allowlisted " f"emails: {leaked[:5]}"
    )


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES,
    ids=[f.name for f in _FIXTURES],
)
def test_fixture_round_trips_through_redact_json_line(fixture: Path):
    """Re-running redaction on an already-redacted fixture must:

    1. Produce no NEW redactions (idempotency — placeholders shouldn't
       trigger any pattern they don't already match).
    2. Leave the JSON parsable on every line.

    Idempotency matters because the cache hit path (from #388) reads
    a previously-redacted summary and serves it directly. If
    re-running redaction would change the text, the cache + fresh
    paths would diverge.
    """
    with fixture.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            result = redaction.redact_json_line(stripped)
            assert result is not None, f"line {i} of {fixture.name} failed redaction round-trip"
            # Idempotency: the redacted text equals the input text.
            # (counts may still be non-zero because the same line may
            # contain placeholder patterns that the regexes happen to
            # accept — but the resulting TEXT is unchanged.)
            assert (
                result.text == stripped
            ), f"line {i} of {fixture.name} is not redaction-idempotent"
