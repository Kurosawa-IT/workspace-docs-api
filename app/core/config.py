from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "workspace-docs-api"
    app_env: str = "local"
    log_level: str = "INFO"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "workspace_docs"
    POSTGRES_USER: str = "workspace_docs_user"
    POSTGRES_PASSWORD: str = "workspace_docs_pass"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


settings = Settings()
