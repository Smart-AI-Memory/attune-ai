"""Tests for _bootstrap.py shared hook-script bootstrap helpers.

Covers the three stdlib-only helpers that hook scripts import before
doing any I/O:

- ``ensure_utf8_stdio`` — reconfigure stdout/stderr to UTF-8, but only
  when the current encoding isn't already utf-8/utf8 AND the stream
  exposes ``.reconfigure``.
- ``read_stdin_utf8`` — decode ``sys.stdin.buffer`` as UTF-8 with
  ``errors="replace"``, honoring an optional byte limit, and falling
  back to ``sys.stdin.read()`` when ``.buffer`` is absent.
- ``ensure_repo_src_on_path`` — insert the repo's ``src/`` at
  ``sys.path[0]`` exactly once, guarded by a real
  ``src/attune/__init__.py`` check, and no-op on ``IndexError`` or a
  missing/invalid package marker.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "hooks" / "scripts" / "_bootstrap.py"
)


@pytest.fixture()
def bootstrap_module():
    """Load _bootstrap.py fresh for each test (no shared sys.path state)."""
    spec = importlib.util.spec_from_file_location("_bootstrap_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_bootstrap_under_test"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_bootstrap_under_test", None)


# ---------------------------------------------------------------------
# ensure_utf8_stdio
# ---------------------------------------------------------------------


class TestEnsureUtf8Stdio:
    def test_reconfigures_non_utf8_stream_with_reconfigure(self, bootstrap_module, monkeypatch):
        """A stream reporting cp1252 (Windows console default) with a
        .reconfigure method gets reconfigured to utf-8/replace."""
        stdout = MagicMock()
        stdout.encoding = "cp1252"
        stderr = MagicMock()
        stderr.encoding = "cp1252"
        monkeypatch.setattr(sys, "stdout", stdout)
        monkeypatch.setattr(sys, "stderr", stderr)

        bootstrap_module.ensure_utf8_stdio()

        stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")

    def test_already_utf8_stream_not_reconfigured(self, bootstrap_module, monkeypatch):
        """A stream already reporting utf-8 is left alone even though it
        has a .reconfigure method (would be a needless no-op call)."""
        stdout = MagicMock()
        stdout.encoding = "utf-8"
        stderr = MagicMock()
        stderr.encoding = "UTF8"  # case + no-hyphen variant also counts as utf8
        monkeypatch.setattr(sys, "stdout", stdout)
        monkeypatch.setattr(sys, "stderr", stderr)

        bootstrap_module.ensure_utf8_stdio()

        stdout.reconfigure.assert_not_called()
        stderr.reconfigure.assert_not_called()

    def test_stream_without_reconfigure_is_noop(self, bootstrap_module, monkeypatch):
        """A stream with a non-utf8 encoding but no .reconfigure (e.g. a
        pytest capture object) must not crash — pure no-op."""

        class NoReconfigure:
            encoding = "cp1252"

        stdout = NoReconfigure()
        stderr = NoReconfigure()
        monkeypatch.setattr(sys, "stdout", stdout)
        monkeypatch.setattr(sys, "stderr", stderr)

        # Must not raise (no .reconfigure to call).
        bootstrap_module.ensure_utf8_stdio()

    def test_stream_with_no_encoding_attr_is_noop(self, bootstrap_module, monkeypatch):
        """A stream with no `encoding` attribute at all (getattr default
        None) short-circuits before touching .reconfigure."""

        class NoEncoding:
            def reconfigure(self, **kwargs):
                raise AssertionError("reconfigure should not be called")

        stdout = NoEncoding()
        stderr = NoEncoding()
        monkeypatch.setattr(sys, "stdout", stdout)
        monkeypatch.setattr(sys, "stderr", stderr)

        bootstrap_module.ensure_utf8_stdio()


# ---------------------------------------------------------------------
# read_stdin_utf8
# ---------------------------------------------------------------------


class _FakeStdinWithBuffer:
    """Mimics sys.stdin with a `.buffer` attribute backed by BytesIO."""

    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)


class TestReadStdinUtf8:
    def test_decodes_full_payload(self, bootstrap_module, monkeypatch):
        monkeypatch.setattr(sys, "stdin", _FakeStdinWithBuffer(b"hello world"))
        assert bootstrap_module.read_stdin_utf8() == "hello world"

    def test_respects_byte_limit(self, bootstrap_module, monkeypatch):
        """limit caps the number of BYTES read from the buffer, not
        characters — only the first N bytes are read/decoded."""
        monkeypatch.setattr(sys, "stdin", _FakeStdinWithBuffer(b"abcdefghij"))
        assert bootstrap_module.read_stdin_utf8(limit=3) == "abc"

    def test_malformed_utf8_bytes_replaced_not_raised(self, bootstrap_module, monkeypatch):
        """Undecodable bytes become U+FFFD replacement chars instead of
        raising UnicodeDecodeError."""
        # 0xFF is never valid as a UTF-8 lead byte.
        monkeypatch.setattr(sys, "stdin", _FakeStdinWithBuffer(b"ok-\xff-end"))
        result = bootstrap_module.read_stdin_utf8()
        assert "�" in result
        assert result.startswith("ok-")
        assert result.endswith("-end")

    def test_buffer_none_falls_back_to_stdin_read(self, bootstrap_module, monkeypatch):
        """When sys.stdin.buffer is None (already-detached/wrapped stream,
        e.g. some test harnesses), fall back to sys.stdin.read()."""

        class DetachedStdin:
            buffer = None

            def read(self, n=None):
                return "fallback-text" if n is None else "fallback-text"[:n]

        monkeypatch.setattr(sys, "stdin", DetachedStdin())
        assert bootstrap_module.read_stdin_utf8() == "fallback-text"

    def test_buffer_none_fallback_respects_limit(self, bootstrap_module, monkeypatch):
        class DetachedStdin:
            buffer = None

            def read(self, n=None):
                full = "fallback-text"
                return full if n is None else full[:n]

        monkeypatch.setattr(sys, "stdin", DetachedStdin())
        assert bootstrap_module.read_stdin_utf8(limit=8) == "fallback"


# ---------------------------------------------------------------------
# ensure_repo_src_on_path
# ---------------------------------------------------------------------


def _make_fake_repo(repo_root: Path, *, with_init: bool) -> Path:
    """Build a repo layout mirroring the real one and return the fake
    script path, so ``Path(fake_script).resolve().parents[3]`` lands on
    ``repo_root / "src"`` — exactly like the real
    ``src/attune/hooks/scripts/_bootstrap.py`` does relative to
    ``src/``. ``attune/hooks/scripts/`` mirrors the real 3-level
    nesting under ``src/`` needed for that arithmetic to hold.
    """
    attune_dir = repo_root / "src" / "attune"
    attune_dir.mkdir(parents=True)
    if with_init:
        (attune_dir / "__init__.py").write_text("")
    fake_script = attune_dir / "hooks" / "scripts" / "_bootstrap.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("")
    return fake_script


class TestEnsureRepoSrcOnPath:
    def test_inserts_valid_src_at_front_of_syspath(self, bootstrap_module, tmp_path, monkeypatch):
        """A valid repo layout (src/attune/__init__.py exists 3 parents
        up from the script) gets inserted at sys.path[0]."""
        repo_root = tmp_path
        fake_script = _make_fake_repo(repo_root, with_init=True)

        monkeypatch.setattr(bootstrap_module, "__file__", str(fake_script))
        original_path = list(sys.path)
        monkeypatch.setattr(sys, "path", list(original_path))

        bootstrap_module.ensure_repo_src_on_path()

        expected_src = str((repo_root / "src").resolve())
        assert sys.path[0] == expected_src

    def test_second_call_does_not_duplicate(self, bootstrap_module, tmp_path, monkeypatch):
        """Calling twice (even with the entry already elsewhere in
        sys.path) results in exactly one occurrence — no duplication."""
        repo_root = tmp_path
        fake_script = _make_fake_repo(repo_root, with_init=True)

        monkeypatch.setattr(bootstrap_module, "__file__", str(fake_script))
        expected_src = str((repo_root / "src").resolve())
        # Pre-seed sys.path with the entry somewhere in the MIDDLE, not
        # index 0, to prove the "already present" check isn't index-bound.
        monkeypatch.setattr(sys, "path", ["/somewhere/else", expected_src, "/another"])

        bootstrap_module.ensure_repo_src_on_path()

        assert sys.path.count(expected_src) == 1
        # And it wasn't moved to the front either — a true no-op.
        assert sys.path[1] == expected_src

    def test_missing_init_py_is_noop(self, bootstrap_module, tmp_path, monkeypatch):
        """If src/attune/ exists but has no __init__.py, the function
        must NOT insert anything — this guards against a namespace-
        package false match from an unrelated `attune` dir outside the
        repo (e.g. the plugin-copy layout)."""
        repo_root = tmp_path
        fake_script = _make_fake_repo(repo_root, with_init=False)

        monkeypatch.setattr(bootstrap_module, "__file__", str(fake_script))
        original_path = list(sys.path)
        monkeypatch.setattr(sys, "path", list(original_path))

        bootstrap_module.ensure_repo_src_on_path()

        expected_src = str((repo_root / "src").resolve())
        assert expected_src not in sys.path
        assert sys.path == original_path

    def test_index_error_from_shallow_parents_is_noop(self, bootstrap_module, monkeypatch):
        """If Path(__file__).resolve().parents[3] raises IndexError (a
        path too shallow to have 4 ancestors), the function returns
        without raising and without touching sys.path."""

        class ShallowParents:
            def __getitem__(self, idx):
                raise IndexError("not enough parents")

        class FakeResolved:
            parents = ShallowParents()

        class FakePath:
            def resolve(self):
                return FakeResolved()

        monkeypatch.setattr(bootstrap_module, "Path", lambda *_a, **_kw: FakePath())
        original_path = list(sys.path)
        monkeypatch.setattr(sys, "path", list(original_path))

        # Must not raise.
        bootstrap_module.ensure_repo_src_on_path()

        assert sys.path == original_path
