"""Behavioral + mutation-resistant tests for long_term_classification.

Covers the two pure-logic functions extracted from long_term.py:

- ``classify_pattern(content, type)`` — precedence-ordered heuristics
  mapping content keywords and pattern types to a Classification level.
- ``check_access(user, classification, metadata)`` — access rules per
  classification, including the workspace-scoping and legacy-fallback
  edges.

Design notes (why these assertions, not coverage padding):

- Every keyword/type list is parametrized so a deleted list element is
  caught (mutmut "remove from collection" survivors).
- Exact-equality assertions on the returned Classification kill
  return-value mutants (SENSITIVE -> INTERNAL, etc.).
- Dedicated *precedence* tests (a higher-priority signal must win when a
  lower-priority one is also present) kill branch-reordering and
  branch-deletion mutants that line coverage alone cannot.
- The workspace ``and`` chain and ``!=`` comparison in check_access are
  exercised from both sides so the comparison-operator and
  short-circuit mutants die.
"""

import pytest

from attune.memory.long_term_classification import (
    FINANCIAL_KEYWORDS,
    HEALTHCARE_KEYWORDS,
    INTERNAL_PATTERN_TYPES,
    PROPRIETARY_KEYWORDS,
    SENSITIVE_PATTERN_TYPES,
    check_access,
    classify_pattern,
)
from attune.memory.long_term_types import Classification

# ===========================================================================
# classify_pattern — keyword-driven classification
# ===========================================================================


@pytest.mark.parametrize("keyword", HEALTHCARE_KEYWORDS)
def test_classify_each_healthcare_keyword_is_sensitive(keyword):
    """Every healthcare keyword, alone, classifies as SENSITIVE."""
    assert classify_pattern(f"note about {keyword} here", "general") == (Classification.SENSITIVE)


@pytest.mark.parametrize("keyword", FINANCIAL_KEYWORDS)
def test_classify_each_financial_keyword_is_sensitive(keyword):
    """Every financial keyword, alone, classifies as SENSITIVE."""
    assert classify_pattern(f"record of {keyword} today", "general") == (Classification.SENSITIVE)


@pytest.mark.parametrize("keyword", PROPRIETARY_KEYWORDS)
def test_classify_each_proprietary_keyword_is_internal(keyword):
    """Every proprietary keyword, alone, classifies as INTERNAL."""
    assert classify_pattern(f"this is {keyword} material", "general") == (Classification.INTERNAL)


@pytest.mark.parametrize("ptype", SENSITIVE_PATTERN_TYPES)
def test_classify_each_sensitive_pattern_type(ptype):
    """Sensitive pattern types classify SENSITIVE on neutral content."""
    assert classify_pattern("neutral content", ptype) == Classification.SENSITIVE


@pytest.mark.parametrize("ptype", INTERNAL_PATTERN_TYPES)
def test_classify_each_internal_pattern_type(ptype):
    """Internal pattern types classify INTERNAL on neutral content."""
    assert classify_pattern("neutral content", ptype) == Classification.INTERNAL


def test_classify_neutral_content_and_type_is_public():
    """No signal in content or type defaults to PUBLIC."""
    assert classify_pattern("the quick brown fox", "general") == Classification.PUBLIC


def test_classify_empty_inputs_is_public():
    """Empty content and type default to PUBLIC (no false positive)."""
    assert classify_pattern("", "") == Classification.PUBLIC


def test_classify_is_case_insensitive():
    """Uppercase content still matches — guards the .lower() normalization."""
    assert classify_pattern("PATIENT INTAKE FORM", "general") == (Classification.SENSITIVE)


def test_classify_matches_keyword_as_substring():
    """Keywords match as substrings (documents the `in` semantics)."""
    # "patient" inside "patients"
    assert classify_pattern("two patients arrived", "general") == (Classification.SENSITIVE)


# ---- Precedence (the high-value mutation kills) ---------------------------


def test_healthcare_beats_proprietary_content():
    """Healthcare (SENSITIVE) outranks proprietary (INTERNAL) content."""
    content = "confidential patient diagnosis"  # proprietary + healthcare
    assert classify_pattern(content, "general") == Classification.SENSITIVE


def test_financial_content_beats_internal_pattern_type():
    """Financial content (SENSITIVE) outranks an INTERNAL pattern type."""
    # type "architecture" alone -> INTERNAL; financial content lifts it.
    assert classify_pattern("payment failed", "architecture") == (Classification.SENSITIVE)


def test_sensitive_pattern_type_beats_proprietary_content():
    """A SENSITIVE pattern type outranks proprietary content (INTERNAL)."""
    # content "confidential" -> INTERNAL; sensitive type checked first.
    assert classify_pattern("confidential notes", "clinical_protocol") == (Classification.SENSITIVE)


def test_proprietary_content_beats_internal_pattern_type_noop():
    """Proprietary content and INTERNAL type agree -> INTERNAL.

    Both paths yield INTERNAL; asserts the INTERNAL branch returns the
    right level rather than falling through to PUBLIC.
    """
    assert classify_pattern("internal trade secret", "business_logic") == (Classification.INTERNAL)


# ===========================================================================
# check_access — PUBLIC
# ===========================================================================


def test_public_grants_access_to_anyone():
    """PUBLIC patterns are accessible regardless of user or metadata."""
    assert check_access("alice", Classification.PUBLIC, {}) is True


def test_public_ignores_workspace_mismatch():
    """PUBLIC access is unconditional — workspace fields are irrelevant."""
    meta = {"workspace": "a", "current_workspace": "b", "created_by": "bob"}
    assert check_access("alice", Classification.PUBLIC, meta) is True


# ===========================================================================
# check_access — INTERNAL (workspace scoping + legacy fallback)
# ===========================================================================


def test_internal_same_workspace_grants_access():
    """INTERNAL access granted when workspaces match."""
    meta = {"workspace": "proj-x", "current_workspace": "proj-x"}
    assert check_access("alice", Classification.INTERNAL, meta) is True


def test_internal_different_workspace_denies_access():
    """INTERNAL access denied across distinct workspaces (kills != -> ==)."""
    meta = {"workspace": "proj-x", "current_workspace": "proj-y"}
    assert check_access("alice", Classification.INTERNAL, meta) is False


def test_internal_missing_both_workspaces_grants_legacy_access():
    """Legacy patterns with no workspace metadata stay accessible."""
    assert check_access("alice", Classification.INTERNAL, {}) is True


def test_internal_only_pattern_workspace_present_grants_access():
    """Only one workspace field set -> the `and` chain short-circuits open."""
    meta = {"workspace": "proj-x"}  # no current_workspace
    assert check_access("alice", Classification.INTERNAL, meta) is True


def test_internal_only_current_workspace_present_grants_access():
    """Symmetric: current set, pattern workspace absent -> access granted."""
    meta = {"current_workspace": "proj-y"}  # no workspace
    assert check_access("alice", Classification.INTERNAL, meta) is True


# ===========================================================================
# check_access — SENSITIVE (creator-only)
# ===========================================================================


def test_sensitive_creator_gets_access():
    """SENSITIVE patterns are accessible to their creator."""
    meta = {"created_by": "alice"}
    assert check_access("alice", Classification.SENSITIVE, meta) is True


def test_sensitive_non_creator_denied():
    """SENSITIVE patterns deny non-creators (kills == -> != on identity)."""
    meta = {"created_by": "alice"}
    assert check_access("mallory", Classification.SENSITIVE, meta) is False


def test_sensitive_missing_creator_denies_named_user():
    """No created_by -> a named user is denied (created_by defaults to '')."""
    assert check_access("alice", Classification.SENSITIVE, {}) is False


def test_sensitive_empty_user_matches_absent_creator_edge():
    """Documented edge: anonymous user ('') matches absent creator ('').

    This pins the current behavior so a future change to it is a
    deliberate, visible decision rather than an accident.
    """
    assert check_access("", Classification.SENSITIVE, {}) is True


def test_sensitive_returns_real_bool():
    """Return is a genuine bool, not a truthy string (guards bool() wrap)."""
    result = check_access("alice", Classification.SENSITIVE, {"created_by": "alice"})
    assert result is True
    assert isinstance(result, bool)
