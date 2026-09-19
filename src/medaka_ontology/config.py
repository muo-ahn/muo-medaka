"""Runtime configuration, read from the environment or a local .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "data" / "seed"
EXPORT_DIR = REPO_ROOT / "data" / "export"
DOSSIER_DIR = REPO_ROOT / "data" / "dossier"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "medaka-dev-password"
    neo4j_database: str = "neo4j"

    ncbi_api_key: str | None = None
    ncbi_email: str | None = None


def get_settings() -> Settings:
    return Settings()
