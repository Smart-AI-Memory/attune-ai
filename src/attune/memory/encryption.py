"""Encryption manager for long-term memory system

Provides AES-256-GCM encryption/decryption for SENSITIVE patterns.
Extracted from long_term.py for better modularity and testability.

Key Features:
- AES-256-GCM authenticated encryption
- Master key management (environment variable, file, or generated)
- Base64-encoded output for safe storage
- Proper error handling and security logging

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import base64
import binascii
import os
from pathlib import Path

import structlog

from .long_term_types import SecurityError

logger = structlog.get_logger(__name__)

# Check for cryptography library
try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False
    logger.warning("cryptography library not available - encryption disabled")


class EncryptionManager:
    """Manages encryption/decryption for SENSITIVE patterns.

    Uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption.
    Keys are derived from a master key using HKDF.
    """

    def __init__(self, master_key: bytes | None = None):
        """Initialize encryption manager.

        Args:
            master_key: 32-byte master key (or None to generate/load)

        """
        if not HAS_ENCRYPTION:
            if master_key is not None:
                raise RuntimeError(
                    "cryptography library required when master_key is provided. "
                    "Install with: pip install cryptography"
                )
            logger.warning("Encryption not available - install cryptography library")
            self.enabled = False
            return

        self.enabled = True
        self.master_key = master_key or self._load_or_generate_key()

    def _load_or_generate_key(self) -> bytes:
        """Load master key from environment or generate new one.

        Production: Set ATTUNE_MASTER_KEY environment variable (EMPATHY_MASTER_KEY also accepted)
        Development: Generates ephemeral key (warning logged)
        """
        from attune.config.env_compat import get_attune_env

        # Check environment variable first
        if env_key := get_attune_env("MASTER_KEY"):
            try:
                return base64.b64decode(env_key)
            except (binascii.Error, ValueError) as e:
                logger.error("invalid_master_key_in_env", error=str(e))
                raise ValueError("Invalid ATTUNE_MASTER_KEY format") from e

        # Check key file
        key_file = Path.home() / ".attune" / "master.key"
        if key_file.exists():
            try:
                return key_file.read_bytes()
            except (OSError, PermissionError) as e:
                logger.error("failed_to_load_key_file", error=str(e))

        # Generate ephemeral key (NOT for production)
        logger.warning(
            "no_master_key_found",
            message="Generating ephemeral encryption key - set EMPATHY_MASTER_KEY for production",
        )
        return AESGCM.generate_key(bit_length=256)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: Content to encrypt

        Returns:
            Base64-encoded ciphertext with format: nonce||ciphertext||tag

        Raises:
            SecurityError: If encryption fails

        """
        if not self.enabled:
            raise SecurityError("Encryption not available - install cryptography library")

        try:
            # Generate random 96-bit nonce (12 bytes)
            nonce = os.urandom(12)

            # Create AESGCM cipher
            aesgcm = AESGCM(self.master_key)

            # Encrypt and authenticate
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

            # Combine nonce + ciphertext for storage
            encrypted_data = nonce + ciphertext

            # Return base64-encoded
            return base64.b64encode(encrypted_data).decode("utf-8")

        except (ValueError, TypeError, UnicodeEncodeError) as e:
            logger.error("encryption_failed", error=str(e))
            raise SecurityError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext_b64: Base64-encoded encrypted data

        Returns:
            Decrypted plaintext

        Raises:
            SecurityError: If decryption fails (invalid key, corrupted data, etc.)

        """
        if not self.enabled:
            raise SecurityError("Encryption not available - install cryptography library")

        try:
            # Decode from base64
            encrypted_data = base64.b64decode(ciphertext_b64)

            # Extract nonce (first 12 bytes) and ciphertext (rest)
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # Create AESGCM cipher
            aesgcm = AESGCM(self.master_key)

            # Decrypt and verify
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext_bytes.decode("utf-8")

        except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, InvalidTag) as e:
            logger.error("decryption_failed", error=str(e))
            raise SecurityError(f"Decryption failed: {e}") from e
