from fastapi import FastAPI
from sqlmodel import SQLModel, Field

#Create the database model
class TodoItem(SQLModel):
    id: None | int = Field(default=None, primary_key=True)
    content: str = Field(index =True, min_length = 3, max_length = 54)
    is_completed: bool = Field(default=False)


app: FastAPI = FastAPI()
async def root():
    return {"message": "Welcome to the To-Do List API"} 
@app.get('/to/do/')
async def read_todos():
    return {'content': 'dummy_todo'}