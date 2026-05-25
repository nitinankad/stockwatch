from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StockWatch API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:5173"
    database_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
