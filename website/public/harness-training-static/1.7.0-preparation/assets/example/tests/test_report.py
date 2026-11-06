"""Black-box acceptance checks for the documented reporting CLI contract."""

import csv
import io
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
HEADER = "date,project,category,minutes\n"
VALID_ROW = "2026-10-19,Orion,Development,7\n"


def run_cli(path):
    # Deliberately do not inherit API credentials or Python startup settings.
    env = {
        "PATH": str(Path(sys.executable).parent),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("SystemRoot", "WINDIR"):
        if name in os.environ:
            env[name] = os.environ[name]
    return subprocess.run(
        [sys.executable, "-B", str(PROJECT / "report.py"), str(path)],
        cwd=PROJECT,
        env=env,
        capture_output=True,
        timeout=3,
        check=False,
    )


def input_file(tmp_path, text):
    path = tmp_path / "activity.csv"
    path.write_bytes(text.encode("utf-8"))
    return path


def assert_success(result, expected):
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout == expected.encode("utf-8")
    assert result.stderr == b""


def assert_input_error(result, *, field=None, row=None, kind=None):
    assert result.returncode == 2
    assert result.stdout == b"", "Invalid input must not emit a partial report"
    message = result.stderr.decode("utf-8")
    assert message.startswith("Input error:"), message
    assert message.removeprefix("Input error:").strip(), message
    assert "Traceback" not in message
    if field is not None:
        assert re.search(rf"\b{re.escape(field)}\b", message, re.IGNORECASE), message
    if row is not None:
        assert re.search(rf"\b(?:row|record)\s*(?:#|:)?\s*{row}\b", message, re.IGNORECASE), message
    if kind is not None:
        assert re.search(kind, message, re.IGNORECASE), message


def csv_record(values):
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerow(values)
    return output.getvalue()


def test_sample_matches_exact_golden_report():
    expected = (PROJECT / "expected" / "activity-report.txt").read_bytes()
    result = run_cli(PROJECT / "data" / "activity.csv")
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout == expected
    assert result.stderr == b""


def test_columns_can_be_reordered_and_blank_lines_ignored(tmp_path):
    source = (
        "minutes,category,date,project\r\n"
        "\r\n"
        "9,Testing,2026-10-19,Lumen\r\n"
        "\r\n"
        "4,Testing,2026-10-20,Lumen\r\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)),
        "Project activity report\nEntries: 2\nTotal minutes: 13\n\n"
        "By project\n- Lumen: 13\n\nBy category\n- Testing: 13\n")


@pytest.mark.parametrize("source,expected", [
    (HEADER,
     "Project activity report\nEntries: 0\nTotal minutes: 0\n\n"
     "By project\n(none)\n\nBy category\n(none)\n"),
    (HEADER + "2026-10-19,Lumen,Testing,0\n",
     "Project activity report\nEntries: 1\nTotal minutes: 0\n\n"
     "By project\n- Lumen: 0\n\nBy category\n- Testing: 0\n"),
], ids=["header-only", "zero-minutes"])
def test_zero_reports(tmp_path, source, expected):
    assert_success(run_cli(input_file(tmp_path, source)), expected)


def test_group_names_use_python_string_order(tmp_path):
    source = HEADER + (
        "2026-10-19,álpha,Ωmega,5\n"
        "2026-10-19,alpha,zed,3\n"
        "2026-10-19,Alpha,Zed,2\n"
        "2026-10-19,_work,zed,0\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)),
        "Project activity report\nEntries: 4\nTotal minutes: 10\n\n"
        "By project\n- Alpha: 2\n- _work: 0\n- alpha: 3\n- álpha: 5\n\n"
        "By category\n- Zed: 2\n- zed: 3\n- Ωmega: 5\n")


def test_repeated_rows_are_counted(tmp_path):
    assert_success(run_cli(input_file(tmp_path, HEADER + VALID_ROW * 3)),
        "Project activity report\nEntries: 3\nTotal minutes: 21\n\n"
        "By project\n- Orion: 21\n\nBy category\n- Development: 21\n")


def test_labels_preserve_spaces_case_commas_and_quotes(tmp_path):
    source = HEADER + csv_record(["2026-10-19", ' Orion, "UI" ', ' Docs, "API" ', "8"])
    source += csv_record(["2026-10-19", "Orion", "docs", "2"])
    assert_success(run_cli(input_file(tmp_path, source)),
        "Project activity report\nEntries: 2\nTotal minutes: 10\n\n"
        'By project\n-  Orion, "UI" : 8\n- Orion: 2\n\n'
        'By category\n-  Docs, "API" : 8\n- docs: 2\n')


def test_calendar_and_ascii_minutes_boundaries(tmp_path):
    source = HEADER + (
        "0001-01-01,Orion,Testing,0007\n"
        "2000-02-29,Orion,Testing,0\n"
        "2024-02-29,Orion,Testing,1000000000000\n"
        "9999-12-31,Orion,Testing,3\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)),
        "Project activity report\nEntries: 4\nTotal minutes: 1000000000010\n\n"
        "By project\n- Orion: 1000000000010\n\n"
        "By category\n- Testing: 1000000000010\n")


@pytest.mark.parametrize("source", [
    "",
    "project,category,minutes\nOrion,Testing,7\n",
    "date,category,minutes\n2026-10-19,Testing,7\n",
    "date,project,minutes\n2026-10-19,Orion,7\n",
    "date,project,category\n2026-10-19,Orion,Testing\n",
    "date,project,category,minutes,minutes\n2026-10-19,Orion,Testing,7,7\n",
    "date,project,category,minutes,note\n2026-10-19,Orion,Testing,7,x\n",
    "date,project,category,Minutes\n2026-10-19,Orion,Testing,7\n",
], ids=["empty", "missing-date", "missing-project", "missing-category",
        "missing-minutes", "duplicate", "extra", "case-mismatch"])
def test_invalid_headers(tmp_path, source):
    assert_input_error(run_cli(input_file(tmp_path, source)), kind=r"header|column|CSV")


@pytest.mark.parametrize("bad_row", [
    "2026-10-20,Orion,Testing\n",
    "2026-10-20,Orion,Testing,3,extra\n",
], ids=["short", "long"])
def test_invalid_row_width_after_valid_row(tmp_path, bad_row):
    result = run_cli(input_file(tmp_path, HEADER + VALID_ROW + bad_row))
    assert_input_error(result, row=3, kind=r"column|cell|field|width|count|CSV|expected")


@pytest.mark.parametrize("date", [
    "2026-2-03", "26-02-03", "2026/02/03", "2026-02-30", "2025-02-29",
    "1900-02-29", "0000-01-01", "2026-13-01", " 2026-10-19",
], ids=["month-width", "year-width", "separator", "impossible-day", "non-leap",
        "century-non-leap", "year-zero", "month-range", "leading-space"])
def test_invalid_dates_after_valid_row(tmp_path, date):
    source = HEADER + VALID_ROW + csv_record([date, "Orion", "Testing", "3"])
    assert_input_error(run_cli(input_file(tmp_path, source)), row=3, field="date")


@pytest.mark.parametrize("minutes", [
    "-1", "+1", "1.0", "1e2", " 1", "1 ", "", "NaN", "١", "１", "1_000",
], ids=["negative", "plus", "decimal", "exponent", "leading-space",
        "trailing-space", "empty", "nan", "arabic-digit", "fullwidth-digit", "underscore"])
def test_invalid_minutes_after_valid_row(tmp_path, minutes):
    source = HEADER + VALID_ROW + csv_record(["2026-10-20", "Orion", "Testing", minutes])
    assert_input_error(run_cli(input_file(tmp_path, source)), row=3, field="minutes")


@pytest.mark.parametrize("field,value", [
    ("project", ""), ("project", "   "), ("category", ""), ("category", "\t "),
], ids=["empty-project", "spaces-project", "empty-category", "whitespace-category"])
def test_blank_labels_after_valid_row(tmp_path, field, value):
    values = {"date": "2026-10-20", "project": "Orion", "category": "Testing", "minutes": "3"}
    values[field] = value
    source = HEADER + VALID_ROW + csv_record(list(values.values()))
    assert_input_error(run_cli(input_file(tmp_path, source)), row=3, field=field)


def test_error_rows_count_csv_records_not_physical_lines(tmp_path):
    source = HEADER + csv_record(["2026-10-19", "Orion\nteam", "Testing", "7"])
    source += "2026-10-20,Orion,Testing,wrong\n"
    assert_input_error(run_cli(input_file(tmp_path, source)), row=3, field="minutes")


@pytest.mark.parametrize("bad_row", [
    '2026-10-20,"Orion,Testing,3\n',
    '2026-10-20,"Orion"junk,Testing,3\n',
], ids=["unterminated-quote", "text-after-quote"])
def test_malformed_csv_after_valid_row(tmp_path, bad_row):
    source = HEADER + VALID_ROW + bad_row
    assert_input_error(run_cli(input_file(tmp_path, source)), kind=r"CSV")


@pytest.mark.parametrize("kind", ["missing", "directory"], ids=["missing-file", "directory"])
def test_unreadable_input(tmp_path, kind):
    path = tmp_path / "missing.csv" if kind == "missing" else tmp_path
    assert_input_error(run_cli(path), kind=r"read|file|UTF-8")


def test_non_utf8_input(tmp_path):
    path = tmp_path / "invalid-encoding.csv"
    path.write_bytes(HEADER.encode("ascii") + b"2026-10-19,Orion,Testing,\xff\n")
    assert_input_error(run_cli(path), kind=r"UTF-8|encoding|read")


def test_help_is_usable():
    result = run_cli("--help")
    assert result.returncode == 0
    assert result.stderr == b""
    help_text = result.stdout.decode("utf-8")
    assert "usage:" in help_text.lower()
    assert "csv" in help_text.lower()


def test_large_minutes_above_decimal_conversion_limit(tmp_path):
    minutes = "1" + "0" * 4299 + "7"
    source = HEADER + f"2026-10-19,Orion,Testing,{minutes}\n"
    expected = (
        f"Project activity report\nEntries: 1\nTotal minutes: {minutes}\n\n"
        f"By project\n- Orion: {minutes}\n\n"
        f"By category\n- Testing: {minutes}\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)), expected)


def test_large_minutes_sum_crosses_decimal_conversion_limit(tmp_path):
    minutes = "9" * 4300
    total = "1" + "0" * 4300
    source = HEADER + (
        f"2026-10-19,Orion,Testing,{minutes}\n"
        "2026-10-20,Orion,Testing,1\n"
    )
    expected = (
        f"Project activity report\nEntries: 2\nTotal minutes: {total}\n\n"
        f"By project\n- Orion: {total}\n\n"
        f"By category\n- Testing: {total}\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)), expected)


@pytest.mark.parametrize("minutes,total", [
    ("0" * 5000 + "7", "7"),
    ("0" * 5001, "0"),
], ids=["nonzero", "zero"])
def test_large_minutes_leading_zeros_render_canonically(tmp_path, minutes, total):
    source = HEADER + f"2026-10-19,Orion,Testing,{minutes}\n"
    expected = (
        f"Project activity report\nEntries: 1\nTotal minutes: {total}\n\n"
        f"By project\n- Orion: {total}\n\n"
        f"By category\n- Testing: {total}\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)), expected)


@pytest.mark.parametrize("minutes", [
    "999999999",
    "1000000000",
    "999999999999999999",
    "1000000000000000001",
], ids=["nine-digits", "ten-digits", "eighteen-digits", "zero-middle-block"])
def test_large_minutes_decimal_block_boundaries(tmp_path, minutes):
    source = HEADER + f"2026-10-19,Orion,Testing,{minutes}\n"
    expected = (
        f"Project activity report\nEntries: 1\nTotal minutes: {minutes}\n\n"
        f"By project\n- Orion: {minutes}\n\n"
        f"By category\n- Testing: {minutes}\n"
    )
    assert_success(run_cli(input_file(tmp_path, source)), expected)
