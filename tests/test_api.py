import pytest
from httpx import AsyncClient # Для асинхронных HTTP запросов в тестах
from sqlmodel import Session, SQLModel, create_engine, select


from src.to_do_list.main import app
from src.to_do_list.create_db import create_tables, get_session, get_db_engine
from src.to_do_list.models import User, Task, UserCreate, TaskCreate, TaskStatus # Импортируем необходимые модели
from src.to_do_list.auth import get_password_hash # Возможно, понадобится для создания тестовых пользователей напрямую

# --- Фикстуры для тестовой базы данных ---
# Эти фикстуры аналогичны тем, что были в test_database.py,
# но адаптированы для использования с TestClient.

@pytest.fixture(name="db_engine")
def db_engine_fixture():
    """
    Фикстура для создания in-memory SQLite базы данных для тестов.
    Каждый тест получает чистую базу данных.
    """
    # Создаем in-memory SQLite движок
    engine = create_engine("sqlite://", echo=False)
    # Создаем все таблицы на основе метаданных SQLModel
    SQLModel.metadata.create_all(engine)
    yield engine
    # Очистка не требуется для in-memory SQLite, она удаляется автоматически

@pytest.fixture(name="session")
def session_fixture(db_engine):
    """
    Фикстура для получения сессии базы данных для тестов.
    """
    with Session(db_engine) as session:
        yield session

@pytest.fixture(name="client")
async def client_fixture(db_engine):
    """
    Фикстура для создания тестового клиента FastAPI.
    Переопределяет зависимость get_session, чтобы использовать тестовую БД.
    """
    # Переопределяем зависимость get_session в приложении FastAPI,
    # чтобы она использовала нашу тестовую базу данных.
    def get_session_override():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    # Инициализация движка приложения через глобальную переменную _app_engine
    # больше не нужна здесь, так как мы используем переопределение зависимостей.
    # Глобальная переменная _app_engine в main.py будет инициализирована lifespan,
    # но для тестов нам это неважно, так как мы переопределяем get_session.

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Вызываем create_tables() вручную, так как lifespan не всегда срабатывает
        # при прямом использовании TestClient без реального uvicorn.
        # Если lifespan гарантированно работает, этот вызов можно убрать.
        create_tables(engine_instance=db_engine) # Убедитесь, что create_tables принимает engine_instance
        yield client
    
    # Очистка переопределений зависимостей после теста
    app.dependency_overrides.clear()
    # Сброс глобального _app_engine здесь не нужен, так как мы его не трогали.


# --- Вспомогательная фикстура для создания и логина тестового пользователя ---
@pytest.fixture(name="test_user_data")
def test_user_data_fixture():
    """Возвращает данные для тестового пользователя."""
    return {
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "password": "testpassword"
    }

@pytest.fixture(name="auth_client")
async def auth_client_fixture(client: AsyncClient, test_user_data: dict):
    """
    Фикстура для получения авторизованного клиента.
    Регистрирует пользователя и выполняет вход, возвращая клиент с токеном.
    """
    # 1. Зарегистрировать пользователя
    register_response = await client.post("/register/", json=test_user_data)
    assert register_response.status_code == 201

    # 2. Войти в систему и получить токен
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    token_response = await client.post("/token", data=login_data) # Используем data= для OAuth2PasswordRequestForm
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    # 3. Добавить токен в заголовки клиента для последующих запросов
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    # Очистка заголовков после теста
    client.headers.pop("Authorization", None)


# --- Тесты API-эндпоинтов ---

async def test_register_user(client: AsyncClient, test_user_data: dict):
    """
    Тест на успешную регистрацию пользователя.
    """
    response = await client.post("/register/", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == test_user_data["username"]
    assert "id" in data
    assert "hashed_password" not in data # Пароль не должен возвращаться

async def test_register_existing_user(client: AsyncClient, test_user_data: dict):
    """
    Тест на попытку регистрации пользователя с уже существующим именем.
    """
    # Сначала регистрируем пользователя
    response = await client.post("/register/", json=test_user_data)
    assert response.status_code == 201

    # Попытка зарегистрировать того же пользователя снова
    response = await client.post("/register/", json=test_user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

async def test_login_for_access_token(client: AsyncClient, test_user_data: dict):
    """
    Тест на успешный вход в систему и получение токена.
    """
    # Сначала регистрируем пользователя
    await client.post("/register/", json=test_user_data)

    # Затем пытаемся войти
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = await client.post("/token", data=login_data) # Используем data= для form-data
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_incorrect_password(client: AsyncClient, test_user_data: dict):
    """
    Тест на вход с неверным паролем.
    """
    # Сначала регистрируем пользователя
    await client.post("/register/", json=test_user_data)

    # Затем пытаемся войти с неверным паролем
    login_data = {
        "username": test_user_data["username"],
        "password": "wrongpassword"
    }
    response = await client.post("/token", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

async def test_create_task_for_user(auth_client: AsyncClient):
    """
    Тест на создание задачи для авторизованного пользователя.
    """
    task_data = {"title": "Купить продукты", "description": "Молоко, хлеб, яйца", "status": TaskStatus.pending}
    response = await auth_client.post("/tasks/", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["status"] == task_data["status"]
    assert "id" in data
    assert "user_id" in data # Убедитесь, что user_id присваивается

async def test_get_my_tasks(auth_client: AsyncClient):
    """
    Тест на получение задач авторизованного пользователя.
    """
    # Создаем несколько задач для тестового пользователя
    await auth_client.post("/tasks/", json={"title": "Задача 1", "status": TaskStatus.pending})
    await auth_client.post("/tasks/", json={"title": "Задача 2", "status": TaskStatus.completed})

    response = await auth_client.get("/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Задача 1"
    assert data[1]["title"] == "Задача 2"

async def test_get_my_tasks_with_pagination_and_filter(auth_client: AsyncClient):
    """
    Тест на получение задач с пагинацией и фильтрацией по статусу.
    """
    # Создаем 5 задач
    for i in range(1, 6):
        status = TaskStatus.pending if i % 2 == 0 else TaskStatus.completed
        await auth_client.post("/tasks/", json={"title": f"Задача {i}", "status": status})

    # Получаем 2 задачи, начиная со смещения 1, только 'pending'
    response = await auth_client.get("/tasks/?offset=1&limit=2&status_filter=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Задача 2"
    assert data[1]["title"] == "Задача 4"
    assert all(task["status"] == TaskStatus.pending for task in data)


async def test_get_single_task(auth_client: AsyncClient):
    """
    Тест на получение одной задачи по ID.
    """
    # Создаем задачу
    create_response = await auth_client.post("/tasks/", json={"title": "Единичная задача"})
    task_id = create_response.json()["id"]

    response = await auth_client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Единичная задача"
    assert data["id"] == task_id

async def test_get_single_task_not_found(auth_client: AsyncClient):
    """
    Тест на получение несуществующей задачи.
    """
    response = await auth_client.get("/tasks/99999") # Несуществующий ID
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."

async def test_get_single_task_unauthorized_access(client: AsyncClient, test_user_data: dict, db_engine):
    """
    Тест на попытку получить задачу другого пользователя (неавторизованный доступ).
    """
    # Создаем первого пользователя и его задачу
    await client.post("/register/", json=test_user_data)
    login_data_1 = {"username": test_user_data["username"], "password": test_user_data["password"]}
    token_response_1 = await client.post("/token", data=login_data_1)
    client.headers["Authorization"] = f"Bearer {token_response_1.json()['access_token']}"
    task_response = await client.post("/tasks/", json={"title": "Задача первого пользователя"})
    task_id = task_response.json()["id"]
    client.headers.pop("Authorization") # Сбрасываем токен первого пользователя

    # Создаем второго пользователя
    test_user_data_2 = {
        "first_name": "Another", "last_name": "User",
        "username": "anotheruser", "password": "anotherpassword"
    }
    await client.post("/register/", json=test_user_data_2)
    login_data_2 = {"username": test_user_data_2["username"], "password": test_user_data_2["password"]}
    token_response_2 = await client.post("/token", data=login_data_2)
    client.headers["Authorization"] = f"Bearer {token_response_2.json()['access_token']}"

    # Второй пользователь пытается получить задачу первого пользователя
    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this task."


async def test_update_task(auth_client: AsyncClient):
    """
    Тест на успешное обновление задачи.
    """
    # Создаем задачу
    create_response = await auth_client.post("/tasks/", json={"title": "Старая задача", "status": TaskStatus.pending})
    task_id = create_response.json()["id"]

    update_data = {"title": "Новая задача", "status": TaskStatus.completed}
    response = await auth_client.patch(f"/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Новая задача"
    assert data["status"] == TaskStatus.completed
    assert data["id"] == task_id

async def test_update_task_not_found(auth_client: AsyncClient):
    """
    Тест на обновление несуществующей задачи.
    """
    response = await auth_client.patch("/tasks/99999", json={"title": "Несуществующая"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."

async def test_update_task_unauthorized(client: AsyncClient, test_user_data: dict, db_engine):
    """
    Тест на попытку обновить задачу другого пользователя.
    """
    # Создаем первого пользователя и его задачу
    await client.post("/register/", json=test_user_data)
    login_data_1 = {"username": test_user_data["username"], "password": test_user_data["password"]}
    token_response_1 = await client.post("/token", data=login_data_1)
    client.headers["Authorization"] = f"Bearer {token_response_1.json()['access_token']}"
    task_response = await client.post("/tasks/", json={"title": "Задача первого пользователя"})
    task_id = task_response.json()["id"]
    client.headers.pop("Authorization")

    # Создаем второго пользователя и авторизуемся им
    test_user_data_2 = {
        "first_name": "Another", "last_name": "User",
        "username": "anotheruser", "password": "anotherpassword"
    }
    await client.post("/register/", json=test_user_data_2)
    login_data_2 = {"username": test_user_data_2["username"], "password": test_user_data_2["password"]}
    token_response_2 = await client.post("/token", data=login_data_2)
    client.headers["Authorization"] = f"Bearer {token_response_2.json()['access_token']}"

    # Второй пользователь пытается обновить задачу первого
    response = await client.patch(f"/tasks/{task_id}", json={"title": "Попытка обновления"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this task."

async def test_delete_task(auth_client: AsyncClient):
    """
    Тест на успешное удаление задачи.
    """
    # Создаем задачу
    create_response = await auth_client.post("/tasks/", json={"title": "Задача для удаления"})
    task_id = create_response.json()["id"]

    response = await auth_client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204 # No Content

    # Проверяем, что задача действительно удалена
    get_response = await auth_client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Task not found."

async def test_delete_task_not_found(auth_client: AsyncClient):
    """
    Тест на удаление несуществующей задачи.
    """
    response = await auth_client.delete("/tasks/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."

async def test_delete_task_unauthorized(client: AsyncClient, test_user_data: dict, db_engine):
    """
    Тест на попытку удалить задачу другого пользователя.
    """
    # Создаем первого пользователя и его задачу
    await client.post("/register/", json=test_user_data)
    login_data_1 = {"username": test_user_data["username"], "password": test_user_data["password"]}
    token_response_1 = await client.post("/token", data=login_data_1)
    client.headers["Authorization"] = f"Bearer {token_response_1.json()['access_token']}"
    task_response = await client.post("/tasks/", json={"title": "Задача первого пользователя"})
    task_id = task_response.json()["id"]
    client.headers.pop("Authorization")

    # Создаем второго пользователя и авторизуемся им
    test_user_data_2 = {
        "first_name": "Another", "last_name": "User",
        "username": "anotheruser", "password": "anotherpassword"
    }
    await client.post("/register/", json=test_user_data_2)
    login_data_2 = {"username": test_user_data_2["username"], "password": test_user_data_2["password"]}
    token_response_2 = await client.post("/token", data=login_data_2)
    client.headers["Authorization"] = f"Bearer {token_response_2.json()['access_token']}"

    # Второй пользователь пытается удалить задачу первого
    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this task."

async def test_complete_task(auth_client: AsyncClient):
    """
    Тест на успешное завершение задачи.
    """
    # Создаем задачу в статусе pending
    create_response = await auth_client.post("/tasks/", json={"title": "Задача для завершения", "status": TaskStatus.pending})
    task_id = create_response.json()["id"]

    # Отправляем запрос на завершение задачи
    response = await auth_client.put(f"/tasks/{task_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["status"] == TaskStatus.completed

    # Проверяем, что статус обновился в базе данных
    get_response = await auth_client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["status"] == TaskStatus.completed

async def test_complete_task_not_found(auth_client: AsyncClient):
    """
    Тест на завершение несуществующей задачи.
    """
    response = await auth_client.put("/tasks/99999/complete")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found."

async def test_complete_task_unauthorized(client: AsyncClient, test_user_data: dict, db_engine):
    """
    Тест на попытку завершить задачу другого пользователя.
    """
    # Создаем первого пользователя и его задачу
    await client.post("/register/", json=test_user_data)
    login_data_1 = {"username": test_user_data["username"], "password": test_user_data["password"]}
    token_response_1 = await client.post("/token", data=login_data_1)
    client.headers["Authorization"] = f"Bearer {token_response_1.json()['access_token']}"
    task_response = await client.post("/tasks/", json={"title": "Задача первого пользователя"})
    task_id = task_response.json()["id"]
    client.headers.pop("Authorization")

    # Создаем второго пользователя и авторизуемся им
    test_user_data_2 = {
        "first_name": "Another", "last_name": "User",
        "username": "anotheruser", "password": "anotherpassword"
    }
    await client.post("/register/", json=test_user_data_2)
    login_data_2 = {"username": test_user_data_2["username"], "password": test_user_data_2["password"]}
    token_response_2 = await client.post("/token", data=login_data_2)
    client.headers["Authorization"] = f"Bearer {token_response_2.json()['access_token']}"

    # Второй пользователь пытается завершить задачу первого
    response = await client.put(f"/tasks/{task_id}/complete")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this task."
