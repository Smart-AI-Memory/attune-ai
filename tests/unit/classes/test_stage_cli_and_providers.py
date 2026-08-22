"""The seams the injected-dependency design left uncovered.

Everything in the stage takes its network and its seats as parameters,
which is what keeps the logic testable — but it also means the DEFAULT
implementations (the `gh` reader, the CLI entry point) never run in the
suite. Those defaults are what actually execute in production, so their
failure modes are pinned here.

The property throughout is the same one the stage is built on: an
unprovable result fails CLOSED. A `gh` that is missing, errors, or
returns junk must yield "no runs" — never a fabricated green.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import subprocess

import pytest

from attune.classes import reconcile as reconcile_mod
from attune.classes import stage as stage_mod
from attune.classes.manifest import (
    ManifestError,
    build_manifest,
    manifest_path,
    validate_manifest,
    write_manifest,
)
from attune.classes.packet import Packet, ResidualItem, _public_symbols, _show
from attune.classes.reconcile import gh_runs_provider

_SHA = "a" * 40


def _completed(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr="")


class TestGhRunsProviderFailsClosed:
    """The default CI reader. Every failure yields [] -> caller says no-run."""

    def test_parses_a_normal_reply(self, monkeypatch):
        payload = json.dumps([{"databaseId": 7, "name": "Tests", "headSha": _SHA}])
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(payload))

        runs = gh_runs_provider("o/r", _SHA)

        assert runs[0]["databaseId"] == 7

    def test_nonzero_exit_yields_no_runs(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed("", returncode=1))

        assert gh_runs_provider("o/r", _SHA) == []

    def test_unparseable_json_yields_no_runs(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed("{not json"))

        assert gh_runs_provider("o/r", _SHA) == []

    def test_non_list_json_yields_no_runs(self, monkeypatch):
        """A dict where a list was expected must not be iterated as runs."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed('{"a": 1}'))

        assert gh_runs_provider("o/r", _SHA) == []

    @pytest.mark.parametrize("exc", [OSError("gh: not found"), subprocess.TimeoutExpired("gh", 60)])
    def test_a_missing_or_hanging_gh_yields_no_runs(self, monkeypatch, exc):
        def boom(*a, **k):
            raise exc

        monkeypatch.setattr(subprocess, "run", boom)

        assert gh_runs_provider("o/r", _SHA) == []

    def test_the_query_binds_repo_and_commit(self, monkeypatch):
        seen = {}

        def capture(argv, **k):
            seen["argv"] = argv
            return _completed("[]")

        monkeypatch.setattr(subprocess, "run", capture)
        gh_runs_provider("owner/name", _SHA)

        assert "--repo" in seen["argv"] and "owner/name" in seen["argv"]
        assert "--commit" in seen["argv"] and _SHA in seen["argv"]


class TestStageCliExitCodes:
    """Exit codes are the contract the /release skill documents."""

    def test_ready_for_the_chair_is_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(
            stage_mod,
            "run_stage",
            lambda *a, **k: stage_mod.StageResult(
                baseline=_fake_baseline(),
                reconcile_receipt=None,
                packet=Packet(sections={"0_header": {}}, items=()),
                sitting=None,
            ),
        )

        assert stage_mod.main(["--no-sitting"]) == 0
        assert json.loads(capsys.readouterr().out)["packet_hash"]

    def test_abort_is_one(self, monkeypatch, capsys):
        def abort(*a, **k):
            raise stage_mod.StageAborted("1-reconcile", "no-run", "nothing for this sha")

        monkeypatch.setattr(stage_mod, "run_stage", abort)

        assert stage_mod.main([]) == 1
        out = json.loads(capsys.readouterr().out)
        assert out["aborted_at"] == "1-reconcile" and out["reason"] == "no-run"

    def test_over_cap_is_two_so_split_is_distinguishable(self, monkeypatch, capsys):
        """R4 reserves 2 so a caller can tell 'split the release' apart."""

        def over(*a, **k):
            raise stage_mod.StageAborted("3-residual", "over-cap", "[]")

        monkeypatch.setattr(stage_mod, "run_stage", over)

        assert stage_mod.main([]) == 2
        assert json.loads(capsys.readouterr().out)["reason"] == "over-cap"


def _fake_baseline():
    from attune.classes.baseline import Baseline

    return Baseline(tag="v1.0.0", baseline_sha="b" * 40, head_sha=_SHA, source="last-release-tag")


class TestPacketHelpersDegrade:
    def test_unparseable_source_yields_no_symbols(self):
        """A corrupt module must not abort the whole symbol delta."""
        assert _public_symbols("def (((") == set()

    def test_null_byte_source_yields_no_symbols(self):
        """ast.parse raises ValueError, not SyntaxError, on a null byte."""
        assert _public_symbols("x = 1\x00\n") == set()

    def test_private_names_are_not_public_surface(self):
        source = "def _hidden(): pass\ndef shown(): pass\n_X = 1\nY = 2\n"

        assert _public_symbols(source) == {"shown", "Y"}

    def test_show_returns_empty_for_a_path_absent_at_that_ref(self, tmp_path):
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)

        assert _show(tmp_path, "HEAD", "nope.py") == ""


class TestManifestValidationBranches:
    def _valid(self):
        packet = Packet(
            sections={},
            items=(
                ResidualItem(
                    item_id="i1",
                    kind="hit",
                    class_id="C3",
                    locus="src/m.py:1",
                    detail="d",
                    default_disposition="SHIP",
                ),
            ),
        )
        return build_manifest(
            packet,
            tag="v1.0.0",
            head_sha=_SHA,
            baseline_sha="b" * 40,
            rulings={"i1": "SHIP"},
            sitting_delta={"i1": False},
            chair_receipt="ok",
        ).as_dict()

    def test_non_mapping_is_refused(self):
        with pytest.raises(ManifestError) as exc:
            validate_manifest(["not", "a", "mapping"])  # type: ignore[arg-type]

        assert exc.value.reason == "not-a-mapping"

    def test_wrong_schema_version_is_refused(self):
        data = self._valid()
        data["schema_version"] = 99

        with pytest.raises(ManifestError) as exc:
            validate_manifest(data)

        assert exc.value.reason == "schema-version"

    def test_dispositions_must_be_a_mapping(self):
        data = self._valid()
        data["per_item_dispositions"] = ["i1"]

        with pytest.raises(ManifestError) as exc:
            validate_manifest(data)

        assert exc.value.reason == "bad-dispositions"

    def test_unknown_disposition_is_refused_on_read(self):
        data = self._valid()
        data["per_item_dispositions"] = {"i1": "MAYBE"}

        with pytest.raises(ManifestError) as exc:
            validate_manifest(data)

        assert exc.value.reason == "bad-disposition"

    def test_missing_key_is_refused(self):
        data = self._valid()
        del data["chair_receipt"]

        with pytest.raises(ManifestError) as exc:
            validate_manifest(data)

        assert exc.value.reason == "missing-keys"

    def test_a_valid_manifest_round_trips_through_validate(self):
        assert validate_manifest(self._valid()).tag == "v1.0.0"

    def test_write_cleans_up_its_temp_file_on_failure(self, tmp_path, monkeypatch):
        """An interrupted write must not leave a .tmp beside the manifest."""
        packet = Packet(sections={}, items=())
        manifest = build_manifest(
            packet,
            tag="v1.0.0",
            head_sha=_SHA,
            baseline_sha="b" * 40,
            rulings={},
            sitting_delta={},
            chair_receipt="ok",
        )
        target = manifest_path(tmp_path, "v1.0.0")
        target.parent.mkdir(parents=True, exist_ok=True)

        def fail_replace(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr("attune.classes.manifest.os.replace", fail_replace)

        with pytest.raises(OSError):
            write_manifest(manifest, tmp_path)

        assert list(target.parent.glob("*.tmp")) == [], "temp file must be cleaned up"


class TestReconcileModuleSurface:
    def test_allowlist_names_the_gate_carrying_workflow(self):
        assert "Tests" in reconcile_mod.ALLOWED_WORKFLOWS

    def test_only_success_is_treated_as_green(self):
        assert reconcile_mod._GREEN == "success"


class TestTheLastRefusalBranches:
    """Defence-in-depth paths that the primary guards normally shadow."""

    def test_git_unavailable_is_a_baseline_error_not_a_crash(self, tmp_path, monkeypatch):
        from attune.classes import baseline as baseline_mod

        def boom(*a, **k):
            raise OSError("git: command not found")

        monkeypatch.setattr(baseline_mod.subprocess, "run", boom)

        with pytest.raises(baseline_mod.BaselineError) as exc:
            baseline_mod.resolve_baseline(tmp_path)

        assert exc.value.reason == "git-unavailable"

    def test_manifest_path_parent_check_catches_what_the_tag_regex_misses(
        self, tmp_path, monkeypatch
    ):
        """The regex normally shadows this; it is the belt to its braces."""
        import re as _re

        import attune.classes.manifest as manifest_mod

        # Relax the shape guard so the resolved-parent assertion is the
        # thing actually under test.
        monkeypatch.setattr(manifest_mod, "_SAFE_TAG", _re.compile(r"^.*$"))

        with pytest.raises(ManifestError) as exc:
            manifest_mod.manifest_path(tmp_path, "../../escape")

        assert exc.value.reason == "unsafe-path"

    def test_a_seat_with_no_recipe_is_absent(self):
        from attune.classes.sitting import hold_sitting

        packet = Packet(sections={"0_header": {}}, items=())
        sitting = hold_sitting(packet, seats=("nonexistent-seat",))

        assert sitting.replies[0].status == "absent"
        assert sitting.seats_present == ()

    def test_amendment_serialises(self):
        from attune.classes.sitting import SeatAmendment

        data = SeatAmendment(item_id="i1", disposition="SHIP", reason="why").as_dict()

        assert data == {"item_id": "i1", "disposition": "SHIP", "reason": "why"}

    def test_over_cap_residual_aborts_the_stage_at_step_3(self, tmp_path, monkeypatch):
        """The stage must translate a packet refusal into an abort, not crash."""
        from attune.classes import stage as st
        from attune.classes.packet import PacketOverCap

        monkeypatch.setattr(st, "resolve_baseline", lambda *a, **k: _fake_baseline())
        monkeypatch.setattr(st, "scan_paths", lambda *a, **k: {"hits": [], "rules": {}})
        monkeypatch.setattr(st, "derive_register", lambda **k: {"rows": []})

        def over(*a, **k):
            raise PacketOverCap({"breaches": [{"cap": "items", "limit": 12, "actual": 20}]})

        monkeypatch.setattr(st, "build_packet", over)

        with pytest.raises(st.StageAborted) as exc:
            st.run_stage(tmp_path, "o/r", skip_reconcile=True)

        assert exc.value.step == "3-residual" and exc.value.reason == "over-cap"
