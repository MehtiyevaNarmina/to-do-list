from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel


class UserBase(SQLModel):
    first_name: str = Field(min_length=2, max_length=50)
    last_name: Optional[str] = Field(default=None, max_length=50)
    username: str = Field(min_length=3, max_length=50, unique=True, index=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    tasks: List["Task"] = Relationship(back_populates="owner")

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserRead(UserBase):
    id: int



class TaskStatus(str, Enum):
    new = "New"
    in_progress = "In Progress"
    completed = "Completed"

class TaskBase(SQLModel):
    title: str = Field(min_length=3, max_length=54, index=True)
    description: Optional[str] = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.new)

class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
 
    user_id: int = Field(foreign_key="user.id", index=True)
    
   
    owner: User = Relationship(back_populates="tasks")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskRead(TaskBase):
    id: int
    user_id: int