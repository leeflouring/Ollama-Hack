from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings


class DatabaseEngine(StrEnum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class LogLevels(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Env(StrEnum):
    DEV = "dev"
    PROD = "prod"


class AppConfig(BaseSettings):
    env: Env = Env.PROD
    log_level: LogLevels = LogLevels.INFO
    secret_key: str = "0llama_H4ck"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


class DatabaseConfig(BaseSettings):
    engine: DatabaseEngine = DatabaseEngine.MYSQL
    host: str = "localhost"
    port: int | None = None
    username: str = "ollama_hack"
    password: str = "0llama_H4ck"
    db: str = "ollama_hack"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800


class Config(BaseSettings):
    database: DatabaseConfig = DatabaseConfig()
    app: AppConfig = AppConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


@lru_cache
def get_config() -> Config:
    """
    Get the config object.
    """
    return Config()
