"""Encryption service for sensitive data (Matrix tokens, passwords).

Uses Fernet symmetric encryption with keys derived from ENCRYPTION_KEY.
Supports automatic migration of plaintext tokens on application startup.
"""

import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import ENCRYPTION_KEY

logger = logging.getLogger("encryption")

# Prefix to identify encrypted values
ENCRYPTED_PREFIX = "enc:v1:"


def _derive_key(key_material: str) -> bytes:
    """Derive a Fernet-compatible key from the encryption key material.

    Uses PBKDF2 with a static salt (key is already high-entropy).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"messenger-service-salt-v1",
        iterations=100_000,
    )
    # Handle hex or base64 encoded keys
    if len(key_material) == 64 and all(c in "0123456789abcdefABCDEF" for c in key_material):
        key_bytes = bytes.fromhex(key_material)
    else:
        try:
            key_bytes = base64.b64decode(key_material)
        except Exception:
            key_bytes = key_material.encode("utf-8")

    derived = kdf.derive(key_bytes)
    return base64.urlsafe_b64encode(derived)


# Initialize Fernet with derived key
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet instance."""
    global _fernet
    if _fernet is None:
        key = _derive_key(ENCRYPTION_KEY)
        _fernet = Fernet(key)
    return _fernet


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token/password for storage.

    Returns a prefixed string to identify encrypted values.
    """
    if not plaintext:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return ENCRYPTED_PREFIX + base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_token(stored_value: str) -> str:
    """Decrypt a stored token/password.

    Handles both encrypted (prefixed) and legacy plaintext values.
    Returns the plaintext token.
    """
    if not stored_value:
        return ""

    # Check if already encrypted
    if stored_value.startswith(ENCRYPTED_PREFIX):
        try:
            fernet = _get_fernet()
            encrypted_data = base64.urlsafe_b64decode(
                stored_value[len(ENCRYPTED_PREFIX):]
            )
            return fernet.decrypt(encrypted_data).decode("utf-8")
        except (InvalidToken, Exception) as e:
            logger.error("Failed to decrypt token: %s", e)
            raise ValueError("Failed to decrypt token") from e

    # Legacy plaintext - return as-is (will be migrated on next update)
    return stored_value


def is_encrypted(stored_value: str) -> bool:
    """Check if a stored value is already encrypted."""
    if not stored_value:
        return True  # Empty values don't need encryption
    return stored_value.startswith(ENCRYPTED_PREFIX)


def migrate_encrypt_if_needed(plaintext: str) -> tuple[str, bool]:
    """Encrypt a value if it's not already encrypted.

    Returns (encrypted_value, was_migrated).
    """
    if not plaintext:
        return "", False

    if is_encrypted(plaintext):
        return plaintext, False

    return encrypt_token(plaintext), True
