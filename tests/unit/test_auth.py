# tests/unit/test_auth.py
from datetime import timedelta
from jose import jwt
from src.to_do_list.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from src.to_do_list.settings import settings


def test_verify_password():

    plain_password = "plain_password"
    hashed_password = get_password_hash(plain_password)

    assert verify_password(plain_password, hashed_password) is True
    assert verify_password("wrong_password", hashed_password) is False


def test_create_access_token_payload():
   
    username = "testuser"
    token = create_access_token(data={"sub": username})

    payload = jwt.decode(token, str(settings.jwt_secret_key), algorithms=[settings.algorithm], options={"verify_signature": False})

    assert payload.get("sub") == username
    assert "exp" in payload 