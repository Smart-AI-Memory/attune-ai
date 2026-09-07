"""Real filesystem receipts for installation-key persistence and failure safety."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from attune.elicitation.surface_key import load_installation_key
from attune.elicitation.surface_policy import SurfaceBinding, SurfaceContextStore

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX installation-key adapter")


def test_key_survives_restart_but_interactions_do_not(tmp_path):
    first = SurfaceContextStore(load_installation_key(tmp_path))
    binding = SurfaceBinding(first.server_instance_id, "s", "c", "interactive_form", "f", "f", "d")
    receipt = first.issue(binding)
    restarted = SurfaceContextStore(load_installation_key(tmp_path))
    current = replace(binding, server_instance_id=restarted.server_instance_id)
    assert restarted.context_reason(receipt, current) == "foreign_receipt"
    forged = receipt[:-1] + ("1" if receipt[-1] == "0" else "0")
    assert restarted.context_reason(forged, current) == "invalid_receipt"
    assert set((tmp_path / "surface-auth").iterdir()) == {tmp_path / "surface-auth/receipt.key"}


def test_concurrent_startups_share_one_complete_key(tmp_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(load_installation_key, [tmp_path] * 32))
    assert len(set(keys)) == 1 and len(keys[0]) == 32
    assert len(list((tmp_path / "surface-auth").iterdir())) == 1


@pytest.mark.parametrize("contents", [b"", b"short", b"x" * 33])
def test_corrupt_existing_key_is_never_replaced(tmp_path, contents):
    load_installation_key(tmp_path)
    path = tmp_path / "surface-auth/receipt.key"
    path.write_bytes(contents)
    with pytest.raises(ValueError, match="exactly 32"):
        load_installation_key(tmp_path)
    assert path.read_bytes() == contents


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes and symlinks")
@pytest.mark.parametrize("target", ["directory", "key", "dangling_key"])
def test_symlink_entries_are_rejected(tmp_path, target):
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    if target == "directory":
        (tmp_path / "surface-auth").symlink_to(external, target_is_directory=True)
    else:
        directory = tmp_path / "surface-auth"
        directory.mkdir(mode=0o700)
        outside_key = external / "key"
        if target == "key":
            outside_key.write_bytes(b"x" * 32)
        (directory / "receipt.key").symlink_to(outside_key)
    with pytest.raises(ValueError):
        load_installation_key(tmp_path)
    assert list(external.iterdir()) == ([external / "key"] if target == "key" else [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX ownership and permission checks")
@pytest.mark.parametrize("target", ["surface-auth", "surface-auth/receipt.key"])
def test_nonprivate_existing_entries_fail_closed(tmp_path, target):
    load_installation_key(tmp_path)
    (tmp_path / target).chmod(0o755)
    with pytest.raises(ValueError, match="private"):
        load_installation_key(tmp_path)


def test_public_system_path_rejected():
    with pytest.raises(ValueError, match="system directory"):
        load_installation_key(Path("/etc/attune"))


def test_interrupted_publication_leaves_no_partial_key(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("fixture disk failure")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="fixture disk failure"):
        load_installation_key(tmp_path)
    assert list((tmp_path / "surface-auth").iterdir()) == []


def test_separate_process_startups_share_key(tmp_path):
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(
        max_workers=3, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        keys = list(pool.map(load_installation_key, [tmp_path] * 6))
    assert len(set(keys)) == 1 and len(keys[0]) == 32


def test_unsupported_platform_does_not_create_storage(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from attune.elicitation import surface_key

    monkeypatch.setattr(surface_key, "os", SimpleNamespace(name="nt"))
    with pytest.raises(OSError, match="not available on this platform"):
        load_installation_key(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_temporary_file_creation_failure_leaves_no_key(tmp_path, monkeypatch):
    from attune.elicitation import surface_key

    def unavailable(**_):
        raise OSError("fixture temporary storage unavailable")

    monkeypatch.setattr(surface_key.tempfile, "NamedTemporaryFile", unavailable)
    with pytest.raises(OSError, match="temporary storage unavailable"):
        load_installation_key(tmp_path)
    assert list((tmp_path / "surface-auth").iterdir()) == []


def test_key_replaced_during_open_fails_closed(tmp_path, monkeypatch):
    original_key = load_installation_key(tmp_path)
    path = tmp_path / "surface-auth/receipt.key"
    replacement = path.with_name("replacement")
    replacement.write_bytes(b"r" * 32)
    replacement.chmod(0o600)
    real_open = os.open

    def replace_before_open(filename, flags, *args, **kwargs):
        if Path(filename) == path:
            replacement.replace(path)
        return real_open(filename, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", replace_before_open)
    with pytest.raises(ValueError, match="changed while opening"):
        load_installation_key(tmp_path)
    assert path.read_bytes() == b"r" * 32 != original_key
    assert set(path.parent.iterdir()) == {path}


def test_concurrent_publisher_wins_without_leaking_temporary_key(tmp_path, monkeypatch):
    real_link = os.link
    winner = b"w" * 32

    def publish_competing_key(source, destination):
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(winner)
        # Exercise the actual no-replace publication failure against the winning file.
        return real_link(source, destination)

    monkeypatch.setattr(os, "link", publish_competing_key)
    assert load_installation_key(tmp_path) == winner
    path = tmp_path / "surface-auth/receipt.key"
    assert set(path.parent.iterdir()) == {path}
    assert load_installation_key(tmp_path) == winner
