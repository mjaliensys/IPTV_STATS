# app/config.py

from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # MySQL connection
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "stream_api"
    db_password: str = "changeme"
    db_name: str = "stream_stats"

    # Connection pool
    db_pool_size: int = 10
    db_pool_overflow: int = 20

    # Aggregation
    aggregation_interval_seconds: int = 60

    # Active sessions persistence (backup to DB every N seconds)
    session_sync_interval_seconds: int = 30

    @property
    def database_url(self) -> str:
        password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        env_prefix = "STREAM_"


settings = Settings()