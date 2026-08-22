"""Class M — "the mock defined the contract" — receipt-type checks.

Release-audit-stage R6 (Phase X, independent of the stage): a fix
for a boundary class must declare a receipt type that actually
exercises the boundary. Enforcement reads **commit trailers**, which
survive squash merges where PR metadata detaches (Agy#6):

    Class-Fix: G1
    Receipt-Type: live-fire
    Evidence: tests/unit/memory/test_file_stash.py::test_two_process

Rules (fail closed — Codex#13/#14):

- ``Receipt-Type`` must be one of :data:`RECEIPT_TYPES` (the
  decision-routine taxonomy verbatim).
- A boundary-class fix (``Class-Fix`` naming an id in
  :data:`BOUNDARY_CLASS_IDS`) requires ``behavioral`` or
  ``live-fire`` — ``suite`` is class M by declaration.
- Every ``Class-Fix`` requires an ``Evidence`` pointer; a bare
  declaration is checkbox theater.
- A commit whose subject names a known class id without a
  ``Class-Fix`` trailer is an UNDECLARED fix and fails — absence is
  not a pass.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

#: The receipt taxonomy, verbatim from the decision-routine rule.
RECEIPT_TYPES = frozenset({"suite", "behavioral", "live-fire", "metric", "evidence-chain"})

#: Receipt types that exercise a real boundary (R6 admissibility).
BOUNDARY_ADMISSIBLE = frozenset({"behavioral", "live-fire"})

#: Register class ids whose defect crosses a real boundary. Seeded
#: from the 2026-08-20 register; Phase 0's rule pack takes over
#: ownership of this set when it lands.
BOUNDARY_CLASS_IDS = frozenset(
    {
        "C1",
        "C2",
        "C3",
        "C4a",
        "C4b",
        "C5",
        "C6",
        "C8",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "G1",
        "G2",
        "G3",
        "G5",
        "I-1",
        "I-2",
        "I-3",
        "I-4",
        "I-5",
        "I-6",
    }
)

_TRAILER_RE = re.compile(
    r"^(?P<key>Class-Fix|Receipt-Type|Evidence):\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)
# A class id mentioned as its own token in a subject line, e.g.
# "fix(G1): ..." or "close I-4 escape". Sorted longest-first so
# "C4a" wins over a hypothetical "C4".
_ID_TOKEN_RE = re.compile(
    r"\b("
    + "|".join(sorted((re.escape(c) for c in BOUNDARY_CLASS_IDS), key=len, reverse=True))
    + r")\b"
)


@dataclass
class ReceiptProblem:
    """One violation found on one commit."""

    sha: str
    problem: str

    def __str__(self) -> str:
        return f"{self.sha[:12]}: {self.problem}"


def _trailers(message: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for m in _TRAILER_RE.finditer(message):
        found.setdefault(m.group("key"), []).append(m.group("value"))
    return found


def check_commit(sha: str, message: str) -> list[ReceiptProblem]:
    """Validate one commit message against the R6 trailer schema.

    Args:
        sha: The commit SHA (used only for reporting).
        message: The full commit message, subject included.

    Returns:
        Every violation found; empty means the commit passes.
    """
    problems: list[ReceiptProblem] = []
    trailers = _trailers(message)
    class_fixes = trailers.get("Class-Fix", [])
    receipt_types = trailers.get("Receipt-Type", [])
    evidence = trailers.get("Evidence", [])
    subject = message.splitlines()[0] if message else ""

    if not class_fixes:
        mentioned = _ID_TOKEN_RE.search(subject)
        if mentioned:
            problems.append(
                ReceiptProblem(
                    sha,
                    f"subject names class {mentioned.group(1)} but carries no "
                    "Class-Fix trailer (undeclared fix fails closed)",
                )
            )
        return problems

    for value in receipt_types:
        if value not in RECEIPT_TYPES:
            problems.append(
                ReceiptProblem(
                    sha,
                    f"Receipt-Type {value!r} not in " f"{sorted(RECEIPT_TYPES)}",
                )
            )

    if not receipt_types:
        problems.append(ReceiptProblem(sha, "Class-Fix declared without a Receipt-Type"))
    if not evidence:
        problems.append(ReceiptProblem(sha, "Class-Fix declared without an Evidence pointer"))

    for class_id in class_fixes:
        if class_id not in BOUNDARY_CLASS_IDS:
            problems.append(
                ReceiptProblem(
                    sha,
                    f"Class-Fix {class_id!r} is not a known class id",
                )
            )
            continue
        admissible = [t for t in receipt_types if t in BOUNDARY_ADMISSIBLE]
        if receipt_types and not admissible:
            problems.append(
                ReceiptProblem(
                    sha,
                    f"boundary class {class_id} declared with "
                    f"{sorted(set(receipt_types))} — requires one of "
                    f"{sorted(BOUNDARY_ADMISSIBLE)} (class M by declaration)",
                )
            )
    return problems


def check_range(base: str, head: str = "HEAD", *, cwd: str | None = None) -> list[ReceiptProblem]:
    """Validate every commit in ``base..head`` (the release baseline).

    Args:
        base: Baseline ref (e.g. the merge-base with the last tag).
        head: Head ref, default ``HEAD``.
        cwd: Repository directory; default the process cwd.

    Returns:
        All violations across the range, oldest commit first.

    Raises:
        subprocess.CalledProcessError: If git cannot resolve the range.
    """
    raw = subprocess.run(
        ["git", "log", "--reverse", "--format=%H%x00%B%x01", f"{base}..{head}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
        cwd=cwd,
    ).stdout
    problems: list[ReceiptProblem] = []
    for record in raw.split("\x01"):
        record = record.strip("\n")
        if not record:
            continue
        sha, _, message = record.partition("\x00")
        problems.extend(check_commit(sha.strip(), message))
    return problems


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.class_m --base <ref> [--head <ref>]``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="baseline ref")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    problems = check_range(args.base, args.head)
    for p in problems:
        print(p)
    if problems:
        print(f"{len(problems)} receipt problem(s)")
        return 1
    print("receipt check clean")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
