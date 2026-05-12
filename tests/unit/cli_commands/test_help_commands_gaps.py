"""Tests for help_commands branches not covered by the existing suite.

The existing `tests/unit/cli_commands/test_help_commands.py` covers
the happy paths (16 tests, 73% line+branch). This file targets the
remaining ~27% — edge cases and the `_record_feedback` /
verbosity-flag branches that the existing tests don't exercise:

- `_get_generated_dir()` path resolution (lines 36-38)
- `_list_categories` missing-category-dir branch (line 63)
- `_list_categories` no-cross-links branch (67->78)
- `_list_category` empty-files branch (103-104)
- `_show_template` prefixed-name-not-found branch (147-148)
- `_list_all_tags` empty-tags branch (199-200)
- `_record_feedback` invalid + happy + prefix-resolution branches
  (220-243)
- `cmd_help` --feedback routing + missing-topic branch (260-264)
- `cmd_help` --deep and --detail verbosity branches (287, 289)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("frontmatter")

from attune.cli_commands.help_commands import (  # noqa: E402
    _get_generated_dir,
    _list_all_tags,
    _list_categories,
    _list_category,
    _record_feedback,
    _show_template,
    cmd_help,
)

# ---------------------------------------------------------------------------
# _get_generated_dir() — path resolution
# ---------------------------------------------------------------------------


class TestGetGeneratedDir:
    def test_returns_path_under_plugin_help(self):
        """Resolves to <repo_root>/plugin/help/generated."""
        result = _get_generated_dir()
        assert isinstance(result, Path)
        assert result.parts[-3:] == ("plugin", "help", "generated")


# ---------------------------------------------------------------------------
# _list_categories — branch coverage for missing dirs and no-cross-links
# ---------------------------------------------------------------------------


class TestListCategoriesBranches:
    def test_missing_category_subdir_shows_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """If `<generated>/<category>` doesn't exist, the function still
        prints `0 templates` for it (line 63 else-branch).
        """
        gen = tmp_path / "generated"
        gen.mkdir()
        # Only create one of the four categories.
        (gen / "errors").mkdir()
        (gen / "errors" / "err-foo.md").write_text("x")

        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=gen,
        ):
            rc = _list_categories()

        assert rc == 0
        out = capsys.readouterr().out
        # The other three categories print "0 templates" via the
        # missing-dir branch. The exact padding varies with the
        # category name length, so count occurrences instead.
        assert out.count("0 templates") == 3
        for missing in ("warnings", "tips", "references"):
            assert missing in out

    def test_no_cross_links_skips_summary_block(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """If `cross_links.json` is missing, the summary block isn't
        printed (branch 67->78 jumps past the linked/tags summary).
        """
        gen = tmp_path / "generated"
        (gen / "errors").mkdir(parents=True)
        (gen / "errors" / "err-foo.md").write_text("x")

        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=gen,
        ):
            rc = _list_categories()

        assert rc == 0
        out = capsys.readouterr().out
        # The "Total: ... linked, ... tags" line only appears when
        # cross_links.json exists — confirm its absence.
        assert "linked" not in out


# ---------------------------------------------------------------------------
# _list_category — empty-files branch
# ---------------------------------------------------------------------------


class TestListCategoryEmpty:
    def test_empty_category_returns_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        gen = tmp_path / "generated"
        cat = gen / "errors"
        cat.mkdir(parents=True)  # exists but empty

        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=gen,
        ):
            rc = _list_category("errors")

        assert rc == 1
        assert "No templates in 'errors'" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _show_template — prefixed-name explicit-not-found branch
# ---------------------------------------------------------------------------


class TestShowTemplatePrefixedNotFound:
    def test_prefixed_name_not_found_returns_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When the name has a known prefix but populate() returns None,
        the function prints "Template '...' not found." and returns 1
        (line 147-148 branch).
        """
        with patch(
            "attune.help.engine.populate",
            return_value=None,
        ):
            rc = _show_template("err-nonexistent")

        assert rc == 1
        out = capsys.readouterr().out
        assert "err-nonexistent" in out
        assert "not found" in out


# ---------------------------------------------------------------------------
# _list_all_tags — empty-tags branch
# ---------------------------------------------------------------------------


class TestListAllTagsEmpty:
    def test_returns_1_when_no_tags(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "attune.help.engine.list_tags",
            return_value={},
        ):
            rc = _list_all_tags()

        assert rc == 1
        assert "No tags found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _record_feedback — invalid rating, happy path, prefix resolution
# ---------------------------------------------------------------------------


class TestRecordFeedback:
    def test_invalid_rating_returns_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = _record_feedback("foo", "maybe")
        assert rc == 1
        assert "Invalid rating" in capsys.readouterr().out

    def test_prefixed_name_passes_through(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A name that already has a known prefix is recorded as-is."""
        with patch(
            "attune.help.engine.record_template_feedback",
            return_value=0.87,
        ) as mock_record:
            rc = _record_feedback("err-foo", "good")
        assert rc == 0
        mock_record.assert_called_once_with("err-foo", "good")
        out = capsys.readouterr().out
        assert "Feedback recorded for err-foo" in out
        assert "Confidence: 0.87" in out

    def test_bare_name_tries_each_prefix(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A bare name tries each prefix; on first match the prefixed
        id is used for recording.
        """

        # populate returns a value only for the "war-" prefix
        def fake_populate(template_id, audience=None):
            return object() if template_id == "war-foo" else None

        with (
            patch(
                "attune.help.engine.populate",
                side_effect=fake_populate,
            ),
            patch(
                "attune.help.engine.record_template_feedback",
                return_value=0.5,
            ) as mock_record,
        ):
            rc = _record_feedback("foo", "bad")

        assert rc == 0
        # The resolved template_id should be "war-foo".
        mock_record.assert_called_once_with("war-foo", "bad")

    def test_bare_name_no_match_falls_back_to_raw(self, capsys: pytest.CaptureFixture[str]) -> None:
        """If no prefix matches, the raw name is passed to record()."""
        with (
            patch(
                "attune.help.engine.populate",
                return_value=None,
            ),
            patch(
                "attune.help.engine.record_template_feedback",
                return_value=0.1,
            ) as mock_record,
        ):
            rc = _record_feedback("unprefixed", "good")

        assert rc == 0
        # No prefix matched — original name passed through.
        mock_record.assert_called_once_with("unprefixed", "good")


# ---------------------------------------------------------------------------
# cmd_help — --feedback routing + missing-topic branch
# ---------------------------------------------------------------------------


class TestCmdHelpFeedback:
    def test_feedback_without_topic_returns_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = argparse.Namespace(feedback="good", topic=None)
        rc = cmd_help(args)
        assert rc == 1
        assert "attune help-docs" in capsys.readouterr().out

    def test_feedback_with_topic_routes(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = argparse.Namespace(feedback="bad", topic="err-foo")
        with patch(
            "attune.help.engine.record_template_feedback",
            return_value=0.42,
        ) as mock_record:
            rc = cmd_help(args)
        assert rc == 0
        mock_record.assert_called_once_with("err-foo", "bad")


# ---------------------------------------------------------------------------
# cmd_help — --deep / --detail verbosity branches
# ---------------------------------------------------------------------------


class TestCmdHelpVerbosity:
    def _make_args(self, **overrides):
        defaults = {
            "feedback": None,
            "tags": False,
            "tag": None,
            "topic": "err-foo",
            "deep": False,
            "detail": False,
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_deep_flag_uses_detailed(self) -> None:
        captured: dict = {}

        def fake_show(name, verbosity="normal"):
            captured["verbosity"] = verbosity
            return 0

        with patch(
            "attune.cli_commands.help_commands._show_template",
            side_effect=fake_show,
        ):
            cmd_help(self._make_args(deep=True))

        assert captured["verbosity"] == "detailed"

    def test_detail_flag_uses_normal(self) -> None:
        captured: dict = {}

        def fake_show(name, verbosity="normal"):
            captured["verbosity"] = verbosity
            return 0

        with patch(
            "attune.cli_commands.help_commands._show_template",
            side_effect=fake_show,
        ):
            cmd_help(self._make_args(detail=True))

        assert captured["verbosity"] == "normal"

    def test_default_flags_use_compact(self) -> None:
        captured: dict = {}

        def fake_show(name, verbosity="normal"):
            captured["verbosity"] = verbosity
            return 0

        with patch(
            "attune.cli_commands.help_commands._show_template",
            side_effect=fake_show,
        ):
            cmd_help(self._make_args())

        assert captured["verbosity"] == "compact"
