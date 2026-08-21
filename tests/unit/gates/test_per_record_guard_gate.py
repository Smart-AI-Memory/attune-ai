"""Gate: a loop that declares per-record tolerance must honour it
(library-review class G2).

The shape, from ``file_stash._load_records`` pre-fix:

    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue                              # per-record SKIP guard
        ts = datetime.fromisoformat(rec["ts"])    # raises, OUTSIDE the guard
        records.append(rec)

The ``except ... : continue`` is a promise: a bad record is skipped, the
rest survive. A bare coercion right after breaks that promise, because
**well-formed JSON can still carry a badly-typed field**. The guard
catches ``JSONDecodeError``; ``int("abc")`` raises ``ValueError``, which
sails past it and out of the function. One bad line then costs every
good record in the file — silently, since the caller usually degrades.

Confirmed by executed repro (2026-08-21), ``read_memory_summary`` over
three records whose middle one carried ``{"est_tokens": "abc"}``::

    pre-fix : ValueError: invalid literal for int() with base 10: 'abc'
    post-fix: total_events 3, total_est_tokens 30   (10 + 0 + 20)

The fix is NOT to widen the ``try``. It is to make the coercion TOTAL —
``_as_int`` / ``_as_float`` / ``_to_day`` return a default instead of
raising — so per-record tolerance is a property of the helper rather
than of every call site remembering to wrap it.

**Why the rule keys on record data.** It fires only when the coerced
value comes out of a parsed record (a ``.get(...)`` or a subscript).
That discriminator was derived empirically: the naive "any int()/float()
after a skip guard" rule found 6 sites, of which 2 were lookalikes —
``int(elapsed * 1000)`` on floats and ``int(m.group(1))`` on a ``(\\d+)``
capture, neither of which can raise. Adding the discriminator took the
rule to 4 hits, 4 real, zero false positives.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOTS = (REPO_ROOT / "src" / "attune", REPO_ROOT / "attune_redis")

#: Coercions that raise on malformed input. Deliberately a short, known
#: list — "anything that might raise" would be all false positives.
_RAISERS = {
    "fromisoformat",
    "fromtimestamp",
    "utcfromtimestamp",
    "strptime",
    "loads",
    "int",
    "float",
}


def _handler_continues(handler: ast.ExceptHandler) -> bool:
    """A handler that SKIPS this record rather than aborting the loop."""
    return any(isinstance(s, ast.Continue) for s in ast.walk(handler))


def _reads_record_data(call: ast.Call) -> bool:
    """True if the coercion's argument comes out of a parsed record."""
    for sub in ast.walk(call):
        if isinstance(sub, ast.Subscript):
            return True
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr == "get":
                return True
    return False


def _inside_any_try_body(node: ast.AST, tries: list[ast.Try]) -> bool:
    for t in tries:
        for stmt in t.body:
            for sub in ast.walk(stmt):
                if sub is node:
                    return True
    return False


def _call_name(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _offending_sites(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []

    hits: list[str] = []
    for loop in ast.walk(tree):
        if not isinstance(loop, ast.For | ast.AsyncFor):
            continue
        guards = [
            s
            for s in loop.body
            if isinstance(s, ast.Try) and any(_handler_continues(h) for h in s.handlers)
        ]
        if not guards:
            continue
        all_tries = [s for s in ast.walk(loop) if isinstance(s, ast.Try)]
        for stmt in loop.body:
            if isinstance(stmt, ast.Try):
                continue
            for sub in ast.walk(stmt):
                if not isinstance(sub, ast.Call) or _call_name(sub) not in _RAISERS:
                    continue
                if _inside_any_try_body(sub, all_tries) or not _reads_record_data(sub):
                    continue
                hits.append(
                    f"{_label(path)}:{sub.lineno}  {_call_name(sub)}(...) on record data, "
                    f"outside the per-record guard at line {guards[0].lineno}"
                )
    return hits


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shipped_modules() -> list[Path]:
    out: list[Path] = []
    for root in SRC_ROOTS:
        if root.exists():
            out.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def test_no_unguarded_per_record_coercion() -> None:
    """A loop promising to skip bad records must not raise on one."""
    offenders: list[str] = []
    for module in _shipped_modules():
        offenders.extend(_offending_sites(module))

    assert not offenders, (
        "Per-record coercion outside the per-record guard (class G2):\n  "
        + "\n  ".join(offenders)
        + "\n\nThe loop's `except ...: continue` promises a bad record is "
        "skipped, but well-formed JSON can still carry a badly-typed field: "
        "int('abc') raises ValueError past a JSONDecodeError handler and out "
        "of the function, costing every good record in the file.\n"
        "Do NOT widen the try — make the coercion total, as "
        "attune.ops.data._as_int / _as_float / _to_day do."
    )


def test_rule_flags_the_class(tmp_path: Path) -> None:
    """The canonical shape must fire."""
    module = tmp_path / "offender.py"
    module.write_text(
        "import json\n"
        "def load(lines):\n"
        "    out = []\n"
        "    for line in lines:\n"
        "        try:\n"
        "            rec = json.loads(line)\n"
        "        except json.JSONDecodeError:\n"
        "            continue\n"
        "        n = int(rec.get('n'))\n"
        "        out.append(n)\n"
        "    return out\n",
        encoding="utf-8",
    )
    assert _offending_sites(module), "rule missed the canonical G2 shape"


def test_rule_clears_a_total_coercion(tmp_path: Path) -> None:
    """Routing through a total helper is the fix, and must pass."""
    module = tmp_path / "fixed.py"
    module.write_text(
        "import json\n"
        "def load(lines):\n"
        "    out = []\n"
        "    for line in lines:\n"
        "        try:\n"
        "            rec = json.loads(line)\n"
        "        except json.JSONDecodeError:\n"
        "            continue\n"
        "        out.append(_as_int(rec.get('n')))\n"
        "    return out\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_rule_ignores_coercions_that_cannot_raise(tmp_path: Path) -> None:
    """The two lookalikes that made the naive rule 67% precise.

    ``int(elapsed * 1000)`` on floats and ``int(m.group(1))`` on a
    digit-only capture cannot raise; neither reads a record field.
    """
    module = tmp_path / "lookalikes.py"
    module.write_text(
        "import json, time\n"
        "def run(probes, matches):\n"
        "    for probe in probes:\n"
        "        start = time.monotonic()\n"
        "        try:\n"
        "            r = probe.run()\n"
        "        except OSError:\n"
        "            continue\n"
        "        ms = int((time.monotonic() - start) * 1000)\n"
        "        n = int(matches.group(1))\n"
        "        print(r, ms, n)\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)


def test_rule_ignores_a_loop_with_no_skip_guard(tmp_path: Path) -> None:
    """Without a per-record guard there is no promise to break.

    A loop that lets everything propagate is a different (possibly fine)
    contract; this class is specifically about declaring tolerance and
    then not honouring it.
    """
    module = tmp_path / "nopromise.py"
    module.write_text(
        "def load(recs):\n    for rec in recs:\n        yield int(rec.get('n'))\n",
        encoding="utf-8",
    )
    assert not _offending_sites(module)
