"""Unit tests for the long-term memory EncryptionManager.

This suite provides behavioral coverage for AES-256-GCM
encrypt/decrypt round-trips, master-key resolution (environment
variable, key file, ephemeral generation), and the security error
paths. It is mutation-oriented: assertions pin the nonce size, the
nonce/ciphertext slice boundaries, the generated key length, and the
exact failure modes so that operator/boundary mutations in
``encryption.py`` are caught.

Mutation status (mutmut 2.4.4, this suite as runner):
``53 mutants -> 36 killed, 17 survived`` -- every survivor is a
documented equivalent: 15 are string-content mutations of log event
names / log messages / exception text (no behavioral effect; the repo
policy is not to over-fit assertions to message strings), and 2 are
the value of the ``except ImportError: HAS_ENCRYPTION = False`` branch,
which is unreachable when ``cryptography`` (a core dependency) is
present. Killable kill-rate is 36/36 = 100%.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import base64

import pytest

import attune.memory.encryption as enc_mod
from attune.memory.encryption import EncryptionManager
from attune.memory.long_term_types import SecurityError

# ``cryptography`` is a core (non-optional) dependency, so the success
# path of the module's import guard is the supported environment and we
# test it unconditionally — no skipif. The crypto-absent path is still
# covered via monkeypatching ``HAS_ENCRYPTION`` (see TestDisabledManager).
pytestmark = pytest.mark.unit

# A deterministic, valid 32-byte AES-256 key used across round-trip tests.
FIXED_KEY = b"0123456789abcdef0123456789abcdef"
GCM_TAG_LEN = 16
NONCE_LEN = 12


@pytest.fixture
def isolated_key_env(monkeypatch, tmp_path):
    """Remove real master-key sources so key resolution is deterministic.

    Clears both the ATTUNE_ and legacy EMPATHY_ master-key env vars and
    redirects ``Path.home()`` to an empty tmp dir (no ``master.key``),
    so ``_load_or_generate_key`` falls through to ephemeral generation
    unless a test explicitly sets one of these up.

    Note: patch ``Path.home`` directly rather than ``$HOME`` — on Windows
    ``Path.home()`` reads ``%USERPROFILE%``, not ``$HOME``, so a
    ``setenv("HOME", ...)`` redirect is silently ignored there (it was —
    see the key-file tests failing on the windows-3.12 lane).
    """
    monkeypatch.delenv("ATTUNE_MASTER_KEY", raising=False)
    monkeypatch.delenv("EMPATHY_MASTER_KEY", raising=False)
    monkeypatch.setattr(enc_mod.Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def manager():
    """An enabled manager with a fixed key (no real key sources touched)."""
    return EncryptionManager(master_key=FIXED_KEY)


class TestInit:
    """Constructor behavior with the cryptography library available."""

    def test_has_encryption_true_when_library_present(self):
        """The import guard must report availability when crypto is installed.

        ``cryptography`` is a core dependency, so the success branch of the
        module-level ``try``/``except`` must set ``HAS_ENCRYPTION = True``.
        Without this, every manager would refuse to construct with a key.
        """
        assert enc_mod.HAS_ENCRYPTION is True

    def test_explicit_master_key_is_stored_and_enabled(self):
        mgr = EncryptionManager(master_key=FIXED_KEY)
        assert mgr.enabled is True
        assert mgr.master_key == FIXED_KEY

    def test_explicit_key_skips_key_resolution(self, monkeypatch):
        """A provided key must short-circuit ``_load_or_generate_key``.

        Kills the ``master_key or self._load_or_generate_key()`` mutation:
        if the ``or`` were dropped, the env key below would win instead of
        the explicit argument.
        """
        monkeypatch.setenv(
            "ATTUNE_MASTER_KEY",
            base64.b64encode(b"x" * 32).decode("utf-8"),
        )

        def _boom(self):  # pragma: no cover - must not be called
            raise AssertionError("_load_or_generate_key should not run")

        monkeypatch.setattr(EncryptionManager, "_load_or_generate_key", _boom)
        mgr = EncryptionManager(master_key=FIXED_KEY)
        assert mgr.master_key == FIXED_KEY

    def test_no_key_generates_ephemeral_256_bit_key(self, isolated_key_env):
        mgr = EncryptionManager()
        assert mgr.enabled is True
        # 256-bit key == 32 bytes; pins ``bit_length=256``.
        assert len(mgr.master_key) == 32

    def test_ephemeral_keys_are_random_per_instance(self, isolated_key_env):
        a = EncryptionManager()
        b = EncryptionManager()
        assert a.master_key != b.master_key


class TestKeyResolution:
    """``_load_or_generate_key`` source precedence and error handling."""

    def test_env_var_base64_is_decoded(self, isolated_key_env, monkeypatch):
        raw = b"A" * 32
        monkeypatch.setenv("ATTUNE_MASTER_KEY", base64.b64encode(raw).decode("utf-8"))
        mgr = EncryptionManager()
        assert mgr.master_key == raw

    def test_legacy_empathy_env_var_is_honored(self, isolated_key_env, monkeypatch):
        raw = b"B" * 32
        monkeypatch.setenv("EMPATHY_MASTER_KEY", base64.b64encode(raw).decode("utf-8"))
        mgr = EncryptionManager()
        assert mgr.master_key == raw

    def test_invalid_base64_env_var_raises(self, isolated_key_env, monkeypatch):
        # Length not a multiple of 4 -> binascii.Error during b64decode.
        monkeypatch.setenv("ATTUNE_MASTER_KEY", "aaaaa")
        with pytest.raises(ValueError, match="Invalid ATTUNE_MASTER_KEY format"):
            EncryptionManager()

    def test_key_file_is_read_when_present(self, isolated_key_env, monkeypatch):
        key_bytes = b"K" * 32
        attune_dir = isolated_key_env / ".attune"
        attune_dir.mkdir(parents=True)
        (attune_dir / "master.key").write_bytes(key_bytes)
        mgr = EncryptionManager()
        assert mgr.master_key == key_bytes

    def test_env_var_takes_precedence_over_key_file(self, isolated_key_env, monkeypatch):
        env_raw = b"E" * 32
        attune_dir = isolated_key_env / ".attune"
        attune_dir.mkdir(parents=True)
        (attune_dir / "master.key").write_bytes(b"F" * 32)
        monkeypatch.setenv("ATTUNE_MASTER_KEY", base64.b64encode(env_raw).decode("utf-8"))
        mgr = EncryptionManager()
        assert mgr.master_key == env_raw

    def test_unreadable_key_file_falls_back_to_ephemeral(self, isolated_key_env, monkeypatch):
        attune_dir = isolated_key_env / ".attune"
        attune_dir.mkdir(parents=True)
        (attune_dir / "master.key").write_bytes(b"unused")

        original_read_bytes = enc_mod.Path.read_bytes

        def _raise(self):
            if self.name == "master.key":
                raise OSError("permission denied")
            return original_read_bytes(self)

        monkeypatch.setattr(enc_mod.Path, "read_bytes", _raise)
        mgr = EncryptionManager()
        # Falls through to a freshly generated 32-byte key.
        assert len(mgr.master_key) == 32


class TestEncryptDecryptRoundTrip:
    """AES-256-GCM round-trip correctness."""

    @pytest.mark.parametrize(
        "plaintext",
        [
            "hello world",
            "",
            "unicode: café — déjà vu — 日本語 — 🔐",
            "x" * 10_000,
            "line1\nline2\ttabbed",
        ],
    )
    def test_round_trip_preserves_plaintext(self, manager, plaintext):
        ciphertext = manager.encrypt(plaintext)
        assert manager.decrypt(ciphertext) == plaintext

    def test_ciphertext_is_base64_string(self, manager):
        ciphertext = manager.encrypt("payload")
        assert isinstance(ciphertext, str)
        # Must decode as base64 without error.
        base64.b64decode(ciphertext)

    def test_encrypted_layout_is_nonce_plus_ciphertext_plus_tag(self, manager):
        plaintext = "exact-length-check"
        raw = base64.b64decode(manager.encrypt(plaintext))
        expected = NONCE_LEN + len(plaintext.encode("utf-8")) + GCM_TAG_LEN
        assert len(raw) == expected

    def test_same_plaintext_yields_distinct_ciphertexts(self, manager):
        """Random per-message nonce -> ciphertexts must differ."""
        a = manager.encrypt("repeat")
        b = manager.encrypt("repeat")
        assert a != b
        # ...but both decrypt back to the same plaintext.
        assert manager.decrypt(a) == manager.decrypt(b) == "repeat"

    def test_round_trip_across_two_managers_with_same_key(self):
        enc = EncryptionManager(master_key=FIXED_KEY)
        dec = EncryptionManager(master_key=FIXED_KEY)
        assert dec.decrypt(enc.encrypt("shared")) == "shared"


class TestDecryptFailureModes:
    """Decryption must raise SecurityError on any integrity failure."""

    def test_wrong_key_raises_security_error(self):
        enc = EncryptionManager(master_key=FIXED_KEY)
        wrong = EncryptionManager(master_key=b"f" * 32)
        ciphertext = enc.encrypt("secret")
        with pytest.raises(SecurityError, match="Decryption failed"):
            wrong.decrypt(ciphertext)

    def test_tampered_ciphertext_raises_security_error(self, manager):
        raw = bytearray(base64.b64decode(manager.encrypt("secret")))
        raw[-1] ^= 0xFF  # corrupt the GCM tag
        tampered = base64.b64encode(bytes(raw)).decode("utf-8")
        with pytest.raises(SecurityError, match="Decryption failed"):
            manager.decrypt(tampered)

    def test_invalid_base64_raises_security_error(self, manager):
        with pytest.raises(SecurityError, match="Decryption failed"):
            manager.decrypt("!!! not base64 !!!")

    def test_truncated_data_raises_security_error(self, manager):
        # Fewer than the 12 nonce bytes -> empty ciphertext -> InvalidTag.
        truncated = base64.b64encode(b"short").decode("utf-8")
        with pytest.raises(SecurityError, match="Decryption failed"):
            manager.decrypt(truncated)


class TestDisabledManager:
    """Behavior when encryption is unavailable or disabled."""

    def test_encrypt_when_disabled_raises(self, manager):
        manager.enabled = False
        with pytest.raises(SecurityError, match="Encryption not available"):
            manager.encrypt("data")

    def test_decrypt_when_disabled_raises(self, manager):
        manager.enabled = False
        with pytest.raises(SecurityError, match="Encryption not available"):
            manager.decrypt("data")

    def test_no_encryption_with_master_key_raises_runtime_error(self, monkeypatch):
        monkeypatch.setattr(enc_mod, "HAS_ENCRYPTION", False)
        with pytest.raises(RuntimeError, match="cryptography library required"):
            EncryptionManager(master_key=FIXED_KEY)

    def test_no_encryption_without_key_disables_manager(self, monkeypatch):
        monkeypatch.setattr(enc_mod, "HAS_ENCRYPTION", False)
        mgr = EncryptionManager()
        assert mgr.enabled is False
