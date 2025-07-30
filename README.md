# To-Do List API
- **Run in terminal using comand: docker-compose up --build**

A secure and modular backend RESTful API for managing personal to-do tasks. Built using **FastAPI**, **SQLModel**, **PostgreSQL** and **Docker**, with full support for authentication, task ownership, filtering, and deployment.

---

## Features

### User Authentication
- Register and log in using JWT tokens
- Secure password hashing
---
### Task Management
- Create, read, update, and delete (CRUD) tasks
- Tasks are associated with specific users
- Only task owners can manage their tasks
- Filter, sort, and paginate task lists
- Mark tasks as completed
---
### Security
- JWT-based authentication
- Environment-based configuration via `.env` file
---
### Testing
- Unit Tests: Isolated tests for individual functions and components, mocking external dependencies. 
- Functional (Integration) Tests: End-to-end testing of API endpoints and user flows, interacting with a real (or dedicated test) database.
---
### Containerization
- **Docker Compose:** Orchestration for a multi-container environment, including:
- Separate containers for the main application database (db).
- Application backend (backend).
- A dedicated database for testing (test_db).
- A dedicated service for running tests (tester).
---

## Technologies Used

- **Web framework** – FastAPI 
- **SQLModel** – ORM and Pydantic integration
- **Database** – PostgreSQL
- **Dependency and environment management** – Poetry
- **Authentication** – JWT
- **Testing** – Pytest, TestClient (for functional tests), python-jose (for unit tests)
- **Containerization** - Docker, Docker Compose
---

## Getting Started Locally

### Prerequisites
- Python 3.11+
- Poetry
- Git
- PostgreSQL database
- Docker
