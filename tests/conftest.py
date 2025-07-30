import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel

from src.to_do_list.main import app, get_session
from src.to_do_list.settings import settings
from src.to_do_list.models import User
from src.to_do_list.auth import get_password_hash

# Use the database URL from settings, which will be overridden by the environment variable in docker-compose
connection_string = str(settings.database_url).replace("postgresql", "postgresql+psycopg")
engine = create_engine(connection_string, echo=False)


@pytest.fixture(scope="function", name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function", name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def user_fixture(session: Session):
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "password": "testpassword",
    }
    hashed_password = get_password_hash(user_data["password"])
    user = User(
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        username=user_data["username"],
        hashed_password=hashed_password,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/token", data=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"} 