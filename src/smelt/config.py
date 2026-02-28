from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMELT_", env_file=".env", extra="ignore")

    model: str = "anthropic/claude-sonnet-4-6"
    project: Path = Path(".")
    memory: Path = Path("memory")
    context_files: list[str] = ["ARCHITECTURE.md", "DECISIONS.md"]
    roadmap_db: str = "roadmap.db"


settings = Settings()
