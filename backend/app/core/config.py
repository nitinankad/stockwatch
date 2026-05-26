from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "StockWatch API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    # Comma-separated list of allowed origins, or "*" to allow all.
    backend_cors_origins: str = "*"
    database_url: str = ""
    model_dir: str = str(_PROJECT_ROOT / "models")
    inference_timeframe: str = "1Min"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
