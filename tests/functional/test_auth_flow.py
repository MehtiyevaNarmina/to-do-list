# tests/functional/test_auth_flow.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.to_do_list.models import User


def test_register_user(client: TestClient, session: Session):
    user_data = {
        "first_name": "New",
        "last_name": "User",
        "username": "newuser",
        "password": "newpassword",
    }
    response = client.post("/register/", json=user_data)

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["username"] == user_data["username"]
    assert "id" in response_data
    assert "hashed_password" not in response_data

    db_user = session.exec(select(User).where(User.username == user_data["username"])).first()
    assert db_user is not None
    assert db_user.username == user_data["username"]


def test_register_user_failure_on_duplicate_username(client: TestClient, test_user: User):
    user_data = {
        "first_name": "Another",
        "last_name": "User",
        "username": "testuser",  # Duplicate username
        "password": "newpassword",
    }
    response = client.post("/register/", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"


def test_login_for_access_token(client: TestClient, test_user: User):
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"


def test_login_with_incorrect_password(client: TestClient, test_user: User):
    login_data = {"username": test_user.username, "password": "wrongpassword"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_with_nonexistent_user(client: TestClient):
    login_data = {"username": "nonexistentuser", "password": "password"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password" 