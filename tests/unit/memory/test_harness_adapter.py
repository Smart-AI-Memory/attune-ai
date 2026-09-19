"""Disposable current-service compatibility and refusal of unqualified effects."""

import json
import socket
import time
from copy import deepcopy
from pathlib import Path

import pytest

from attune.memory import personal, session_stash
from attune.memory.file_stash import FileStashBackend
from attune.memory.harness_adapter import CompatibilityAdapter


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "telemetry-home"))
    monkeypatch.setenv("ATTUNE_USAGE_PING", "0")
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("No network/provider permitted in adapter tests")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(personal, "_load_author", forbidden)
    yield
    assert not attempted


def config(tmp_path, *tiers):
    roots = []
    for i, tier in enumerate(tiers):
        root = tmp_path / str(i)
        root.mkdir()
        roots.append(
            {
                "id": f"root{i}",
                "path": str(root.resolve()),
                "tier": tier,
                "scope": "project",
                "owner": "patrick",
                "classification": "internal",
            }
        )
    return {
        "schema_version": 1,
        "actor": "patrick",
        "owners": ["patrick"],
        "scopes": ["project"],
        "classifications": ["internal"],
        "profiles": ["luna", "astra"],
        "roots": roots,
    }


def raw_source(root, *, text="Aurora: keep the CI exception.", id="N1", cwd="project"):
    path = Path(root) / "findings.jsonl"
    row = {
        "id": id,
        "text": text,
        "session_id": "synthetic",
        "topics": ["type:note", "cwd:" + cwd],
        "cwd": cwd,
        "ts": time.time(),
        "future_field": {"preserve": ["all", "metadata"]},
    }
    with path.open("a") as stream:
        stream.write(json.dumps(row) + "\n")
    return path


def test_full_raw_read_scope_metadata_and_no_effects(tmp_path):
    cfg = config(tmp_path, "raw")
    root = cfg["roots"][0]["path"]
    text = "Aurora: retain exception and source. " * 50 + "FINAL_DETAIL"
    path = raw_source(root, text=text)
    raw_source(root, id="foreign", cwd="foreign-project")
    before = path.read_bytes()
    adapter = CompatibilityAdapter(cfg)
    packet = adapter.query("Aurora")
    assert packet["status"] == "available"
    assert [i["id"] for i in packet["items"]] == ["root0:N1"]
    item = packet["items"][0]
    assert item["text"] == text and item["metadata"]["future_field"]["preserve"] == [
        "all",
        "metadata",
    ]
    assert adapter.resolve(item)["text"] == text
    assert adapter.query("")["items"][0]["text"] == text
    with pytest.raises(ValueError, match="mutations unavailable"):
        adapter.apply("forget", "N1")
    assert path.read_bytes() == before
    assert adapter.capabilities()["worker_mutations"] == []


def test_document_root_collision_curated_metadata_and_full_content(tmp_path):
    cfg = config(tmp_path, "personal", "curated")
    for i, root in enumerate(cfg["roots"]):
        doc = Path(root["path"]) / "aurora" / "decision.md"
        doc.parent.mkdir()
        doc.write_text(
            f"---\nname: decision\nreview: accepted-{i}\n---\n# Aurora\n\nAurora reminder at {9+i}:15.\n"
            + ("Exception and [[source]] survive. " * 70)
            + f"FINAL-{i}"
        )
    adapter = CompatibilityAdapter(cfg)
    packet = adapter.query("Aurora reminder", k=20)
    assert packet["status"] == "available"
    assert {i["id"] for i in packet["items"]} == {
        "root0:aurora/decision.md",
        "root1:aurora/decision.md",
    }
    for index, item in enumerate(packet["items"]):
        full = adapter.resolve(item)
        assert f"accepted-{index}" in full["text"] and f"FINAL-{index}" in full["text"]
        assert "[[source]]" in full["text"] and len(full["text"]) > 500


@pytest.mark.parametrize("tier", ["raw", "personal"])
@pytest.mark.parametrize("change", ["correct", "delete"])
def test_corrected_or_deleted_source_handle_rejected(tmp_path, tier, change):
    cfg = config(tmp_path, tier)
    root = Path(cfg["roots"][0]["path"])
    if tier == "raw":
        path = raw_source(root)
    else:
        path = root / "aurora" / "decision.md"
        path.parent.mkdir()
        path.write_text("# Aurora\n\nAurora original decision.")
    adapter = CompatibilityAdapter(cfg)
    item = adapter.query("Aurora")["items"][0]
    if change == "delete":
        path.unlink()
    else:
        path.write_text(path.read_text().replace("Aurora", "Corrected Aurora"))
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        adapter.resolve(item)


def test_truthful_empty_unavailable_partial(tmp_path):
    cfg = config(tmp_path, "raw", "personal")
    adapter = CompatibilityAdapter(cfg)
    assert adapter.query("Aurora")["status"] == "empty"
    Path(cfg["roots"][1]["path"]).rmdir()
    assert adapter.query("Aurora")["status"] == "unavailable"
    raw_source(cfg["roots"][0]["path"])
    result = adapter.query("Aurora")
    assert result["status"] == "partial" and result["problems"][0]["root_id"] == "root1"


@pytest.mark.parametrize("corrupt", ["duplicate", "malformed", "wrong_shape"])
def test_raw_invalid_identity_not_silently_empty(tmp_path, corrupt):
    cfg = config(tmp_path, "raw")
    path = raw_source(cfg["roots"][0]["path"])
    if corrupt == "duplicate":
        raw_source(cfg["roots"][0]["path"])
    else:
        with path.open("a") as stream:
            stream.write("{bad json\n" if corrupt == "malformed" else "[]\n")
    assert CompatibilityAdapter(cfg).query("Aurora")["status"] == "unavailable"


@pytest.mark.parametrize(
    ("key", "value"), [("owner", "foreign"), ("classification", "sensitive"), ("scope", "foreign")]
)
def test_foreign_root_refused_before_service(tmp_path, monkeypatch, key, value):
    cfg = config(tmp_path, "personal")
    cfg["roots"][0][key] = value
    monkeypatch.setattr(
        personal.PersonalMemory, "query", lambda *a, **k: pytest.fail("Unauthorized service call")
    )
    with pytest.raises(ValueError, match="authority"):
        CompatibilityAdapter(cfg)


def test_symlink_and_path_escape_refused(tmp_path):
    cfg = config(tmp_path, "personal")
    root = Path(cfg["roots"][0]["path"])
    outside = tmp_path / "foreign.md"
    outside.write_text("# Aurora\nforeign canary")
    (root / "link.md").symlink_to(outside)
    adapter = CompatibilityAdapter(cfg)
    assert adapter.query("Aurora")["status"] == "unavailable"
    with pytest.raises(ValueError):
        adapter._read(cfg["roots"][0], "../foreign.md")
    (root / "link.md").unlink()
    cfg["roots"][0]["path"] = str(root / "..")
    with pytest.raises(ValueError):
        CompatibilityAdapter(cfg)


def test_changed_authority_refused(tmp_path):
    cfg = config(tmp_path, "raw")
    raw_source(cfg["roots"][0]["path"])
    adapter = CompatibilityAdapter(cfg)
    item = adapter.query("Aurora")["items"][0]
    foreign = deepcopy(item)
    foreign["authority"] = "foreign"
    with pytest.raises(ValueError):
        adapter.resolve(foreign)
    adapter.config["owners"].append("foreign")
    with pytest.raises(ValueError, match="authority changed"):
        adapter.query("Aurora")


def test_missing_rag_distinct_and_legacy_default_preserved(tmp_path, monkeypatch):
    cfg = config(tmp_path, "personal")
    monkeypatch.setattr(personal, "_load_rag", lambda: None)
    memory = personal.PersonalMemory(
        global_root=Path(cfg["roots"][0]["path"]), project_root=Path(cfg["roots"][0]["path"])
    )
    assert memory.query("Aurora") == []
    with pytest.raises(ImportError):
        memory.query("Aurora", strict=True)
    assert CompatibilityAdapter(cfg).query("Aurora")["status"] == "unavailable"


def test_rag_failure_distinct_and_legacy_default_preserved(tmp_path, monkeypatch):
    cfg = config(tmp_path, "personal")

    def broken(*args, **kwargs):
        raise ValueError("synthetic reader unavailable")

    monkeypatch.setattr(personal, "_load_rag", lambda: (broken, object))
    memory = personal.PersonalMemory(
        global_root=Path(cfg["roots"][0]["path"]), project_root=Path(cfg["roots"][0]["path"])
    )
    assert memory.query("Aurora") == []
    with pytest.raises(ValueError):
        memory.query("Aurora", strict=True)
    assert CompatibilityAdapter(cfg).query("Aurora")["status"] == "unavailable"


@pytest.mark.parametrize("error_type", [OSError, AttributeError])
def test_adapter_distinguishes_read_failure_from_programming_defect(
    tmp_path, monkeypatch, error_type
):
    cfg = config(tmp_path, "personal")

    def broken(*args, **kwargs):
        raise error_type("synthetic reader failure")

    monkeypatch.setattr(personal, "_load_rag", lambda: (broken, object))
    adapter = CompatibilityAdapter(cfg)
    if error_type is OSError:
        result = adapter.query("Aurora")
        assert result["status"] == "unavailable"
        assert result["problems"][0]["reason"] == "OSError"
    else:
        with pytest.raises(AttributeError, match="synthetic reader failure"):
            adapter.query("Aurora")


def strict(content, backend, **kwargs):
    return session_stash.stash_content_strict(
        content,
        backend=backend,
        memory_id="exact-id",
        session_id="synthetic",
        cwd="project",
        kind="note",
        **kwargs,
    )


def test_strict_roundtrip_does_not_truncate_or_divert(tmp_path, monkeypatch):
    backend = FileStashBackend(base_dir=tmp_path / "explicit-backend")
    monkeypatch.setattr(
        session_stash, "_divert_to_file", lambda *a: pytest.fail("No diversion allowed")
    )
    assert strict("Aurora preserves exceptions.", backend)["status"] == "acknowledged"
    hits = session_stash.recall_entries("Aurora", backend=backend)
    assert hits[0]["id"] == "exact-id"
    assert strict("x" * 501, backend)["status"] == "refused"
    assert len(backend.recent(100)) == 1
    assert backend.forget(["exact-id"]) == 1
    assert backend.recent(100) == []  # Actual service effect, not new worker qualification.


@pytest.mark.parametrize("failure", ["false_ack", "exception", "backend_exception"])
def test_strict_uncertain_write_never_diverts_or_retries(tmp_path, monkeypatch, failure):
    backend = FileStashBackend(base_dir=tmp_path / "explicit-backend")
    calls = []

    class BackendLostAck(Exception):
        pass

    class LostAck:
        def remember(self, *args, **kwargs):
            calls.append(1)
            backend.remember(*args, **kwargs)
            if failure == "exception":
                raise OSError("response lost after effect")
            if failure == "backend_exception":
                raise BackendLostAck("backend-specific response lost after effect")
            return False

    monkeypatch.setattr(session_stash, "_divert_to_file", lambda *a: pytest.fail("No diversion"))
    assert strict("Aurora exactly once per explicit call.", LostAck())["status"] == "uncertain"
    assert calls == [1] and len(backend.recent(100)) == 1


@pytest.mark.parametrize("content", ["", "   ", "api_key=sk-" + "abc123def456ghi789jkl"])
def test_strict_unsafe_content_never_reaches_backend(content):
    class Forbidden:
        def remember(self, *args, **kwargs):
            pytest.fail("Unsafe write reached backend")

    assert strict(content, Forbidden())["status"] == "refused"


def test_unavailable_sanitizer_and_reserved_tags_refused(tmp_path, monkeypatch):
    backend = FileStashBackend(base_dir=tmp_path / "explicit-backend")
    monkeypatch.setattr(session_stash, "_sanitize", lambda content: None)
    assert strict("Aurora", backend)["status"] == "refused"
    assert strict("Aurora", backend, tags=["cwd:foreign"])["reason"] == "invalid_metadata"
    assert strict("Aurora", object())["status"] == "refused"


def test_secret_source_never_exposed(tmp_path):
    cfg = config(tmp_path, "raw")
    raw_source(cfg["roots"][0]["path"], text="Aurora api_key=sk-" + "abc123def456ghi789jkl")
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable" and result["items"] == []


def test_metadata_secret_and_security_conflict_refused(tmp_path):
    cfg = config(tmp_path, "raw", "personal")
    path = raw_source(cfg["roots"][0]["path"])
    row = json.loads(path.read_text())
    row["future_field"] = {"credential": "api_key=sk-" + "abc123def456ghi789jkl"}
    path.write_text(json.dumps(row) + "\n")
    doc = Path(cfg["roots"][1]["path"]) / "aurora" / "decision.md"
    doc.parent.mkdir()
    doc.write_text("---\nclassification: sensitive\n---\n# Aurora\nAurora private decision.")
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable" and len(result["problems"]) == 2


def test_expired_raw_handle_rejected(tmp_path, monkeypatch):
    cfg = config(tmp_path, "raw")
    raw_source(cfg["roots"][0]["path"])
    adapter = CompatibilityAdapter(cfg)
    item = adapter.query("Aurora")["items"][0]
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + 31 * 86400)
    with pytest.raises(ValueError, match="expired"):
        adapter.resolve(item)


def test_leaf_swap_cannot_escape_scope(tmp_path, monkeypatch):
    import os

    cfg = config(tmp_path, "personal")
    root = Path(cfg["roots"][0]["path"])
    source = root / "decision.md"
    source.write_text("authorized")
    foreign = tmp_path / "foreign.md"
    foreign.write_text("FOREIGN_CANARY")
    adapter = CompatibilityAdapter(cfg)
    original = os.open

    def swap(path, flags, *args, **kwargs):
        if path == "decision.md":
            source.unlink()
            source.symlink_to(foreign)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swap)
    with pytest.raises(OSError):
        adapter._read(cfg["roots"][0], "decision.md")


@pytest.mark.parametrize("tier", ["raw", "personal"])
def test_service_only_reads_private_snapshot(tmp_path, monkeypatch, tier):
    cfg = config(tmp_path, tier)
    root = Path(cfg["roots"][0]["path"])
    if tier == "raw":
        source = raw_source(root)
        target_class, method = FileStashBackend, "search"
    else:
        source = root / "aurora" / "decision.md"
        source.parent.mkdir()
        source.write_text("# Aurora\nAurora original decision.")
        target_class, method = personal.PersonalMemory, "query"
    before = source.read_bytes()
    original = getattr(target_class, method)

    def swap(self, *args, **kwargs):
        source.write_text(before.decode().replace("Aurora", "Changed Aurora"))
        result = original(self, *args, **kwargs)
        source.write_bytes(before)
        return result

    monkeypatch.setattr(target_class, method, swap)
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable"
    assert "Changed Aurora" not in str(result)
    assert source.read_bytes() == before


def test_nonregular_source_refused_without_blocking(tmp_path):
    import os

    cfg = config(tmp_path, "personal")
    root = Path(cfg["roots"][0]["path"])
    os.mkfifo(root / "pipe.md")
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("tier", ["raw", "personal"])
def test_identical_replacement_invalidates_old_handle(tmp_path, tier):
    cfg = config(tmp_path, tier)
    root = Path(cfg["roots"][0]["path"])
    if tier == "raw":
        source = raw_source(root)
    else:
        source = root / "aurora" / "decision.md"
        source.parent.mkdir()
        source.write_text("# Aurora\nAurora original decision.")
    adapter = CompatibilityAdapter(cfg)
    handle = adapter.query("Aurora")["items"][0]
    before = source.read_bytes()
    source.unlink()
    source.write_bytes(before)
    with pytest.raises(ValueError, match="refresh context"):
        adapter.resolve(handle)
    refreshed = adapter.query("Aurora")["items"][0]
    assert refreshed["text"] == handle["text"] and refreshed["version"] != handle["version"]


@pytest.mark.parametrize("nested", [False, True])
def test_metadata_keys_are_guarded_with_nonstring_values(tmp_path, nested):
    cfg = config(tmp_path, "raw")
    path = raw_source(cfg["roots"][0]["path"])
    row = json.loads(path.read_text())
    secret_key = "api_key=sk-" + "abc123def456ghi789jkl"
    if nested:
        row["future_field"] = {"nested": [{secret_key: True}]}
    else:
        row[secret_key] = True
    path.write_text(json.dumps(row) + "\n")
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable" and secret_key not in str(result)


@pytest.mark.parametrize(
    "prefix,newline", [("", "\r\n"), ("\ufeff", "\n"), ("\ufeff", "\r\n"), ("", "\r")]
)
def test_frontmatter_security_cannot_be_bypassed_with_line_endings(tmp_path, prefix, newline):
    cfg = config(tmp_path, "personal")
    source = Path(cfg["roots"][0]["path"]) / "aurora" / "decision.md"
    source.parent.mkdir()
    source.write_bytes(
        (
            prefix
            + newline.join(
                ["---", "classification: sensitive", "---", "# Aurora", "Aurora sensitive canary"]
            )
        ).encode()
    )
    result = CompatibilityAdapter(cfg).query("Aurora")
    assert result["status"] == "unavailable" and result["items"] == []


def test_existing_summary_and_verdict_sidecars_preserved(tmp_path):
    import os

    from attune.memory.curated_audit import load_memory
    from attune.memory.verdict_log import VerdictRecord, append_verdict

    cfg = config(tmp_path, "curated")
    root = Path(cfg["roots"][0]["path"])
    source = root / "decision.md"
    source.write_text(
        "---\nname: decision\ndescription: Retain the documented exception.\nmetadata:\n  type: reference\n---\n# Decision\nRetain the documented exception."
    )
    old_time = time.time() - 100 * 86400
    os.utime(source, (old_time, old_time))
    summary = root / "summaries_by_path.json"
    summary.write_text(json.dumps({"decision.md": "Aurora quasar schedule reminder"}))
    memory = load_memory(source)
    # Actual persisted review provenance and summary retrieval paths.
    record = VerdictRecord.create("decision", "keep", memory.digest, "synthetic-reviewer")
    append_verdict(root, record)
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    legacy = personal.PersonalMemory(global_root=root, project_root=root).query("Aurora quasar")
    adapter = CompatibilityAdapter(cfg)
    item = adapter.query("Aurora quasar")["items"][0]
    assert item["metadata"]["summary"] == legacy[0]["summary"]
    assert item["metadata"]["status"] == legacy[0]["status"]
    assert item["metadata"]["unverified_days"] == legacy[0]["unverified_days"]
    assert {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()} == before
    summary.write_text(json.dumps({"decision.md": "New schedule"}))
    with pytest.raises(ValueError, match="refresh context"):
        adapter.resolve(item)


def test_document_age_cannot_be_spoofed_by_directory_aba(tmp_path, monkeypatch):
    import os

    cfg = config(tmp_path, "curated")
    root = Path(cfg["roots"][0]["path"])
    source = root / "decision.md"
    source.write_text(
        "---\nname: decision\ndescription: Aurora old decision.\nmetadata:\n  type: reference\n---\n# Aurora\nAurora old decision."
    )
    (root / "summaries_by_path.json").write_text(json.dumps({"decision.md": "Aurora old decision"}))
    from attune.memory.curated_audit import load_memory
    from attune.memory.verdict_log import VerdictRecord, append_verdict

    append_verdict(
        root, VerdictRecord.create("decision", "keep", load_memory(source).digest, "synthetic")
    )
    old_ns = time.time_ns() - 100 * 86400 * 10**9
    os.utime(source, ns=(old_ns, old_ns))
    alternate = tmp_path / "alternate"
    alternate.mkdir()
    (alternate / source.name).write_bytes(source.read_bytes())
    parked = tmp_path / "parked"
    adapter = CompatibilityAdapter(cfg)
    capture, path_stat, set_time = adapter._capture, Path.stat, os.utime
    captured = False

    def arm(root_config, relative):
        nonlocal captured
        result = capture(root_config, relative)
        if relative == source.name:
            captured = True
        return result

    def swap(self, *args, **kwargs):
        if captured and self == source and kwargs.get("follow_symlinks") is False:
            # Restore the original before later version checks: byte/inode
            # validation alone cannot detect the intervening timestamp read.
            root.rename(parked)
            alternate.rename(root)
            try:
                return path_stat(self, *args, **kwargs)
            finally:
                root.rename(alternate)
                parked.rename(root)
        return path_stat(self, *args, **kwargs)

    def stamp(*args, **kwargs):
        nonlocal captured
        captured = False
        return set_time(*args, **kwargs)

    monkeypatch.setattr(adapter, "_capture", arm)
    monkeypatch.setattr(Path, "stat", swap)
    monkeypatch.setattr(os, "utime", stamp)
    packet = adapter.query("Aurora")
    assert packet["status"] == "available", packet["problems"]
    assert packet["items"][0]["metadata"]["unverified_days"] == 100
    assert source.stat().st_mtime_ns == old_ns
