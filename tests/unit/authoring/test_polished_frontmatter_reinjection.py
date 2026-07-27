"""Regression tests for source_hash LLM-laundering fix.

The polish LLM is given the rendered template (with frontmatter)
as input context and asked to polish the body. Empirically, the
LLM also echoes the frontmatter in its output — sometimes with
single-character transcription errors in deterministic fields
like ``source_hash``. This broke staleness detection: the
frontmatter ``source_hash`` written into the polished file
didn't match what ``compute_source_hash`` recomputed on the
same source, leaving the feature permanently "stale" after a
successful regen.

The fix in ``generator.apply_polish_results`` strips whatever
frontmatter the LLM emitted and re-injects the canonical
frontmatter from ``entry.rendered_content``.

See ``docs/specs/regen-staleness-hash-mismatch/decisions.md``
for the full diagnosis.
"""

from __future__ import annotations

from pathlib import Path

from attune.authoring.generator import (
    GenerationResult,
    PolishPreparation,
    _PendingPolish,
    _replace_polished_frontmatter,
    apply_polish_results,
)

_CANONICAL_FRONTMATTER = (
    "---\n"
    "type: concept\n"
    "name: spec-engine-concept\n"
    "feature: spec-engine\n"
    "depth: concept\n"
    "generated_at: 2026-05-27T02:19:54.313049+00:00\n"
    "source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337\n"
    "status: generated\n"
    "---\n"
)

_RENDERED_BODY = "\n# Spec Engine\n\nThe spec engine is the runtime layer.\n"
_POLISHED_BODY = "\n# Spec Engine\n\nThe spec engine reads a plan and runs tasks.\n"


def _hash_field(text: str) -> str:
    """Pull the ``source_hash`` value out of a frontmatter block."""
    for line in text.splitlines():
        if line.startswith("source_hash:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("no source_hash in text")


class TestReplacePolishedFrontmatter:
    """Direct unit tests of ``_replace_polished_frontmatter``."""

    def test_polished_with_perturbed_source_hash_is_corrected(self) -> None:
        """The bug: LLM transcribed ``f7`` → ``f4`` at one position.
        Fix must restore the canonical hash regardless of LLM output."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        # LLM emitted frontmatter with a single-character corruption
        # at position 19 of the hash (the actual bug we observed).
        llm_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "f8ced22b02899aa25ff709",
            "f8ced22b02899aa25ff409",  # f7 → f4
        )
        polished = llm_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        # Canonical hash restored.
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)
        # Polished body preserved.
        assert _POLISHED_BODY.strip() in result
        # Original body not retained.
        assert "runtime layer" not in result

    def test_polished_with_missing_frontmatter_gets_canonical_prepended(self) -> None:
        """LLM might drop the frontmatter entirely. We still prepend
        the canonical block so the file isn't malformed."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished_body_only = _POLISHED_BODY.lstrip("\n")

        result = _replace_polished_frontmatter(polished_body_only, canonical)

        assert result.startswith("---\n")
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)
        assert "reads a plan" in result

    def test_polished_with_correct_frontmatter_unchanged_semantically(self) -> None:
        """When the LLM echoes the frontmatter correctly, output is
        functionally identical to the input (canonical block wins,
        but the canonical block IS what the LLM emitted)."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished = _CANONICAL_FRONTMATTER + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)
        assert "reads a plan" in result

    def test_canonical_without_frontmatter_returns_polished_unchanged(self) -> None:
        """Defensive: if rendered template has no frontmatter
        (shouldn't happen in practice), return polished untouched
        rather than crash."""
        canonical = "# No frontmatter\n\nJust a body.\n"
        polished = "# Polished\n\nDifferent body.\n"

        result = _replace_polished_frontmatter(polished, canonical)

        assert result == polished

    def test_extra_blank_lines_in_polished_body_preserved(self) -> None:
        """Polish layer often returns extra newlines for readability.
        Body whitespace should pass through untouched."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished = _CANONICAL_FRONTMATTER + "\n\n# Heading\n\nParagraph.\n\n\n"

        result = _replace_polished_frontmatter(polished, canonical)

        assert result.endswith("Paragraph.\n\n\n")

    def test_polish_skipped_marker_preserved(self) -> None:
        """Lenient-mode polish failure adds a ``polish: skipped``
        marker to the frontmatter via
        :func:`attune.authoring.polish._mark_polish_skipped`. The
        re-inject must preserve that marker — it's the regression
        signal downstream consumers (and snapshot tests) rely on
        to detect raw-template output."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        # Polish-skipped path adds `polish: skipped` as a non-
        # deterministic frontmatter field. The deterministic
        # fields can ALSO be perturbed (LLM transcription) but
        # in the lenient-fallback path the polish layer just
        # passes the rendered frontmatter through with the
        # marker appended — so the only mutation is the new
        # field. We still exercise both.
        polished_frontmatter = (
            _CANONICAL_FRONTMATTER.replace(
                "f8ced22b02899aa25ff709",
                "f8ced22b02899aa25ff409",  # f7 → f4 perturbation
            )
            .rstrip("\n")
            .rstrip("-")
            .rstrip("\n")
            .rstrip("-")
            .rstrip("\n")
            .rstrip("-")
        )
        # Reconstruct with the marker before the closing ---
        polished_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "f8ced22b02899aa25ff709",
            "f8ced22b02899aa25ff409",
        ).replace("status: generated\n---\n", "status: generated\npolish: skipped\n---\n")
        polished = polished_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        # Deterministic field corrected from canonical.
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)
        # Non-deterministic polish marker preserved.
        assert "polish: skipped" in result

    def test_unknown_non_deterministic_field_preserved(self) -> None:
        """Forward-compatibility: if the polish layer adds a NEW
        non-deterministic field in the future (e.g.
        ``polish_attempts: 3``), the re-inject must preserve it.
        Only the closed set of DETERMINISTIC fields is overridden."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "status: generated\n---\n",
            "status: generated\npolish_attempts: 3\nmodel: claude-sonnet-4-6\n---\n",
        )
        polished = polished_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        assert "polish_attempts: 3" in result
        assert "model: claude-sonnet-4-6" in result

    def test_comment_lines_in_polished_frontmatter_preserved(self) -> None:
        """Non-key lines in the polished frontmatter (comments, blanks)
        parse with an empty key in ``_parse_frontmatter_lines`` and so
        flow through the non-deterministic branch — they must survive
        the merge verbatim, same as any preserved field."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "status: generated\n---\n",
            "status: generated\n# hand-authored note — keep me\n\nsummary: a concept\n---\n",
        )
        polished = polished_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        # Comment line (empty-key) preserved.
        assert "# hand-authored note — keep me" in result
        # Non-deterministic field that followed it preserved too.
        assert "summary: a concept" in result
        # Deterministic field still corrected from canonical.
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)

    def test_deterministic_field_in_polished_absent_from_canonical_is_dropped(self) -> None:
        """When the polish output carries a DETERMINISTIC field the
        canonical block lacks (here ``scaffold_hash`` — not present in
        the rendered template), the value is dropped rather than
        trusted: ``canonical_by_key.get(key)`` is ``None`` so neither
        the polished nor a canonical line is emitted ("better silence
        than propagating a possibly-perturbed value")."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY  # no scaffold_hash
        polished_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "status: generated\n---\n",
            "status: generated\nscaffold_hash: deadbeefcafe0000\n---\n",
        )
        polished = polished_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        # The deterministic field absent from canonical is dropped entirely.
        assert "scaffold_hash" not in result
        assert "deadbeefcafe0000" not in result
        # Other fields unaffected.
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)

    def test_deterministic_field_missing_from_polished_appended_from_canonical(self) -> None:
        """If the LLM dropped a single deterministic line (here
        ``source_hash``) but kept the rest of the frontmatter, the
        canonical value must still be re-appended — the final
        canonical-append loop guarantees deterministic fields are
        always present, distinct from the whole-frontmatter-missing
        path (``polished_match is None``)."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        # Polished frontmatter identical to canonical except the
        # source_hash line is omitted entirely.
        polished_frontmatter = "".join(
            f"{line}\n"
            for line in _CANONICAL_FRONTMATTER.splitlines()
            if not line.startswith("source_hash:")
        )
        polished = polished_frontmatter + _POLISHED_BODY
        assert "source_hash:" not in polished_frontmatter  # guard the setup

        result = _replace_polished_frontmatter(polished, canonical)

        # Canonical source_hash re-appended despite polish omitting it.
        assert _hash_field(result) == _hash_field(_CANONICAL_FRONTMATTER)

    def test_multiline_yaml_value_in_polished_frontmatter_preserved(self) -> None:
        """Structural / continuation lines of a multi-line YAML value
        (a ``tags:`` list) aren't ``key: value`` shaped, so they parse
        with an empty key and must pass through verbatim — the merge
        must not flatten or drop block-style values."""
        canonical = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        polished_frontmatter = _CANONICAL_FRONTMATTER.replace(
            "status: generated\n---\n",
            "status: generated\ntags:\n  - spec\n  - engine\n---\n",
        )
        polished = polished_frontmatter + _POLISHED_BODY

        result = _replace_polished_frontmatter(polished, canonical)

        assert "tags:" in result
        assert "  - spec" in result
        assert "  - engine" in result


class TestApplyPolishResultsReinjectsFrontmatter:
    """Behavioral tests for the wiring in ``apply_polish_results``."""

    def test_polished_template_keeps_canonical_source_hash(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """End-to-end: a polished template with corrupted source_hash
        in the LLM output gets the canonical hash on disk."""
        # Disable fact-check + faithfulness gates to keep this unit
        # test self-contained (no network, no schema validation).
        monkeypatch.setenv("ATTUNE_AUTHOR_FACT_CHECK", "off")
        monkeypatch.setenv("ATTUNE_AUTHOR_FAITHFULNESS_GATE", "off")
        monkeypatch.chdir(tmp_path)

        out_path = tmp_path / "concept.md"
        rendered_content = _CANONICAL_FRONTMATTER + _RENDERED_BODY
        # Polish "output" perturbs the hash by one character.
        polished_content = (
            _CANONICAL_FRONTMATTER.replace(
                "f8ced22b02899aa25ff709",
                "f8ced22b02899aa25ff409",
            )
            + _POLISHED_BODY
        )

        prep = PolishPreparation(
            feature=type("F", (), {"name": "spec-engine"})(),
            source_hash="f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337",
            matched_files=[],
            source_info=None,
            pending=(
                _PendingPolish(
                    depth="concept",
                    rendered_content=rendered_content,
                    out_path=out_path,
                ),
            ),
            use_rag=False,
        )

        result = apply_polish_results(prep, {"concept": polished_content})

        assert isinstance(result, GenerationResult)
        written = out_path.read_text(encoding="utf-8")
        # The corrupted ``f4`` hash from the LLM output must NOT
        # have survived to disk.
        assert "ff409" not in written
        # The canonical ``f7`` hash from the rendered template is
        # what got written.
        assert _hash_field(written) == _hash_field(_CANONICAL_FRONTMATTER)
        # The polished body did make it through.
        assert "reads a plan" in written

    def test_no_polish_result_uses_rendered_content_directly(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """If polish was skipped (lenient-mode failure), apply still
        writes the rendered template with correct frontmatter."""
        monkeypatch.setenv("ATTUNE_AUTHOR_FACT_CHECK", "off")
        monkeypatch.setenv("ATTUNE_AUTHOR_FAITHFULNESS_GATE", "off")
        monkeypatch.chdir(tmp_path)

        out_path = tmp_path / "concept.md"
        rendered_content = _CANONICAL_FRONTMATTER + _RENDERED_BODY

        prep = PolishPreparation(
            feature=type("F", (), {"name": "spec-engine"})(),
            source_hash="f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337",
            matched_files=[],
            source_info=None,
            pending=(
                _PendingPolish(
                    depth="concept",
                    rendered_content=rendered_content,
                    out_path=out_path,
                ),
            ),
            use_rag=False,
        )

        # No entry for "concept" in the polished map.
        result = apply_polish_results(prep, {})

        assert isinstance(result, GenerationResult)
        written = out_path.read_text(encoding="utf-8")
        assert _hash_field(written) == _hash_field(_CANONICAL_FRONTMATTER)
        # Original rendered body, not a polished one.
        assert "runtime layer" in written
