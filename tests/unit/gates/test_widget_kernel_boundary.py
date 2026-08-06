"""AC-4 for widget-kernel-family: the generalized seal gate holds AND
is proven able to fail (a gate that cannot fail is not a gate).

Live half: the real repo passes for every registered kernel. Seeded
half: an import leak, an inward reference, and a size breach each
produce a violation when injected into a synthetic kernel tree.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "check_widget_kernel_boundaries",
    REPO_ROOT / "scripts/check_widget_kernel_boundaries.py",
)
gate = importlib.util.module_from_spec(_spec)
sys.modules["check_widget_kernel_boundaries"] = gate
_spec.loader.exec_module(gate)


def _policy(tmp_path: Path, **overrides) -> gate.KernelPolicy:
    defaults = {
        "name": "fakekit",
        "kernel_dir": "src/widgets/fakekit",
        "ceiling": 100,
        "allowed_outside": frozenset({"src/loader.py"}),
        "internal_markers": ("fakekit/", "widgets.fakekit"),
    }
    defaults.update(overrides)
    return gate.KernelPolicy(**defaults)


class TestLiveSeal:
    def test_real_repo_passes_for_all_registered_kernels(self) -> None:
        violations = gate.run_checks(REPO_ROOT, list(gate.KERNELS.values()), require_dist=False)
        assert violations == []

    def test_chartkit_is_registered_with_ruled_default_ceiling(self) -> None:
        assert "chartkit" in gate.KERNELS
        assert gate.KERNELS["chartkit"].ceiling == 20_480


class TestSeededViolations:
    def test_outward_import_leak_fails(self, tmp_path: Path) -> None:
        src = tmp_path / "src/widgets/fakekit/src"
        src.mkdir(parents=True)
        (src / "kernel.js").write_text(
            'import { x } from "../escape.js";\nimport y from "./ok.js";\n',
            encoding="utf-8",
        )
        violations: list[str] = []
        gate.check_outward(tmp_path, _policy(tmp_path), violations)
        assert len(violations) == 1
        assert "outward import '../escape.js'" in violations[0]

    def test_inward_reference_fails_and_allowlist_admits(self, tmp_path: Path) -> None:
        outsider = tmp_path / "src/consumer.py"
        outsider.parent.mkdir(parents=True)
        outsider.write_text("from widgets.fakekit import internals\n", encoding="utf-8")
        sanctioned = tmp_path / "src/loader.py"
        sanctioned.write_text("DATA = 'widgets.fakekit'\n", encoding="utf-8")

        violations: list[str] = []
        gate.check_inward(
            tmp_path,
            _policy(tmp_path),
            ["src/consumer.py", "src/loader.py"],
            violations,
        )
        assert len(violations) == 1
        assert "src/consumer.py" in violations[0]

    def test_size_breach_fails(self, tmp_path: Path) -> None:
        dist = tmp_path / "src/widgets/fakekit/dist"
        dist.mkdir(parents=True)
        (dist / "kernel.min.js").write_bytes(b"x" * 101)
        violations: list[str] = []
        gate.check_size(tmp_path, _policy(tmp_path), violations, require_dist=True)
        assert len(violations) == 1
        assert "exceeds the 100-byte ceiling" in violations[0]

    def test_missing_dist_fails_only_when_required(self, tmp_path: Path) -> None:
        (tmp_path / "src/widgets/fakekit").mkdir(parents=True)
        violations: list[str] = []
        gate.check_size(tmp_path, _policy(tmp_path), violations, require_dist=False)
        assert violations == []
        gate.check_size(tmp_path, _policy(tmp_path), violations, require_dist=True)
        assert len(violations) == 1
        assert "missing" in violations[0]
