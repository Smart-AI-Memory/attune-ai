"""Exercise standalone HTML reports and safe output through the public CLI."""

import csv
from html.parser import HTMLParser
import io
import math
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


PROJECT = Path(__file__).resolve().parents[1]
HEADER = "date,project,category,minutes\n"
SAMPLE = PROJECT / "data" / "activity.csv"


def run_cli(path, *options):
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
        [sys.executable, "-B", str(PROJECT / "report.py"), str(path),
         *(str(option) for option in options)],
        cwd=PROJECT, env=env, capture_output=True, timeout=3, check=False,
    )


def input_file(tmp_path, text):
    path = tmp_path / "activity.csv"
    path.write_text(text, encoding="utf-8", newline="")
    return path


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def descendants(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.descendants()

    def text(self, *, visible=False):
        if visible and self.tag in {"head", "style", "script"}:
            return ""
        return " ".join(
            child.text(visible=visible) if isinstance(child, Element) else child
            for child in self.children
        )


class ReportHTML(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.declarations = []
        self.feed(source)
        self.close()

    def handle_decl(self, decl):
        self.declarations.append(decl.lower())

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in self.VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def elements(self, *tags):
        return [node for node in self.root.descendants() if node.tag in tags]

    @property
    def visible_text(self):
        return " ".join(self.root.text(visible=True).split())


def assert_standalone_html(source):
    document = ReportHTML(source)
    assert "doctype html" in document.declarations
    assert len(document.elements("html")) == 1
    assert len(document.elements("body")) == 1
    assert any(node.text().strip() for node in document.elements("title"))
    assert document.elements("h1"), "Give the report a readable main heading"
    assert not document.elements("script", "iframe", "object", "embed")
    for node in document.root.descendants():
        for name, value in node.attrs.items():
            assert not name.lower().startswith("on"), (node.tag, name)
            if name in {"src", "srcset", "href", "action", "formaction", "poster", "data"}:
                assert not re.search(r"https?:|^\s*//|javascript:", value or "", re.I)
        if node.tag == "style":
            assert not re.search(r"@import|url\(\s*['\"]?(?:https?:|//)", node.text(), re.I)
    return document


def assert_html_success(result):
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    return assert_standalone_html(result.stdout.decode("utf-8"))


def contains_number(text, number):
    text = re.sub(r"(?<=\d)[,\u2009\u202f](?=\d)", "", text)
    return re.search(r"(?<!\d)" + re.escape(number) + r"(?!\d)", text) is not None


def assert_summary(document, entries, minutes):
    text = document.visible_text
    assert re.search(r"\bentries\b", text, re.I)
    assert re.search(r"\btotal\s+minutes\b", text, re.I)
    assert contains_number(text, entries)
    assert contains_number(text, minutes)


def assert_group_row(document, label, minutes):
    for table in document.elements("table"):
        for row in table.descendants():
            if row.tag != "tr":
                continue
            cells = [cell for cell in row.descendants() if cell.tag in {"th", "td"}]
            if any(cell.text().strip() == label for cell in cells):
                assert any(contains_number(cell.text(), minutes) for cell in cells)
                return
    pytest.fail(f"Missing table row for {label!r} with {minutes!r} minutes")


def assert_group_sections(document, *, tables=True):
    headings = " ".join(node.text() for node in document.elements("h2", "h3", "caption"))
    assert re.search(r"\bprojects?\b", headings, re.I)
    assert re.search(r"\bcategor(?:y|ies)\b", headings, re.I)
    if tables:
        assert len(document.elements("table")) >= 2
        assert any(re.search(r"\bminutes\b", node.text(), re.I)
                   for node in document.elements("th"))


def assert_date_endpoints(document, first, last):
    dates = [node.attrs.get("datetime") for node in document.elements("time")]
    dates += re.findall(r"\b\d{4}-\d{2}-\d{2}\b", document.visible_text)
    assert first in dates
    assert last in dates
    assert dates.index(first) <= dates.index(last)


def assert_safe_bar_values(document, *, required=False):
    values = []
    for node in document.root.descendants():
        style = node.attrs.get("style", "") or ""
        assert not re.search(r"\b(?:nan|inf(?:inity)?)\b", style, re.I)
        for value in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", style):
            number = float(value)
            assert math.isfinite(number) and 0 <= number <= 100
            values.append(number)
        if node.tag in {"progress", "meter"} or "aria-valuenow" in node.attrs:
            current = float(node.attrs.get("aria-valuenow", node.attrs.get("value", "0")))
            lower = float(node.attrs.get("aria-valuemin", node.attrs.get("min", "0")))
            upper = float(node.attrs.get("aria-valuemax", node.attrs.get("max", "1")))
            assert all(math.isfinite(value) for value in (current, lower, upper))
            assert lower <= current <= upper
            values.append(current)
        if node.tag == "rect" and "width" in node.attrs:
            number = float(node.attrs["width"].rstrip("%"))
            assert math.isfinite(number) and number >= 0
            if node.attrs["width"].endswith("%"):
                assert number <= 100
            values.append(number)
    if required:
        assert values, "Expose bounded chart proportions through standard HTML or CSS values"


def test_html_stdout_contains_sample_summary_groups_and_date_range():
    document = assert_html_success(run_cli(SAMPLE, "--format", "html"))
    assert_summary(document, "6", "270")
    assert_group_sections(document)
    for label, minutes in (
        ("Lumen", "90"), ("Orion", "180"), ("Development", "150"),
        ("Documentation", "75"), ("Testing", "45"),
    ):
        assert_group_row(document, label, minutes)
    assert_date_endpoints(document, "2026-10-19", "2026-10-21")
    assert_safe_bar_values(document, required=True)


def test_html_escapes_untrusted_labels_without_active_content(tmp_path):
    project = '<script>alert("project")</script> & <b>Orion</b>'
    category = '<img src="https://example.invalid/x" onerror="alert(1)"> "Docs"'
    source = io.StringIO(newline="")
    writer = csv.writer(source, lineterminator="\n")
    writer.writerow(["date", "project", "category", "minutes"])
    writer.writerow(["2026-10-19", project, category, "7"])
    document = assert_html_success(run_cli(input_file(tmp_path, source.getvalue()), "--format", "html"))
    assert not document.elements("script", "img")
    assert_group_row(document, project, "7")
    assert_group_row(document, category, "7")


@pytest.mark.parametrize("source,entries", [
    (HEADER, "0"),
    (HEADER + "2026-10-19,Lumen,Testing,0\n", "1"),
], ids=["header-only", "zero-minutes"])
def test_html_zero_reports_are_readable_and_have_safe_proportions(tmp_path, source, entries):
    document = assert_html_success(run_cli(input_file(tmp_path, source), "--format", "html"))
    assert_summary(document, entries, "0")
    assert_group_sections(document, tables=entries != "0")
    assert_safe_bar_values(document)
    if entries == "1":
        assert_group_row(document, "Lumen", "0")
        assert_group_row(document, "Testing", "0")
        assert_date_endpoints(document, "2026-10-19", "2026-10-19")


def test_html_date_range_uses_calendar_extremes_not_record_order(tmp_path):
    source = HEADER + (
        "2026-10-21,Orion,Testing,1\n"
        "2026-10-19,Orion,Testing,2\n"
        "2026-10-20,Orion,Testing,3\n"
    )
    document = assert_html_success(run_cli(input_file(tmp_path, source), "--format", "html"))
    assert_date_endpoints(document, "2026-10-19", "2026-10-21")
    assert_summary(document, "3", "6")


def test_html_large_minutes_are_exact_and_chart_widths_stay_bounded(tmp_path):
    minutes = "1" + "0" * 4299 + "7"
    total = "1" + "0" * 4299 + "8"
    source = HEADER + (
        f"2026-10-19,Orion,Development,{minutes}\n"
        "2026-10-20,Lumen,Testing,1\n"
    )
    document = assert_html_success(run_cli(input_file(tmp_path, source), "--format", "html"))
    assert_summary(document, "2", total)
    assert_group_row(document, "Orion", minutes)
    assert_group_row(document, "Development", minutes)
    assert_group_row(document, "Lumen", "1")
    assert_group_row(document, "Testing", "1")
    assert_safe_bar_values(document, required=True)


def test_html_output_creates_new_file_and_prints_only_confirmation(tmp_path):
    output = tmp_path / "activity report.html"
    result = run_cli(SAMPLE, "--format", "html", "--output", output)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    assert result.stdout == f"Saved report to {output}\n".encode("utf-8")
    document = assert_standalone_html(output.read_text(encoding="utf-8"))
    assert_summary(document, "6", "270")
    assert_group_row(document, "Orion", "180")


@pytest.mark.parametrize("explicit_format", [False, True], ids=["default-text", "explicit-text"])
def test_text_output_option_preserves_exact_report(tmp_path, explicit_format):
    output = tmp_path / "report.txt"
    options = ["--output", output]
    if explicit_format:
        options += ["--format", "text"]
    result = run_cli(SAMPLE, *options)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    assert result.stdout == f"Saved report to {output}\n".encode("utf-8")
    assert output.read_bytes() == (PROJECT / "expected" / "activity-report.txt").read_bytes()


def test_explicit_text_stdout_preserves_exact_report():
    result = run_cli(SAMPLE, "--format", "text")
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    assert result.stdout == (PROJECT / "expected" / "activity-report.txt").read_bytes()


@pytest.mark.parametrize("source", [
    "",
    HEADER + "2026-10-19,Orion,Development,7\n2026-10-20,Orion,Testing,-1\n",
    HEADER + "2026-10-19,Orion,Development,7\n2026-02-30,Orion,Testing,3\n",
    HEADER + '2026-10-19,Orion,Development,7\n2026-10-20,"Orion,Testing,3\n',
], ids=["empty", "minutes", "date", "malformed-csv"])
@pytest.mark.parametrize("save", [False, True], ids=["stdout", "new-file"])
def test_invalid_csv_emits_no_partial_html_or_output_file(tmp_path, source, save):
    path = input_file(tmp_path, source)
    output = tmp_path / "invalid-report.html"
    options = ["--format", "html"]
    if save:
        options += ["--output", output]
    result = run_cli(path, *options)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"Input error:")
    assert b"Traceback" not in result.stderr
    assert not output.exists()
    assert path.read_bytes() == source.encode("utf-8")


@pytest.mark.parametrize("target", ["existing-output", "input-file"], ids=["existing-output", "input-file"])
def test_output_refusal_preserves_existing_output_and_input(tmp_path, target):
    source = HEADER + "2026-10-19,Orion,Testing,7\n"
    path = input_file(tmp_path, source)
    output = tmp_path / "report.html" if target == "existing-output" else path
    if target == "existing-output":
        output.write_bytes(b"Existing report must survive.\n")
    before = output.read_bytes()
    result = run_cli(path, "--format", "html", "--output", output)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.strip()
    assert b"Traceback" not in result.stderr
    assert output.read_bytes() == before
    assert path.read_bytes() == source.encode("utf-8")
