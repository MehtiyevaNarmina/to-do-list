
from sqlmodel import SQLModel, Session, create_engine
from src.to_do_list.settings import settings 
from src.to_do_list.models import User, Task 


_engine = None 

def get_db_engine():
    
    global _engine
    if _engine is None:
        connection_string = str(settings.database_url).replace("postgresql", "postgresql+psycopg")
        _engine = create_engine(connection_string, echo=True)
    return _engine

def create_tables(engine_instance=None): 
    
    if engine_instance is None:
        engine_instance = get_db_engine()
    print('Creating Tables...')
    SQLModel.metadata.create_all(engine_instance)
    print("Tables Created.")

def get_session(engine_instance=None): 

    if engine_instance is None:
        engine_instance = get_db_engine()
    with Session(engine_instance) as session:
        yield session