#!/usr/bin/env python3
"""Score src/attune modules by customer-facing risk × coverage gap.

See docs/specs/test-quality-program/design.md §Prioritization rubric
for the customer-weight table and risk-multiplier rules.

Usage:
    python scripts/score_test_quality.py [path/to/coverage.xml]

Output:
    docs/specs/test-quality-program/rubric_cache.csv (sorted desc)

If coverage.xml is missing, every module gets coverage_gap=1.0.
The relative ordering of customer_weight × risk_multiplier still
surfaces a defensible first working set; refresh after a fresh
`pytest --cov=src/attune --cov-report=xml` for sharper gap data.
"""

from __future__ import annotations

import csv
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "attune"
OUTPUT_CSV = REPO_ROOT / "docs" / "specs" / "test-quality-program" / "rubric_cache.csv"


# Customer weight rules: (pattern, weight). First match wins.
# Patterns are POSIX paths relative to repo root. `**` matches any
# number of segments; `*` matches one segment. Default weight is 1.
WEIGHT_RULES: list[tuple[str, int]] = [
    # 5 — User-invoked directly (CLI / MCP / Ops entry points,
    # workflow class files users invoke via `attune workflow run`)
    ("src/attune/cli_minimal.py", 5),
    ("src/attune/cli_router.py", 5),
    ("src/attune/cli_commands/*.py", 5),
    ("src/attune/mcp/server.py", 5),
    ("src/attune/mcp/workflow_handlers.py", 5),
    ("src/attune/mcp/memory_handlers.py", 5),
    ("src/attune/ops/server.py", 5),
    ("src/attune/ops/cli.py", 5),
    ("src/attune/ops/routes/*.py", 5),
    ("src/attune/workflows/bug_predict.py", 5),
    ("src/attune/workflows/code_review.py", 5),
    ("src/attune/workflows/deep_review.py", 5),
    ("src/attune/workflows/dependency_check.py", 5),
    ("src/attune/workflows/documentation_orchestrator.py", 5),
    ("src/attune/workflows/refactor_plan.py", 5),
    # 4 — Workflow helpers shaping user-visible output
    ("src/attune/workflows/*_report.py", 4),
    ("src/attune/workflows/*_patterns.py", 4),
    ("src/attune/workflows/*_audit.py", 4),
    ("src/attune/workflows/*_parsers.py", 4),
    ("src/attune/workflows/doc_audit/**/*.py", 4),
    ("src/attune/workflows/doc_orch_*.py", 4),
    ("src/attune/workflows/test_gen/**/*.py", 4),
    ("src/attune/workflows/document_gen/**/*.py", 4),
    # 2 — Middleware, validators, security boundaries
    # (must precede the broader 3 rules for security/agents/models)
    ("src/attune/security/**/*.py", 2),
    ("src/attune/mcp/rate_limiter.py", 2),
    ("src/attune/ops/middleware.py", 2),
    ("src/attune/hooks/**/*.py", 2),
    # 3 — Composed by user-invoked code
    ("src/attune/agents/**/*.py", 3),
    ("src/attune/models/**/*.py", 3),
    ("src/attune/workflows/**/*.py", 3),
    ("src/attune/memory/**/*.py", 3),
    ("src/attune/ops/data.py", 3),
    ("src/attune/ops/config.py", 3),
    # 1 — Deep plumbing (everything else, including data_classes,
    # mixins, registries, internal helpers)
]


# Risk multiplier rules: (pattern, multiplier). First match wins.
# Default is 1.0.
RISK_RULES: list[tuple[str, float]] = [
    # 2.0 — security-sensitive
    ("src/attune/security/**/*.py", 2.0),
    ("src/attune/mcp/rate_limiter.py", 2.0),
    ("src/attune/mcp/server.py", 2.0),
    ("src/attune/ops/middleware.py", 2.0),
    ("src/attune/hooks/scripts/security*.py", 2.0),
    ("src/attune/models/auth*.py", 2.0),
    ("src/attune/models/auth_*.py", 2.0),
    # 1.5 — data-handling
    ("src/attune/memory/**/*.py", 1.5),
    ("src/attune/telemetry/**/*.py", 1.5),
    ("src/attune/ops/data.py", 1.5),
]


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a `**`/`*`-style glob to a compiled regex.

    `**` matches any number of path segments (including zero);
    `*` matches a single segment (no `/`).
    """
    out = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 3] == "**/":
            out.append("(?:.*/)?")
            i += 3
        elif pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] in ".+()[]{}|^$\\":
            out.append(re.escape(pattern[i]))
            i += 1
        else:
            out.append(pattern[i])
            i += 1
    return re.compile("^" + "".join(out) + "$")


_WEIGHT_PATTERNS = [(_glob_to_regex(p), w) for p, w in WEIGHT_RULES]
_RISK_PATTERNS = [(_glob_to_regex(p), r) for p, r in RISK_RULES]


def load_coverage_omits() -> list[re.Pattern[str]]:
    """Parse `[tool.coverage.run] omit = [...]` from pyproject.toml.

    Returns compiled regexes for each non-meta omit entry. Meta
    entries (`*/tests/*`, `*/test_*.py`, `*/__pycache__/*`,
    `*/site-packages/*`) are skipped — they don't represent
    production source we'd ever consider for the working set.
    """
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return []
    text = pyproject.read_text(encoding="utf-8")
    # Find the omit block
    m = re.search(
        r"\[tool\.coverage\.run\][\s\S]*?omit\s*=\s*\[([\s\S]*?)\]",
        text,
    )
    if not m:
        return []
    body = m.group(1)
    meta = {"*/tests/*", "*/test_*.py", "*/__pycache__/*", "*/site-packages/*"}
    patterns: list[re.Pattern[str]] = []
    for line in body.splitlines():
        m2 = re.match(r'\s*"([^"]+)"', line)
        if not m2:
            continue
        pat = m2.group(1)
        if pat in meta:
            continue
        patterns.append(_glob_to_regex(pat))
    return patterns


_OMIT_PATTERNS = load_coverage_omits()


def is_excluded(rel_path: str) -> bool:
    """True if rel_path matches any `[tool.coverage.run] omit` pattern."""
    for regex in _OMIT_PATTERNS:
        if regex.match(rel_path):
            return True
    return False


def classify_weight(rel_path: str) -> int:
    for regex, weight in _WEIGHT_PATTERNS:
        if regex.match(rel_path):
            return weight
    return 1


def classify_risk(rel_path: str) -> float:
    for regex, risk in _RISK_PATTERNS:
        if regex.match(rel_path):
            return risk
    return 1.0


def load_coverage(coverage_xml: Path) -> dict[str, float]:
    """Parse coverage.xml and return {filename: line_rate}.

    `filename` is whatever the XML records — typically a path
    relative to the coverage `source` root.
    """
    if not coverage_xml.exists():
        return {}
    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    result: dict[str, float] = {}
    for cls in root.iter("class"):
        filename = cls.get("filename")
        rate = cls.get("line-rate")
        if filename and rate is not None:
            try:
                result[filename] = float(rate)
            except ValueError:
                continue
    return result


def lookup_coverage(py: Path, coverage: dict[str, float]) -> float | None:
    """Try the common key shapes coverage.xml uses for a source file."""
    rel = py.relative_to(REPO_ROOT).as_posix()
    rel_src = py.relative_to(SRC_ROOT.parent).as_posix()
    rel_pkg = py.relative_to(SRC_ROOT).as_posix()
    for key in (rel, rel_src, rel_pkg, str(py)):
        if key in coverage:
            return coverage[key]
    return None


def collect_rows(coverage: dict[str, float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for py in SRC_ROOT.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(REPO_ROOT).as_posix()
        module = py.relative_to(SRC_ROOT).as_posix()

        weight = classify_weight(rel)
        risk = classify_risk(rel)
        # `[tool.coverage.run] omit` patterns commonly use `*/` prefix;
        # match against both the repo-relative path and the bare
        # module path.
        excluded = is_excluded(rel) or is_excluded("*/" + module)
        line_rate = lookup_coverage(py, coverage)
        gap = 1.0 - line_rate if line_rate is not None else 1.0
        covered_pct = f"{line_rate * 100:.1f}" if line_rate is not None else "?"
        # Excluded modules score 0 so they sink to the bottom but
        # remain visible in the CSV for audit purposes.
        score = 0.0 if excluded else weight * gap * risk
        last_mod = datetime.fromtimestamp(py.stat().st_mtime).strftime("%Y-%m-%d")
        rows.append(
            {
                "module": module,
                "customer_weight": weight,
                "coverage_gap": round(gap, 3),
                "risk_multiplier": risk,
                "score": round(score, 3),
                "covered_pct": covered_pct,
                "excluded": "yes" if excluded else "",
                "last_modified": last_mod,
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["module"]))
    return rows


def write_csv(rows: list[dict[str, object]], source_note: str) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    header_note = (
        f"# Generated by scripts/score_test_quality.py "
        f"on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"# Coverage source: {source_note}\n"
        f"# See docs/specs/test-quality-program/design.md "
        f"§Prioritization rubric for the scoring formula.\n"
    )
    with OUTPUT_CSV.open("w", newline="") as f:
        f.write(header_note)
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_top(rows: list[dict[str, object]], n: int = 20) -> None:
    print(f"\nTop {n} candidates by score (customer_weight × gap × risk):\n")
    print(f"  {'score':>6}  {'w':>2}  {'gap':>4}  {'risk':>4}  " f"{'cov%':>5}  module")
    print("  " + "-" * 72)
    for r in rows[:n]:
        print(
            f"  {r['score']:>6.2f}  {r['customer_weight']:>2}  "
            f"{r['coverage_gap']:>4.2f}  {r['risk_multiplier']:>4.1f}  "
            f"{str(r['covered_pct']):>5}  {r['module']}"
        )


def main() -> int:
    coverage_xml = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO_ROOT / "coverage.xml"
    coverage = load_coverage(coverage_xml)
    if coverage:
        try:
            source_note = str(coverage_xml.relative_to(REPO_ROOT))
        except ValueError:
            source_note = str(coverage_xml)
    else:
        source_note = "(none — all coverage_gap defaulted to 1.0)"

    rows = collect_rows(coverage)
    if not rows:
        print("No source files found under src/attune/", file=sys.stderr)
        return 1

    write_csv(rows, source_note)
    rel_out = OUTPUT_CSV.relative_to(REPO_ROOT)
    print(f"Wrote {len(rows)} rows to {rel_out}")
    print(f"Coverage source: {source_note}")
    print_top(rows, n=20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
