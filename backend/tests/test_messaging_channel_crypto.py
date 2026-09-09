# NOTICE: This file is protected under RCF-PL
from app.models.messaging_channel import MessagingChannel
from app.services.messaging_service import (
    decrypt_channel_config,
    encrypt_channel_config,
)
from app.crypto import is_fernet_token


def test_encrypt_decrypt_channel_config():
    plain_config = {
        "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "chat_id": 987654321,
        "twilio_sid": "twilio_sid_dummy_test_value",
        "twilio_token": "secret_auth_token_xyz",
        "custom_label": "My Test Channel",
    }

    encrypted = encrypt_channel_config(plain_config)

    # Sensitive keys must be encrypted Fernet tokens
    assert is_fernet_token(encrypted["bot_token"])
    assert is_fernet_token(encrypted["twilio_sid"])
    assert is_fernet_token(encrypted["twilio_token"])

    # Non-sensitive keys must remain unchanged
    assert encrypted["chat_id"] == 987654321
    assert encrypted["custom_label"] == "My Test Channel"

    # Decrypt restores original values
    decrypted = decrypt_channel_config(encrypted)
    assert decrypted["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert decrypted["twilio_sid"] == "twilio_sid_dummy_test_value"
    assert decrypted["twilio_token"] == "secret_auth_token_xyz"
    assert decrypted["chat_id"] == 987654321
    assert decrypted["custom_label"] == "My Test Channel"


def test_channel_model_decrypted_config_property():
    plain_config = {
        "bot_token": "123456:TELEGRAM_TOKEN",
        "admin_chat_id": "112233",
    }
    encrypted = encrypt_channel_config(plain_config)

    channel = MessagingChannel(
        id=1,
        user_id=10,
        type="telegram",
        name="Telegram Bot",
        config=encrypted,
    )

    # config holds encrypted ciphertext
    assert is_fernet_token(channel.config["bot_token"])
    # decrypted_config property yields plaintext
    assert channel.decrypted_config["bot_token"] == "123456:TELEGRAM_TOKEN"
    assert channel.decrypted_config["admin_chat_id"] == "112233"


def test_channel_model_legacy_unencrypted_config():
    # Legacy rows in DB might contain unencrypted tokens
    legacy_config = {
        "bot_token": "legacy_unencrypted_token",
        "admin_chat_id": "112233",
    }

    channel = MessagingChannel(
        id=2,
        user_id=10,
        type="telegram",
        name="Legacy Bot",
        config=legacy_config,
    )

    # Returns as-is without crashing
    assert channel.decrypted_config["bot_token"] == "legacy_unencrypted_token"
    assert channel.decrypted_config["admin_chat_id"] == "112233"


def test_idempotent_encryption():
    plain_config = {"bot_token": "token_123"}
    enc1 = encrypt_channel_config(plain_config)
    # Encrypting already encrypted token shouldn't double-encrypt
    enc2 = encrypt_channel_config(enc1)
    assert enc1["bot_token"] == enc2["bot_token"]
    assert decrypt_channel_config(enc2)["bot_token"] == "token_123"
