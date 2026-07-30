"""Smoke test pinning the polish wire-level model name.

Lives outside the broader polish test suite specifically to
catch the next model-change failure immediately. The polish model
is the *editing* model (ruled 2026-07-29 — Sonnet drafts, the
editing model edits): the default comes from
``attune.models.editing`` and is overridable via
``ATTUNE_MODEL_EDITING``. When the editing default is bumped
again, this test fires a clear "the wire contract is stale"
signal so the bump is mechanical.

The test mocks at ``attune.models.single_turn.call_api``
so no API tokens are spent.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.authoring.polish import _polish_model, polish_template

# The current editing-model default the codebase is pinned to. Update
# *both* this constant and editing._DEFAULT_EDITING_MODEL together
# when migrating; the co-located assertion catches half-migrations
# where someone bumps one and forgets the other.
_EXPECTED_MODEL = "claude-opus-5"


def test_polish_model_matches_expected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sentinel: the resolved polish model is the alias we expect.

    Failure mode: someone bumped the editing default in
    ``attune.models.editing`` without bumping ``_EXPECTED_MODEL``
    here. Update both together.
    """
    monkeypatch.delenv("ATTUNE_MODEL_EDITING", raising=False)
    assert _polish_model() == _EXPECTED_MODEL


def test_polish_model_respects_editing_env_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CI model pin must reach the polish path."""
    monkeypatch.setenv("ATTUNE_MODEL_EDITING", "claude-sonnet-5")
    assert _polish_model() == "claude-sonnet-5"


def test_polish_template_calls_sdk_with_expected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wire-contract test: the model passed to ``call_api``
    matches the resolved premium tier (and thus our expected alias).

    Pinning the wire-level call shape — not just the resolver —
    catches refactors that bypass the tier module or pin the
    model elsewhere in the call site.

    Forces a cache miss via patched ``_cache_get`` so the LLM
    call path always runs (otherwise on a hot polish cache the
    SDK never gets called).
    """
    monkeypatch.delenv("ATTUNE_MODEL_PREMIUM", raising=False)
    with patch("attune.authoring.polish._cache_get", return_value=None):
        with patch("attune.models.single_turn.call_api", return_value="polished body") as mock_call:
            with patch("attune.models.single_turn.get_client") as mock_client:
                mock_client.return_value = object()
                result = polish_template(
                    content="# Sample\n\nBody.\n",
                    feature_name="sample",
                    source_summary="def f(): pass",
                    template_type="concept",
                    strict=True,
                )

    # polish_template runs _sanitize_output, which may add a trailing newline.
    # Assert content rather than exact equality so the test isn't brittle.
    assert result.strip() == "polished body"
    mock_call.assert_called_once()
    kwargs = mock_call.call_args.kwargs
    assert kwargs["model"] == _EXPECTED_MODEL, (
        f"polish call went out with model={kwargs['model']!r}, "
        f"expected {_EXPECTED_MODEL!r}. If the premium tier was intentionally "
        "bumped, update _EXPECTED_MODEL in tests/test_polish_smoke.py."
    )


def test_polish_template_env_pin_flows_to_sdk_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Belt-and-suspenders: pinning ``ATTUNE_MODEL_EDITING`` flows
    through to the SDK call — resolution is per call, not a
    hard-coded model name at the call site.
    """
    monkeypatch.setenv("ATTUNE_MODEL_EDITING", "claude-opus-4-8")
    with patch("attune.authoring.polish._cache_get", return_value=None):
        with patch("attune.models.single_turn.call_api", return_value="ok") as mock_call:
            with patch("attune.models.single_turn.get_client") as mock_client:
                mock_client.return_value = object()
                polish_template(
                    content="# X\n\nY\n",
                    feature_name="x",
                    source_summary="",
                    template_type="concept",
                    strict=True,
                )

    assert mock_call.call_args.kwargs["model"] == "claude-opus-4-8"


@pytest.mark.parametrize(
    "deprecated_alias",
    [
        # Historical: previously-pinned model that hit EOL 2026-06-15.
        # Re-using this list as a regression seed if we ever migrate again.
        "claude-sonnet-4-20250514",
        # Pre-tier pin replaced by the premium tier (specs/fable-model-tiers).
        "claude-sonnet-4-6",
    ],
)
def test_no_deprecated_model_aliases_in_defaults(
    deprecated_alias: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure deprecated aliases don't sneak back via copy-paste."""
    monkeypatch.delenv("ATTUNE_MODEL_PREMIUM", raising=False)
    assert _polish_model() != deprecated_alias
