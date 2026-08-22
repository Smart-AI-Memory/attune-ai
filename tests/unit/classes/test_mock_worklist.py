"""Class-M AST worklist detector — three shapes on pinned fixtures."""

from __future__ import annotations

import textwrap
from pathlib import Path

from attune.classes.mock_worklist import scan_file, scan_paths


def _write(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "test_fixture.py"
    f.write_text(textwrap.dedent(body))
    return f


class TestPatchedCallSite:
    def test_mock_only_assertions_flag(self, tmp_path):
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def test_calls_store():
                with patch("pkg.mod.get_store") as m:
                    run()
                    m.assert_called_once_with("x")
        """,
        )
        items = scan_file(f)
        assert [i.shape for i in items] == ["patched-call-site"]
        assert "pkg.mod.get_store" in items[0].detail

    def test_real_assert_alongside_mock_does_not_flag(self, tmp_path):
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def test_calls_store():
                with patch("pkg.mod.get_store") as m:
                    result = run()
                    m.assert_called_once()
                    assert result == 3
        """,
        )
        assert scan_file(f) == []

    def test_decorator_patch_detected(self, tmp_path):
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            @patch("pkg.mod.helper")
            def test_uses_helper(m):
                go()
                m.assert_called_once()
        """,
        )
        items = scan_file(f)
        assert items and items[0].shape == "patched-call-site"

    def test_non_test_function_ignored(self, tmp_path):
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def helper():
                with patch("pkg.mod.x") as m:
                    m.assert_called_once()
        """,
        )
        assert scan_file(f) == []


class TestLiteralFixture:
    def test_dict_literal_to_from_dict_flags(self, tmp_path):
        f = _write(
            tmp_path,
            """
            def test_reads_record():
                rec = Store.from_dict({"ts": 1, "body": "x"})
                assert rec.ts == 1
        """,
        )
        items = scan_file(f)
        assert [i.shape for i in items] == ["literal-fixture"]
        assert "from_dict" in items[0].detail

    def test_serializer_built_record_does_not_flag(self, tmp_path):
        f = _write(
            tmp_path,
            """
            def test_reads_record():
                rec = Store.from_dict(make_record().to_dict())
                assert rec.ts == 1
        """,
        )
        assert scan_file(f) == []


class TestPatchedRefusal:
    def test_patched_write_with_oserror_flags(self, tmp_path):
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def test_cannot_write():
                with patch("pathlib.Path.write_text", side_effect=OSError("denied")):
                    assert save() is False
        """,
        )
        items = scan_file(f)
        assert [i.shape for i in items] == ["patched-refusal"]

    def test_urlopen_error_is_not_a_refusal_candidate(self, tmp_path):
        # Calibration FP pin (2026-08-22): substring "open" matched
        # urlopen; network error tests are legitimate patches.
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def test_network_down():
                with patch("urllib.request.urlopen", side_effect=OSError("net")):
                    assert fetch() is None
        """,
        )
        assert [i.shape for i in scan_file(f)] == []

    def test_popen_error_is_not_a_refusal_candidate(self, tmp_path):
        # Calibration FP pin (2026-08-22): "Popen" substring-matched "open".
        f = _write(
            tmp_path,
            """
            from unittest.mock import patch

            def test_subprocess_fails():
                with patch("subprocess.Popen", side_effect=OSError("boom")):
                    assert launch() is None
        """,
        )
        assert [i.shape for i in scan_file(f)] == []

    def test_real_chmod_refusal_does_not_flag(self, tmp_path):
        f = _write(
            tmp_path,
            """
            def test_cannot_write(tmp_path):
                tmp_path.chmod(0o500)
                assert save(tmp_path) is False
        """,
        )
        assert scan_file(f) == []


class TestScanPlumbing:
    def test_unparseable_file_returns_empty(self, tmp_path):
        f = tmp_path / "test_bad.py"
        f.write_text("def broken(:\n")
        assert scan_file(f) == []

    def test_scan_paths_walks_directories(self, tmp_path):
        _write(
            tmp_path,
            """
            def test_x():
                rec = load({"a": 1})
                assert rec
        """,
        )
        items = scan_paths([tmp_path])
        assert len(items) == 1
