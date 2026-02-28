from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMELT_", env_file=".env", extra="ignore")

    model: str = "anthropic/claude-sonnet-4-6"
    loader_model: str = "anthropic/claude-haiku-4-5-20251001"
    loader_api_key: str | None = None
    loader_retries: int = 3
    project: Path = Path(".")
    memory: Path = Path("memory")
    context_files: list[str] = ["ARCHITECTURE.md", "DECISIONS.md"]
    roadmap_db: str = "roadmap.db"

    @property
    def db_path(self) -> Path:
        return self.memory / self.roadmap_db


settings = Settings()
