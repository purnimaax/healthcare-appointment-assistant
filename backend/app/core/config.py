from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.3

    SQLITE_DB_PATH: str = "./data/app.db"
    CHECKPOINT_DB_PATH: str = "./data/checkpoints.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    KB_DIR: str = "./data/kb"
    UPLOAD_DIR: str = "./data/uploads"

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for p in (
            self.CHROMA_PERSIST_DIR,
            self.KB_DIR,
            self.UPLOAD_DIR,
            Path(self.SQLITE_DB_PATH).parent,
            Path(self.CHECKPOINT_DB_PATH).parent,
        ):
            Path(p).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()
