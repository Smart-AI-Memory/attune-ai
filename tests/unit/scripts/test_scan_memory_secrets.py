"""Tests for the advisory memory secret sweep (R2).

Hermetic: builds a fake corpus under tmp_path. Never reads the real home
directory — a test that did would leak a machine-specific dependency into CI.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "scan_memory_secrets",
    Path(__file__).resolve().parents[3] / "scripts" / "scan_memory_secrets.py",
)
scan_memory_secrets = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scan_memory_secrets)


def _write(root: Path, name: str, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / name
    p.write_text(body, encoding="utf-8")
    return p


def test_clean_corpus_reports_no_findings(tmp_path: Path) -> None:
    _write(tmp_path, "feedback_a.md", "Patrick prefers concise responses.")
    report = scan_memory_secrets.sweep([tmp_path], [])
    assert report["findings"] == []
    assert report["files_scanned"] == 1


def test_finds_secret_in_markdown(tmp_path: Path) -> None:
    _write(tmp_path, "project_leak.md", "the key is AKIAIOSFODNN7EXAMPLE oops")
    report = scan_memory_secrets.sweep([tmp_path], [])
    assert len(report["findings"]) == 1
    assert report["findings"][0]["type"] == "aws_access_key"
    assert report["findings"][0]["path"].endswith("project_leak.md")


def test_finds_bare_anthropic_key_the_proof_case(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "project_x.md",
        "note: sk-ant-api03-aB3xY7kLmN9pQ2rS5tU8vW1zA4bC6dE0fG3hJ5kL7nP9qR2sT4uV6wX8yZ0aB1cD3eF5gH7iJ9kL1mN3oP5qR7sT9uV1wX3",
    )
    report = scan_memory_secrets.sweep([tmp_path], [])
    assert any(f["type"] == "anthropic_api_key" for f in report["findings"])


def test_prose_mention_is_not_a_finding(tmp_path: Path) -> None:
    _write(tmp_path, "note.md", "console shows the real sk-ant value only in the dialog")
    assert scan_memory_secrets.sweep([tmp_path], [])["findings"] == []


def test_hyphenated_slug_is_not_a_key(tmp_path: Path) -> None:
    """Regression: the first live sweep flagged 61 false openai keys — all the
    telemetry slug 'sk-queued-as-resume-...'. A real key carries digits and
    mixed case; an English hyphenated slug does not, so the key-shape gate
    rejects it while the real key alphabet (incl. _ and -) is preserved."""
    jf = tmp_path / "memory_events.jsonl"
    jf.write_text(
        '{"note": "session-task-queued-as-resume-this-batch-can-be-picked-up-later"}\n',
        encoding="utf-8",
    )
    assert scan_memory_secrets.sweep([], [jf])["findings"] == []


def test_real_openai_key_with_underscore_and_dash_is_caught(tmp_path: Path) -> None:
    """A review found the earlier alnum-only tightening leaked real sk-proj-
    keys, whose bodies contain _ and -. The gate must catch them."""
    body = "aB3_xY7-kLmN9pQ2rS5tU8vW1zA4bC6dE0fG3hJ5kL7nP9qR2"
    _write(tmp_path, "leak.md", f"key: sk-proj-{body}")
    findings = scan_memory_secrets.sweep([tmp_path], [])["findings"]
    assert any(f["type"] == "openai_api_key" for f in findings)


def test_scans_jsonl_lines_with_line_numbers(tmp_path: Path) -> None:
    jf = tmp_path / "findings.jsonl"
    jf.write_text('{"content": "clean"}\n{"content": "AKIAIOSFODNN7EXAMPLE"}\n', encoding="utf-8")
    report = scan_memory_secrets.sweep([], [jf])
    assert len(report["findings"]) == 1
    assert report["findings"][0]["line"] == 2


def test_main_exit_codes(tmp_path: Path) -> None:
    _write(tmp_path, "clean.md", "nothing here")
    assert scan_memory_secrets.main(["--root", str(tmp_path)]) == 0
    _write(tmp_path, "dirty.md", "AKIAIOSFODNN7EXAMPLE")
    assert scan_memory_secrets.main(["--root", str(tmp_path)]) == 1


def test_sweep_is_read_only(tmp_path: Path) -> None:
    import hashlib

    p = _write(tmp_path, "project_leak.md", "AKIAIOSFODNN7EXAMPLE")
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    scan_memory_secrets.sweep([tmp_path], [])
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
