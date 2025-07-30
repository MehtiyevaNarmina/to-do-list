# tests/functional/test_tasks_flow.py
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.to_do_list.models import Task, TaskStatus, User
from src.to_do_list.auth import get_password_hash


def test_create_task(client: TestClient, auth_headers: dict, test_user: User):
    task_data = {"title": "Test Task", "description": "A task for testing"}
    response = client.post("/tasks/", json=task_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["user_id"] == test_user.id

def test_get_my_tasks(client: TestClient, auth_headers: dict, session: Session, test_user: User):
    session.add(Task(title="Task 1", user_id=test_user.id))
    session.add(Task(title="Task 2", user_id=test_user.id))
    session.commit()

    response = client.get("/tasks/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_my_tasks_empty(client: TestClient, auth_headers: dict):
    response = client.get("/tasks/", headers=auth_headers)
    assert response.status_code == 404

def test_get_single_task(client: TestClient, auth_headers: dict, session: Session, test_user: User):
    task = Task(title="My Task", user_id=test_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.get(f"/tasks/{task.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "My Task"

def test_update_task(client: TestClient, auth_headers: dict, session: Session, test_user: User):
    task = Task(title="Original Title", user_id=test_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.patch(
        f"/tasks/{task.id}",
        json={"title": "Updated Title", "status": TaskStatus.completed},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == TaskStatus.completed

def test_delete_task(client: TestClient, auth_headers: dict, session: Session, test_user: User):
    task = Task(title="To Delete", user_id=test_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.delete(f"/tasks/{task.id}", headers=auth_headers)
    assert response.status_code == 204

    db_task = session.get(Task, task.id)
    assert db_task is None

def test_complete_task(client: TestClient, auth_headers: dict, session: Session, test_user: User):
    task = Task(title="To Complete", status=TaskStatus.new, user_id=test_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.put(f"/tasks/{task.id}/complete", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == TaskStatus.completed


def test_get_my_tasks_with_status_filter(client: TestClient, auth_headers: dict, session: Session, test_user: User):

    session.add(Task(title="Task New", status=TaskStatus.new, user_id=test_user.id))
    session.add(Task(title="Task In Progress", status=TaskStatus.in_progress, user_id=test_user.id))
    session.add(Task(title="Task Completed", status=TaskStatus.completed, user_id=test_user.id))
    session.commit()

    response = client.get("/tasks/", headers=auth_headers, params={"status_filter": "Completed"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task Completed"
    assert tasks[0]["status"] == TaskStatus.completed

def test_get_my_tasks_with_sorting(client: TestClient, auth_headers: dict, session: Session, test_user: User):

    session.add(Task(title="Task C", user_id=test_user.id))
    session.add(Task(title="Task A", user_id=test_user.id))
    session.add(Task(title="Task B", user_id=test_user.id))
    session.commit()

    response = client.get("/tasks/", headers=auth_headers, params={"sort_by": "title", "sort_order": "asc"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3
    assert tasks[0]["title"] == "Task A"
    assert tasks[1]["title"] == "Task B"
    assert tasks[2]["title"] == "Task C"


def test_get_tasks_unauthenticated(client: TestClient):

    response = client.get("/tasks/")
    assert response.status_code == 401

def test_access_another_users_task(client: TestClient, session: Session, auth_headers: dict):

    other_user = User(username="otheruser", hashed_password=get_password_hash("password"))
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    task = Task(title="Other's Task", user_id=other_user.id)
    session.add(task)
    session.commit()
    session.refresh(task)

    # test_user (from auth_headers) try to get access to tasks of another user(other_user)
    response_get = client.get(f"/tasks/{task.id}", headers=auth_headers)
    assert response_get.status_code == 403


def test_task_full_lifecycle(client: TestClient):
    user_data = {"username": "e2e_user", "password": "e2e_password", "first_name": "E2E", "last_name": "Test"}
    reg_response = client.post("/register/", json=user_data)
    assert reg_response.status_code == 201

    login_data = {"username": user_data["username"], "password": user_data["password"]}
    token_response = client.post("/token", data=login_data)
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    task_data = {"title": "Lifecycle Task", "description": "Full test"}
    create_response = client.post("/tasks/", json=task_data, headers=headers)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    get_list_response = client.get("/tasks/", headers=headers)
    assert get_list_response.status_code == 200
    assert len(get_list_response.json()) == 1

    update_data = {"title": "Updated Lifecycle Task", "status": "In Progress"}
    update_response = client.patch(f"/tasks/{task_id}", json=update_data, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["title"] == update_data["title"]

    delete_response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete_response.status_code == 204

    get_single_response = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_single_response.status_code == 404 