"""Security primitives (Module 20).

Provides symmetric encryption for secrets at rest (SMTP passwords, API keys)
using Fernet (AES-128-CBC + HMAC). Credentials are sourced from the environment
and encrypted before persistence — never hardcoded, never stored in plaintext.

Usage as a module entrypoint to mint a key for ``.env``::

    python -m careerpilot.backend.core.security generate-key
"""

from __future__ import annotations

import sys

from cryptography.fernet import Fernet, InvalidToken

from careerpilot.backend.config.settings import get_settings


class EncryptionError(RuntimeError):
    """Raised when encryption/decryption fails or no key is configured."""


def generate_key() -> str:
    """Generate a new urlsafe base64 Fernet key suitable for ``.env``."""
    return Fernet.generate_key().decode("utf-8")


def _resolve_key() -> bytes:
    """Resolve the active Fernet key from settings.

    In production a key is mandatory. In non-production environments we fall
    back to a deterministic-per-process ephemeral key so local dev and tests do
    not require operator setup — such data is not portable across restarts.
    """
    settings = get_settings()
    if settings.encryption_key:
        return settings.encryption_key.encode("utf-8")
    if settings.is_production:
        raise EncryptionError(
            "CAREERPILOT_ENCRYPTION_KEY must be set in production. "
            "Generate one with: python -m careerpilot.backend.core.security generate-key"
        )
    # Non-production fallback: stable for the lifetime of the process.
    return _ephemeral_key()


_EPHEMERAL: bytes | None = None


def _ephemeral_key() -> bytes:
    global _EPHEMERAL
    if _EPHEMERAL is None:
        _EPHEMERAL = Fernet.generate_key()
    return _EPHEMERAL


class SecretCipher:
    """Thin wrapper around Fernet for encrypting/decrypting string secrets."""

    def __init__(self, key: bytes | None = None) -> None:
        self._fernet = Fernet(key or _resolve_key())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a UTF-8 string, returning an urlsafe token string."""
        if plaintext is None:
            raise EncryptionError("Cannot encrypt None")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Decrypt a token produced by :meth:`encrypt`."""
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:  # pragma: no cover - defensive
            raise EncryptionError("Failed to decrypt secret (invalid key or token)") from exc


def get_cipher() -> SecretCipher:
    """Factory for the default cipher (resolves the configured key)."""
    return SecretCipher()


def _main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0] == "generate-key":
        print(generate_key())
        return 0
    print("Usage: python -m careerpilot.backend.core.security generate-key", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv[1:]))
