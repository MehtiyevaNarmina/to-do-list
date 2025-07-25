from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()


DATABASE_URL = config("DATABASE_URL", cast=Secret)
# TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)

#Or can be written as:
# from src.config.settings import DATABASE_URL
# engine = create_engine(DATABASE_URL.get_secret_value())
