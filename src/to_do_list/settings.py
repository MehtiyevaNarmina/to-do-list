from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, SecretStr
from sqlmodel import create_engine

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: PostgresDsn
    jwt_secret_key: SecretStr 
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

settings = Settings()

connection_string: str = str(settings.database_url).replace("postgresql", "postgresql+psycopg")

engine = create_engine(
    connection_string, 
    pool_recycle=300, 
    pool_size=10, 
    echo=False
)