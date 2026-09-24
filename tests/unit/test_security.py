import pytest
from services.api.core.security import hash_password, verify_password, create_access_token, decode_access_token, encrypt_secret, decrypt_secret

def test_password_hashing():
    raw = "MySuperSecret123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_tokens():
    payload = {"sub": "usr_12345", "email": "dev@ziref.app"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "usr_12345"
    assert decoded["email"] == "dev@ziref.app"

def test_secret_encryption():
    secret = "sk_live_1234567890abcdef"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret
