# from sqlmodel import SQLModel, Session
# from settings import engine
# from models import User, Task

# def create_tables(db_engine=engine):
#     """Creates the database tables based on the SQLModel metadata."""
#     SQLModel.metadata.create_all(db_engine)

# def get_session(db_engine=engine):
#     """Dependency function to get a database session."""
#     with Session(db_engine) as session:
#         yield session


# database/create_db.py
from sqlmodel import SQLModel, Session, create_engine
from settings import settings # Make sure this import is correct
from models import User, Task # Ensure all your models are imported here


_engine = None # Internal variable to store the engine instance

def get_db_engine():
    """Returns the database engine, initializing it if not already done."""
    global _engine
    if _engine is None:
        # Use settings.database_url directly here
        _engine = create_engine(str(settings.database_url), echo=True)
    return _engine

def create_tables(engine_instance=None): # Accept engine as parameter
    """Creates the database tables based on the SQLModel metadata."""
    # If no engine instance is provided, get it from the global helper
    if engine_instance is None:
        engine_instance = get_db_engine()
    print('Creating Tables...')
    SQLModel.metadata.create_all(engine_instance)
    print("Tables Created.")

def get_session(engine_instance=None): # Accept engine as parameter
    """Dependency function to get a database session."""
    # If no engine instance is provided, get it from the global helper
    if engine_instance is None:
        engine_instance = get_db_engine()
    with Session(engine_instance) as session:
        yield session