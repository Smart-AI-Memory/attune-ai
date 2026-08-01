"""Edge-case coverage for run_context.py's defensive error paths.

The main provenance-resolution behavior (trigger validation, plain-repo
and worktree project identity) is already covered by
``test_run_record_corpus.py::TestProvenanceFields``. This file targets
the remaining defensive branches: the ``Path.resolve()``/``Path.cwd()``
failure in ``resolve_project_identity``, and the read failure / no-match
paths in ``_worktree_parent_name``.
"""

from pathlib import Path

from attune.models.telemetry.run_context import (
    _worktree_parent_name,
    resolve_project_identity,
)


class TestResolveProjectIdentityOSError:
    """Line 54-55: Path.cwd()/resolve() failure degrades to None."""

    def test_cwd_oserror_degrades_to_none(self, monkeypatch):
        def raise_oserror():
            raise OSError("cwd unavailable")

        monkeypatch.setattr(Path, "cwd", staticmethod(raise_oserror))
        assert resolve_project_identity() is None

    def test_resolve_oserror_degrades_to_none(self, monkeypatch, tmp_path):
        real_resolve = Path.resolve

        def raise_oserror(self, strict=False):
            if self == tmp_path / "start":
                raise OSError("resolve failed")
            return real_resolve(self, strict=strict)

        monkeypatch.setattr(Path, "resolve", raise_oserror)
        assert resolve_project_identity(tmp_path / "start") is None


class TestWorktreeParentNameEdgeCases:
    """Lines 69-71 (unreadable file), 74 (skip non-gitdir lines),
    79 (no matching gitdir line -> None)."""

    def test_unreadable_git_file_returns_none(self, tmp_path):
        missing = tmp_path / "does-not-exist" / ".git"
        assert _worktree_parent_name(missing) is None

    def test_skips_non_gitdir_lines_before_match(self, tmp_path):
        main = tmp_path / "mainrepo"
        (main / ".git" / "worktrees" / "slug").mkdir(parents=True)
        git_file = tmp_path / ".git"
        git_file.write_text(
            "\n".join(
                [
                    "# a stray comment line",
                    "",
                    f"gitdir: {main / '.git' / 'worktrees' / 'slug'}",
                ]
            ),
            encoding="utf-8",
        )
        assert _worktree_parent_name(git_file) == "mainrepo"

    def test_no_gitdir_line_returns_none(self, tmp_path):
        git_file = tmp_path / ".git"
        git_file.write_text("not a gitdir pointer at all\n", encoding="utf-8")
        assert _worktree_parent_name(git_file) is None

    def test_gitdir_line_not_matching_worktrees_layout_returns_none(self, tmp_path):
        git_file = tmp_path / ".git"
        git_file.write_text(f"gitdir: {tmp_path / 'somewhere' / 'else'}\n", encoding="utf-8")
        assert _worktree_parent_name(git_file) is None
