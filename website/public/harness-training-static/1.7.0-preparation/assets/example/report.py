"""Generate a project activity report from validated CSV records."""

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from html import escape
import io
from pathlib import Path
import re
import sys


class InputError(ValueError):
    """CSV input cannot produce a complete report."""


@dataclass
class _ReportData:
    entries: int
    total_minutes: int
    project_totals: dict[str, int]
    category_totals: dict[str, int]
    first_date: date | None
    last_date: date | None


def _parse_minutes(text: str) -> int:
    """Convert validated digits using small decimal blocks."""
    value = 0
    for start in range(0, len(text), 9):
        block = text[start:start + 9]
        value = value * 10 ** len(block) + int(block)
    return value


def _format_minutes(value: int) -> str:
    """Render nonnegative totals without a large decimal conversion."""
    if value == 0:
        return "0"
    blocks = []
    while value:
        value, remainder = divmod(value, 1_000_000_000)
        blocks.append(f"{remainder:09d}")
    return "".join(reversed(blocks)).lstrip("0")


def _aggregate_records(csv_text: str) -> _ReportData:
    """Validate all records and collect data shared by both output formats."""
    required_columns = {"date", "project", "category", "minutes"}
    reader = csv.reader(io.StringIO(csv_text, newline=""), strict=True)
    header = None
    row_number = 0
    entries = 0
    total_minutes = 0
    project_totals = {}
    category_totals = {}
    first_date = None
    last_date = None

    try:
        for record in reader:
            if not record:
                continue
            row_number += 1

            if header is None:
                if len(record) != len(required_columns) or set(record) != required_columns:
                    raise InputError(
                        "header must contain exactly date, project, category and "
                        "minutes columns, each once"
                    )
                header = record
                continue

            if len(record) != len(header):
                raise InputError(
                    f"row {row_number}: expected {len(header)} columns, "
                    f"found {len(record)}"
                )
            values = dict(zip(header, record))

            date_text = values["date"]
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_text) is None:
                raise InputError(f"row {row_number}: date must use YYYY-MM-DD")
            try:
                record_date = date.fromisoformat(date_text)
            except ValueError as exc:
                raise InputError(
                    f"row {row_number}: date is not a real calendar date"
                ) from exc

            for field in ("project", "category"):
                if not values[field].strip():
                    raise InputError(
                        f"row {row_number}: {field} must contain non-whitespace text"
                    )

            minutes_text = values["minutes"]
            if re.fullmatch(r"[0-9]+", minutes_text) is None:
                raise InputError(
                    f"row {row_number}: minutes must be a nonnegative whole "
                    "number using ASCII digits"
                )
            minutes = _parse_minutes(minutes_text)

            project = values["project"]
            category = values["category"]
            entries += 1
            total_minutes += minutes
            project_totals[project] = project_totals.get(project, 0) + minutes
            category_totals[category] = category_totals.get(category, 0) + minutes
            if first_date is None or record_date < first_date:
                first_date = record_date
            if last_date is None or record_date > last_date:
                last_date = record_date
    except csv.Error as exc:
        raise InputError(f"row {row_number + 1}: invalid CSV: {exc}") from exc

    if header is None:
        raise InputError(
            "CSV header is missing; expected date, project, category and minutes columns"
        )

    return _ReportData(
        entries, total_minutes, project_totals, category_totals, first_date, last_date
    )


def _render_text(data: _ReportData) -> str:
    lines = [
        "Project activity report",
        f"Entries: {data.entries}",
        f"Total minutes: {_format_minutes(data.total_minutes)}",
    ]
    for heading, totals in (
        ("By project", data.project_totals),
        ("By category", data.category_totals),
    ):
        lines.extend(["", heading])
        if totals:
            lines.extend(
                f"- {name}: {_format_minutes(totals[name])}" for name in sorted(totals)
            )
        else:
            lines.append("(none)")
    return "\n".join(lines) + "\n"


def render_report(csv_text: str) -> str:
    """Validate every record before returning the complete text report."""
    return _render_text(_aggregate_records(csv_text))


def _percentage(minutes: int, total: int) -> str:
    """Format a bounded percentage without converting large integers to floats."""
    hundredths = minutes * 10_000 // total if total else 0
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def _render_table(heading: str, group: str, totals: dict[str, int], total: int) -> str:
    rows = []
    for name in sorted(totals):
        minutes = _format_minutes(totals[name])
        percentage = _percentage(totals[name], total)
        rows.append(
            f'<tr><th scope="row" class="group-name">{escape(name)}</th>'
            f'<td class="minutes">{minutes}</td>'
            f'<td><span class="share-value">{percentage}%</span>'
            '<span class="bar-track" aria-hidden="true">'
            f'<span class="bar" style="width: {percentage}%"></span>'
            '</span></td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="3" class="empty-state">No activity recorded.</td></tr>')
    return (
        f'<section aria-labelledby="by-{group}">\n'
        f'<h2 id="by-{group}">{heading}</h2>\n'
        '<div class="table-wrap"><table>\n'
        f'<caption>Recorded minutes and share of total time by {group}.</caption>\n'
        '<thead><tr>'
        f'<th scope="col">{group.capitalize()}</th>'
        '<th scope="col">Minutes</th><th scope="col">Share of total</th>'
        '</tr></thead>\n<tbody>\n'
        + "\n".join(rows)
        + '\n</tbody></table></div>\n</section>'
    )


_REPORT_CSS = """
:root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #243831; background: #f7f4ec; }
* { box-sizing: border-box; }
body { margin: 0; line-height: 1.6; }
main { max-width: 1060px; margin: 0 auto; padding: 48px 32px; }
header { padding: 30px 34px; border-radius: 10px; color: #f7f4ec; background: #143e34; }
.eyebrow { margin: 0 0 8px; color: #d5e2cd; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; }
h1 { margin: 0; font-size: clamp(28px, 4vw, 40px); line-height: 1.2; letter-spacing: -.025em; }
.date-range { margin: 16px 0 0; color: #e3e9dc; }
.summary { display: grid; grid-template-columns: 2fr 1.5fr 1fr; gap: 16px; margin: 24px 0 36px; }
.summary > div { min-width: 0; padding: 20px; border: 1px solid #d5ddcd; border-radius: 8px; background: #fffdf8; }
dt { font-size: 13px; font-weight: 600; color: #52654f; }
dd { margin: 6px 0 0; font-size: 24px; font-weight: 650; line-height: 1.4; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
section { margin-top: 32px; }
h2 { margin: 0 0 8px; color: #143e34; font-size: 23px; }
.table-wrap { width: 100%; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; background: #fffdf8; }
caption { padding: 0 0 12px; text-align: left; font-size: 14px; color: #52654f; }
th, td { padding: 14px 16px; border-bottom: 1px solid #d5ddcd; text-align: left; vertical-align: top; }
thead th { background: #e6ecdf; color: #284e3b; font-size: 13px; }
thead th:first-child { width: 43%; }
thead th:nth-child(2) { width: 30%; }
thead th:nth-child(3) { width: 27%; }
tbody th { font-weight: 500; }
.group-name { white-space: pre-wrap; overflow-wrap: anywhere; }
.minutes { overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.share-value { font-size: 14px; font-variant-numeric: tabular-nums; }
.bar-track { display: block; height: 9px; margin-top: 8px; border: 1px solid #b8cbb3; border-radius: 3px; overflow: hidden; background: #e8eddf; }
.bar { display: block; height: 100%; background: #31654a; }
.empty-state { color: #52654f; }
.report-note { margin: 28px 0 0; color: #52654f; font-size: 13px; }
@media (max-width: 640px) {
  main { padding: 20px 16px; }
  header { padding: 24px 20px; }
  .summary { grid-template-columns: 1fr; gap: 10px; margin-bottom: 28px; }
  .summary > div { padding: 14px 18px; }
  dd { font-size: 22px; }
  th, td { padding: 12px 8px; font-size: 14px; }
  thead th:first-child { width: 38%; }
  thead th:nth-child(2) { width: 32%; }
  thead th:nth-child(3) { width: 30%; }
}
@page { margin: 18mm; }
@media print {
  :root { background: white; color: #172c20; font-size: 10pt; }
  main { max-width: none; padding: 0; }
  header { padding: 0 0 18px; border-bottom: 2px solid #143e34; border-radius: 0; color: #143e34; background: white; }
  .eyebrow, .date-range { color: #344b39; }
  h1 { font-size: 25pt; }
  h2 { break-after: avoid; font-size: 17pt; }
  .summary { grid-template-columns: 2fr 1.5fr 1fr; gap: 10px; }
  .summary > div { padding: 12px; }
  dd { font-size: 16pt; }
  table { font-size: 10pt; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; }
  .bar-track, .bar { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
}
""".strip()


def _render_html(data: _ReportData) -> str:
    hours, remaining_minutes = divmod(data.total_minutes, 60)
    if data.first_date is None:
        date_range = "No activity dates recorded."
    else:
        months = (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        )
        first = data.first_date.isoformat()
        last = data.last_date.isoformat()
        first_label = f"{data.first_date.day} {months[data.first_date.month - 1]} {data.first_date.year}"
        last_label = f"{data.last_date.day} {months[data.last_date.month - 1]} {data.last_date.year}"
        if data.first_date == data.last_date:
            date_range = f'Date range: <time datetime="{first}">{first_label}</time>'
        elif (data.first_date.year, data.first_date.month) == (data.last_date.year, data.last_date.month):
            date_range = (
                f'Date range: <time datetime="{first}">{data.first_date.day}</time>–'
                f'<time datetime="{last}">{last_label}</time>'
            )
        else:
            date_range = (
                f'Date range: <time datetime="{first}">{first_label}</time> to '
                f'<time datetime="{last}">{last_label}</time>'
            )
    project_table = _render_table("By project", "project", data.project_totals, data.total_minutes)
    category_table = _render_table("By category", "category", data.category_totals, data.total_minutes)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project activity report</title>
<style>
{_REPORT_CSS}
</style>
</head>
<body>
<main>
<header>
<p class="eyebrow">Activity summary</p>
<h1>Project activity report</h1>
<p class="date-range">{date_range}</p>
</header>
<dl class="summary" aria-label="Report summary">
<div><dt>Total time</dt><dd>{_format_minutes(hours)} hours {remaining_minutes} minutes</dd></div>
<div><dt>Total minutes</dt><dd>{_format_minutes(data.total_minutes)}</dd></div>
<div><dt>Entries</dt><dd>{data.entries}</dd></div>
</dl>
{project_table}
{category_table}
<p class="report-note">All totals include every validated CSV entry. Shares are rounded down to two decimal places; visual bars show the same shares.</p>
</main>
</body>
</html>
"""


def render_html_report(csv_text: str) -> str:
    """Validate every record before returning a standalone HTML report."""
    return _render_html(_aggregate_records(csv_text))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Summarize project activity from a CSV file.")
    parser.add_argument("csv_file", type=Path, help="UTF-8 activity CSV")
    parser.add_argument(
        "--format", choices=("text", "html"), default="text",
        help="report format (default: text)",
    )
    parser.add_argument(
        "--output", type=Path,
        help="create a new UTF-8 report file; existing files are not overwritten",
    )
    args = parser.parse_args(argv)
    try:
        with args.csv_file.open(encoding="utf-8", newline="") as csv_file:
            csv_text = csv_file.read()
    except (OSError, UnicodeError):
        print("Input error: cannot read the input as UTF-8 CSV", file=sys.stderr)
        return 2
    try:
        data = _aggregate_records(csv_text)
        report = _render_html(data) if args.format == "html" else _render_text(data)
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8", newline="\n") as output_file:
                output_file.write(report)
        except FileExistsError:
            print("Output error: the output path already exists; choose a new path", file=sys.stderr)
            return 2
        except (OSError, UnicodeError):
            print("Output error: cannot create and write the report file", file=sys.stderr)
            return 2
        sys.stdout.write(f"Saved report to {args.output}\n")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
