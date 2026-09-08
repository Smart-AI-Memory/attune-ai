"""Gate: no parser call sits under a handler set that misses what it raises.

Library-review class C4b is the general sibling of C4a (``ast.parse`` +
``ValueError``): ``yaml.safe_load`` raises ``YAMLError``,
``datetime.fromisoformat`` raises ``ValueError``, ``ast.parse`` raises
``ValueError`` on 3.10/3.11. A ``try`` that names only OSError, KeyError
or another sibling lets the parser's own exception escape a handler that
was written to contain it. The instances were fixed in PR #2121 and the
class has carried zero hits since — with no gate, which the register
reports as FIXED-BUT-UNGATED (#2310): nothing stopped the class from
returning.

This gate binds C4b to its calibrated rule R7a (precision 1.0 on the
#2121 fix-set) run over the shipped tree minus recorded dispositions,
and pins the rule's discriminators as fixtures so a later simplification
cannot drop them. Scan errors fail the gate: absence is not a pass
(contract principle 7).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0

Register-Class: C4b
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from attune.classes.register import derive_register
from attune.classes.rules import scan_source

REPO_ROOT = Path(__file__).resolve().parents[3]
RULE = "R7a-parse-under-narrow-except"


def _hits(source: str):
    return [h for h in scan_source(textwrap.dedent(source), "probe.py") if h.rule_id == RULE]


def test_no_parser_outside_its_handler_set() -> None:
    """The shipped tree carries no C4b site the review has not dispositioned."""
    register = derive_register(repo_root=REPO_ROOT)
    assert not register["scan_errors"], register["scan_errors"]
    assert not register["disposition_problems"], register["disposition_problems"]
    row = next(r for r in register["rows"] if r["class_id"] == "C4b")
    assert row["calibrated_hits"] == 0, row
    assert row["advisory_hits"] == 0, row
    assert row["gate_problem"] is None, row
    assert row["status"] == "CLOSED", row


# --- discriminators, pinned ------------------------------------------------


def test_yaml_under_a_sibling_handler_is_a_hit() -> None:
    src = """
        import yaml
        try:
            cfg = yaml.safe_load(text)
        except OSError:
            cfg = None
    """
    hits = _hits(src)
    assert hits and "YAMLError" in hits[0].detail


def test_yaml_under_its_own_error_is_clean() -> None:
    src = """
        import yaml
        try:
            cfg = yaml.safe_load(text)
        except (OSError, yaml.YAMLError):
            cfg = None
    """
    assert not _hits(src)


def test_fromisoformat_under_keyerror_is_a_hit() -> None:
    src = """
        from datetime import datetime
        try:
            when = datetime.fromisoformat(row["ts"])
        except KeyError:
            when = None
    """
    hits = _hits(src)
    assert hits and "ValueError" in hits[0].detail


def test_fromisoformat_under_valueerror_is_clean() -> None:
    src = """
        from datetime import datetime
        try:
            when = datetime.fromisoformat(row["ts"])
        except (KeyError, ValueError):
            when = None
    """
    assert not _hits(src)


def test_ast_parse_under_syntaxerror_only_is_a_hit() -> None:
    """The C4a instance is also a C4b instance; both gates must agree."""
    src = """
        import ast
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = None
    """
    hits = _hits(src)
    assert hits and "ValueError" in hits[0].detail


def test_catch_all_handler_is_clean() -> None:
    src = """
        import yaml
        try:
            cfg = yaml.safe_load(text)
        except Exception:
            cfg = None
    """
    assert not _hits(src)


def test_json_is_the_other_rule_s_domain() -> None:
    """``json.loads`` raises ``JSONDecodeError`` (a ValueError); R7a carries no
    expectation for it by design — non-object JSON is R7b's class (C3)."""
    src = """
        import json
        try:
            data = json.loads(text)
        except OSError:
            data = None
    """
    assert not _hits(src)
