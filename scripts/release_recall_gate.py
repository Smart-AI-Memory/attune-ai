#!/usr/bin/env python3
"""Release gate: prove memory recall works in the BUILT artifact.

Why this exists: 9.3.0 shipped with ``attune memory recall`` 100%
broken (capture succeeded, recall returned nothing) while every mocked
unit test was green — all local testing ran the checkout, never the
wheel. This gate installs the actual artifact into a clean venv with an
ISOLATED ``$HOME`` and exercises the user-facing CLI round-trip:
capture N memories, recall each, assert hits land and no duplicate
paths come back (the 9.4.x dedup class).

Usage::

    python scripts/release_recall_gate.py                # builds the wheel
    python scripts/release_recall_gate.py --wheel dist/attune_ai-X.Y.Z-*.whl

Exit 0 = gate passed; exit 1 = gate FAILED (do not publish).
Spec: docs/specs/curated-memory-productionization/tasks.md (T7).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: (topic, kind, content, recall query) — three kinds, distinct wording
#: so keyword recall has real signal to rank on.
CASES = [
    (
        "release-gate-decision",
        "decision",
        "We gate every release on an artifact-level recall round-trip "
        "after 9.3.0 shipped with recall completely broken.",
        "why do we gate releases on recall",
    ),
    (
        "redis-timeout-tuning",
        "troubleshooting",
        "Intermittent Redis connection failures under load were fixed "
        "by raising the connection timeout to thirty seconds.",
        "intermittent redis connection failures under load",
    ),
    (
        "keyword-corpus-pattern",
        "reference",
        "The personal memory corpus is retrieved with the attune-rag "
        "keyword pipeline over polished markdown files.",
        "how is the personal memory corpus retrieved",
    ),
]


def run(cmd: list[str], env: dict[str, str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a command, echoing it, never raising on nonzero exit."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)


def fail(msg: str) -> int:
    print(f"\nRECALL GATE FAILED: {msg}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", help="Path/glob of the wheel to test (default: build one)")
    args = parser.parse_args()

    base_env = os.environ.copy()

    if args.wheel:
        wheels = sorted(glob.glob(args.wheel))
        if not wheels:
            return fail(f"no wheel matches {args.wheel!r}")
        wheel = wheels[-1]
    else:
        print("building wheel (uv build) ...")
        built = run(["uv", "build", "--wheel"], base_env, timeout=600)
        if built.returncode != 0:
            return fail(f"uv build failed:\n{built.stderr[-800:]}")
        wheels = sorted(glob.glob(str(REPO / "dist" / "attune_ai-*.whl")), key=os.path.getmtime)
        if not wheels:
            return fail("uv build produced no wheel in dist/")
        wheel = wheels[-1]
    print(f"wheel: {wheel}")

    with tempfile.TemporaryDirectory(prefix="recall-gate-") as tmp:
        tmpdir = Path(tmp)
        venv = tmpdir / "venv"
        fake_home = tmpdir / "home"
        fake_home.mkdir()

        print("creating clean venv ...")
        made = run(["uv", "venv", "-q", str(venv)], base_env)
        if made.returncode != 0:
            return fail(f"uv venv failed:\n{made.stderr[-400:]}")

        print("installing the artifact ...")
        installed = run(
            ["uv", "pip", "install", "-q", "--python", str(venv / "bin" / "python"), wheel],
            base_env,
            timeout=600,
        )
        if installed.returncode != 0:
            return fail(f"wheel install failed:\n{installed.stderr[-800:]}")

        # Isolated HOME: the artifact's memory writes/reads must land in
        # a fresh corpus, and no key/env from the developer machine may
        # leak in (keyless like CI — empty string, not unset).
        env = {
            "HOME": str(fake_home),
            "PATH": os.environ.get("PATH", ""),
            "ANTHROPIC_API_KEY": "",
        }
        attune = str(venv / "bin" / "attune")

        print("capture -> recall round-trips ...")
        for topic, kind, content, _query in CASES:
            cap = run([attune, "memory", "capture", topic, content, "--kind", kind], env)
            if cap.returncode != 0:
                return fail(f"capture {topic!r} exited {cap.returncode}:\n{cap.stderr[-400:]}")

        hits = 0
        for topic, kind, _content, query in CASES:
            rec = run([attune, "memory", "recall", query, "--k", "3", "--json"], env)
            if rec.returncode != 0:
                return fail(f"recall {query!r} exited {rec.returncode}:\n{rec.stderr[-400:]}")
            try:
                results = json.loads(rec.stdout)
            except json.JSONDecodeError:
                return fail(f"recall {query!r} emitted non-JSON:\n{rec.stdout[-400:]}")
            paths = [r.get("path", "") for r in results]
            if len(paths) != len(set(paths)):
                return fail(f"recall {query!r} returned duplicate paths: {paths}")
            if any(p == f"{topic}/{kind}.md" for p in paths):
                hits += 1
            else:
                print(f"  MISS: {query!r} -> {paths}")

        print(f"\nhit@3: {hits}/{len(CASES)}")
        if hits < len(CASES):
            return fail(
                f"only {hits}/{len(CASES)} queries recalled their capture "
                "from the built artifact"
            )

    print("RECALL GATE PASSED — artifact-level capture->recall verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
