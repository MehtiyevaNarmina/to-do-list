from fastapi import FastAPI, Depends, HTTPException, status, Query, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Добавил OAuth2PasswordBearer
from sqlmodel import Session, select, desc
from typing import Annotated, Optional, List
from contextlib import asynccontextmanager
from datetime import timedelta

# Import the new functions from create_db
from create_db import create_tables, get_session, get_db_engine
from models import (
    User, UserCreate, UserRead, # Убедитесь, что UserRead определен в models.py
    Task, TaskCreate, TaskUpdate, TaskRead, TaskStatus # Убедитесь, что TaskStatus определен в models.py
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user # Убедитесь, что get_current_user определен в auth.py
from settings import settings

# Global variable to store the engine instance, managed by lifespan
_app_engine = None

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Application startup...')
    global _app_engine
    _app_engine = get_db_engine() # Initialize engine during startup
    create_tables(engine_instance=_app_engine) # Pass the engine instance to create_tables
    print("Application startup complete. Tables created.")
    yield
    print("Application shutdown.")
    # For SQLModel, often not strictly necessary as sessions handle connections
    # but you could add _app_engine.dispose() here for explicit cleanup if needed.

app: FastAPI = FastAPI(
    lifespan=lifespan,
    title="To-Do App API",
    description="A secure API for managing daily tasks with user authentication.",
    version='1.0.0'
)

# --- Authentication Endpoints ---

@app.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register_user(user_create: UserCreate, session: Annotated[Session, Depends(get_session)]):
    """
    Register a new user.
    """
    # Проверяем, существует ли пользователь с таким именем пользователя
    existing_user = session.exec(select(User).where(User.username == user_create.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed_password = get_password_hash(user_create.password)
    user = User(
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        username=user_create.username,
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/token", tags=["Authentication"])
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: Annotated[Session, Depends(get_session)]
):
    """
    Logs in a user and returns a JWT access token.
    """
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Protected Task Endpoints ---

@app.post('/tasks/', response_model=TaskRead, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task_for_user(
    task: TaskCreate, 
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)]
):
    """
    Creates a new task for the authenticated user.
    """
    # Убедитесь, что у вашей модели Task есть поле user_id
    db_task = Task.model_validate(task, update={"user_id": current_user.id})
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

@app.get('/tasks/', response_model=List[TaskRead], tags=["Tasks"])
async def get_my_tasks(
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)],
    offset: int = 0,
    limit: int = Query(default=10, le=100),
    sort_by: Optional[str] = Query(None, description="Sort by 'id', 'title', or 'status'"),
    sort_order: Optional[str] = Query("asc", description="Sort order: 'asc' or 'desc'"),
    status_filter: Optional[TaskStatus] = Query(None, description="Filter tasks by status")
):
    """
    Retrieves all tasks for the authenticated user with optional pagination, sorting, and filtering.
    """
    query = select(Task).where(Task.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Task.status == status_filter)

    if sort_by and sort_by in ['id', 'title', 'status']:
        sort_column = getattr(Task, sort_by)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

    query = query.offset(offset).limit(limit)

    tasks = session.exec(query).all()
    if not tasks:
        # FastAPI по умолчанию возвращает пустой список для List[Model],
        # так что 404 здесь не обязателен, но может быть полезен для UX.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tasks found for this user.")
    
    return tasks

@app.get('/tasks/{task_id}', response_model=TaskRead, tags=["Tasks"])
async def get_single_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)]
):
    """
    Retrieves a single task for the authenticated user by its ID.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    
    # Важная проверка: задача должна принадлежать текущему пользователю
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this task.")

    return task

@app.patch('/tasks/{task_id}', response_model=TaskRead, tags=["Tasks"])
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)]
):
    """
    Updates an existing task. Only the owner can update.
    """
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    
    # Важная проверка: задача должна принадлежать текущему пользователю
    if db_task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task.")

    task_data = task_update.model_dump(exclude_unset=True)
    for key, value in task_data.items():
        setattr(db_task, key, value)
    
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def delete_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)]
):
    """
    Deletes a task. Only the owner can delete.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    
    # Важная проверка: задача должна принадлежать текущему пользователю
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this task.")
    
    session.delete(task)
    session.commit()
    # Для 204 No Content не нужно возвращать тело ответа

# New Endpoint for marking a task as completed (Requirement 4)
@app.put('/tasks/{task_id}/complete', response_model=TaskRead, tags=["Tasks"])
async def complete_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)], # Зависимость от авторизованного пользователя
    session: Annotated[Session, Depends(get_session)]
):
    """
    Marks a task as 'Completed'.
    """
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    # Важная проверка: задача должна принадлежать текущему пользователю
    if db_task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task.")

    db_task.status = TaskStatus.completed # Убедитесь, что TaskStatus.completed существует
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task
