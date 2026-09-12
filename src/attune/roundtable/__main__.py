"""``python -m attune.roundtable`` — command-line entry points for the round table.

Only ``ledger`` exists today: it renders (and optionally appends) the R5
dogfood-ledger row for a captured ``/cross-review`` result. The
mechanics stay in :mod:`attune.roundtable.review`.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys

from attune.roundtable.review import ledger_cli


def main(argv: list[str] | None = None) -> int:
    """Dispatch the subcommand; ``ledger`` is the only one."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["ledger"]:
        return ledger_cli(args[1:])
    print(
        "usage: python -m attune.roundtable ledger --result <file> [--disposition TEXT | --disposition-file FILE] [--append RECEIPTS_MD]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
