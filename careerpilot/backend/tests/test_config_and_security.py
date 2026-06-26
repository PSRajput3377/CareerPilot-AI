"""Tests for configuration loading and secret encryption (Modules 19 & 20)."""

from __future__ import annotations

import pytest

from careerpilot.backend.core.security import (
    EncryptionError,
    SecretCipher,
    generate_key,
)


def test_config_loads_yaml_sections():
    from careerpilot.backend.config.settings import reload_settings

    settings = reload_settings()
    # YAML-sourced structured config is present with sane defaults.
    assert settings.rate_limits.emails_per_hour >= 1
    assert settings.retry.max_attempts >= 1
    assert isinstance(settings.scheduling.followup_offsets_days, list)


def test_generate_key_is_usable():
    key = generate_key().encode()
    cipher = SecretCipher(key=key)
    token = cipher.encrypt("hunter2")
    assert token != "hunter2"
    assert cipher.decrypt(token) == "hunter2"


def test_decrypt_with_wrong_key_fails():
    cipher_a = SecretCipher(key=generate_key().encode())
    cipher_b = SecretCipher(key=generate_key().encode())
    token = cipher_a.encrypt("secret")
    with pytest.raises(EncryptionError):
        cipher_b.decrypt(token)
