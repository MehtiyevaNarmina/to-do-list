from sqlmodel import SQLModel, create_engine, Session
from settings import settings, engine
from models import User, Task  # Import both models

def create_tables():
    """Creates the database tables based on the SQLModel metadata."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency function to get a database session."""
    with Session(engine) as session:
        yield session