"""The chair manifest (release-audit-stage R7).

The manifest is what stops the stage being advisory-by-accident, so the
tests are about its REFUSALS: a partial ruling set, a ruling bound to a
different commit, an in-place amendment, and a missing sitting delta
must all reject rather than degrade.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.classes.manifest import (
    MANIFEST_SCHEMA_VERSION,
    ManifestError,
    build_manifest,
    load_manifest,
    manifest_path,
    require_manifest,
    validate_manifest,
    write_manifest,
)
from attune.classes.packet import Packet, ResidualItem

_SHA = "a" * 40


def _item(n: int, disposition: str = "GATE-FIRST") -> ResidualItem:
    return ResidualItem(
        item_id=f"hit:R7b:src/mod.py:{n}",
        kind="hit",
        class_id="C3",
        locus=f"src/mod.py:{n}",
        detail="parsed then used unguarded",
        default_disposition=disposition,
    )


def _packet(count: int = 2) -> Packet:
    return Packet(sections={"0_header": {}}, items=tuple(_item(i) for i in range(count)))


def _kw(packet: Packet, **over):
    rulings = over.pop("rulings", {i.item_id: "SHIP" for i in packet.items})
    delta = over.pop("sitting_delta", {i.item_id: False for i in packet.items})
    base = {
        "tag": "v14.0.0",
        "head_sha": _SHA,
        "baseline_sha": "b" * 40,
        "rulings": rulings,
        "chair_receipt": "ruled 2026-08-22",
        "sitting_delta": delta,
    }
    base.update(over)
    return base


class TestCompletionInvariant:
    """R3: every residual item id carries EXACTLY ONE ruling."""

    def test_missing_ruling_is_refused(self):
        packet = _packet(3)
        partial = {packet.items[0].item_id: "SHIP"}

        with pytest.raises(ManifestError) as exc:
            build_manifest(packet, **_kw(packet, rulings=partial))

        assert exc.value.reason == "missing-rulings"

    def test_ruling_for_an_item_not_in_the_packet_is_refused(self):
        packet = _packet(1)
        rulings = {packet.items[0].item_id: "SHIP", "hit:ghost:x.py:1": "SHIP"}

        with pytest.raises(ManifestError) as exc:
            build_manifest(packet, **_kw(packet, rulings=rulings))

        assert exc.value.reason == "unknown-items"

    def test_unknown_disposition_is_refused(self):
        packet = _packet(1)
        rulings = {packet.items[0].item_id: "LGTM"}

        with pytest.raises(ManifestError) as exc:
            build_manifest(packet, **_kw(packet, rulings=rulings))

        assert exc.value.reason == "bad-disposition"

    def test_complete_ruling_set_builds(self):
        packet = _packet(2)

        manifest = build_manifest(packet, **_kw(packet))

        assert manifest.packet_hash == packet.packet_hash
        assert len(manifest.per_item_dispositions) == 2


class TestSittingDeltaIsRequired:
    """D9 — a manifest without it is invalid, not merely incomplete."""

    def test_absent_delta_is_refused_at_build(self):
        packet = _packet(2)

        with pytest.raises(ManifestError) as exc:
            build_manifest(packet, **_kw(packet, sitting_delta={}))

        assert exc.value.reason == "missing-sitting-delta"

    def test_absent_delta_is_refused_at_validate(self):
        packet = _packet(1)
        data = build_manifest(packet, **_kw(packet)).as_dict()
        data["sitting_delta"] = {}

        with pytest.raises(ManifestError) as exc:
            validate_manifest(data)

        assert exc.value.reason == "missing-sitting-delta"

    def test_delta_reports_whether_the_sitting_moved_anything(self):
        packet = _packet(2)
        ids = [i.item_id for i in packet.items]

        quiet = build_manifest(packet, **_kw(packet))
        moved = build_manifest(packet, **_kw(packet, sitting_delta={ids[0]: True, ids[1]: False}))

        assert quiet.sitting_changed_anything is False
        assert moved.sitting_changed_anything is True


class TestImmutability:
    def test_writing_twice_is_refused(self, tmp_path):
        packet = _packet(1)
        manifest = build_manifest(packet, **_kw(packet))
        write_manifest(manifest, tmp_path)

        with pytest.raises(ManifestError) as exc:
            write_manifest(manifest, tmp_path)

        assert exc.value.reason == "already-exists"

    def test_written_manifest_round_trips(self, tmp_path):
        packet = _packet(2)
        manifest = build_manifest(packet, **_kw(packet))

        path = write_manifest(manifest, tmp_path)
        loaded = load_manifest(tmp_path, "v14.0.0")

        assert path == manifest_path(tmp_path, "v14.0.0")
        assert loaded.as_dict() == manifest.as_dict()
        assert json.loads(path.read_text())["schema_version"] == MANIFEST_SCHEMA_VERSION


class TestReleaseExecuteGate:
    """require_manifest is what stops the stage being advisory."""

    def test_no_manifest_refuses_the_tag(self, tmp_path):
        with pytest.raises(ManifestError) as exc:
            require_manifest(tmp_path, "v14.0.0", _SHA)

        assert exc.value.reason == "no-manifest"

    def test_manifest_for_a_different_commit_refuses(self, tmp_path):
        """A ruling on an earlier SHA does not authorize this tag."""
        packet = _packet(1)
        write_manifest(build_manifest(packet, **_kw(packet)), tmp_path)

        with pytest.raises(ManifestError) as exc:
            require_manifest(tmp_path, "v14.0.0", "c" * 40)

        assert exc.value.reason == "sha-mismatch"

    def test_blocked_items_refuse_the_tag(self, tmp_path):
        """D4 teeth: the stage may hold a release."""
        packet = _packet(2)
        rulings = {packet.items[0].item_id: "SHIP", packet.items[1].item_id: "GATE-FIRST"}
        write_manifest(build_manifest(packet, **_kw(packet, rulings=rulings)), tmp_path)

        with pytest.raises(ManifestError) as exc:
            require_manifest(tmp_path, "v14.0.0", _SHA)

        assert exc.value.reason == "blocked-items"

    def test_cleared_manifest_authorizes_the_tag(self, tmp_path):
        packet = _packet(2)
        write_manifest(build_manifest(packet, **_kw(packet)), tmp_path)

        manifest = require_manifest(tmp_path, "v14.0.0", _SHA)

        assert manifest.blocked == ()

    def test_corrupt_manifest_refuses_rather_than_degrading(self, tmp_path):
        target = manifest_path(tmp_path, "v14.0.0")
        target.parent.mkdir(parents=True)
        target.write_text("{not json", encoding="utf-8")

        with pytest.raises(ManifestError) as exc:
            require_manifest(tmp_path, "v14.0.0", _SHA)

        assert exc.value.reason == "unreadable"


class TestTagCannotEscapeTheManifestDirectory:
    """A tag is caller-supplied and lands in a path (path-validation gate)."""

    @pytest.mark.parametrize(
        "tag",
        [
            "../../../etc/cron.d/x",
            "../outside",
            "v1.0.0/../../escape",
            "/absolute/elsewhere",
            "with\x00null",
            "",
            "." * 200,
        ],
    )
    def test_hostile_tag_is_refused(self, tmp_path, tag):
        with pytest.raises(ManifestError) as exc:
            manifest_path(tmp_path, tag)

        assert exc.value.reason in ("bad-tag", "unsafe-path")

    @pytest.mark.parametrize("tag", ["v14.0.0", "v1.2.3-rc1", "v0.1.0"])
    def test_real_tags_are_accepted(self, tmp_path, tag):
        path = manifest_path(tmp_path, tag)

        assert path.name == f"{tag}.json"
        assert path.parent.name == "release-manifests"

    def test_escape_is_refused_at_write_time_too(self, tmp_path):
        """The guard sits in the path builder, so writers inherit it."""
        packet = _packet(1)
        manifest = build_manifest(packet, **_kw(packet, tag="../escape"))

        with pytest.raises(ManifestError):
            write_manifest(manifest, tmp_path)
