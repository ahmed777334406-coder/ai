from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Beihang SmartFind"
    environment: str = "development"
    database_url: str = "sqlite:///./smartfind.db"
    jwt_secret_key: str = "CHANGE_ME_FOR_LOCAL_DEVELOPMENT_ONLY"
    access_token_expire_minutes: int = 60 * 12
    visitor_session_days: int = 30
    upload_dir: str = "./uploads"
    max_upload_mb: int = 8
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    text_embedding_model: str = "intfloat/multilingual-e5-small"
    image_embedding_model: str = "ViT-B-32"
    ai_device: str = "auto"
    admin_email: str = "admin@example.edu"
    admin_password: str = ""
    enable_local_models: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    model_cache_dir: str = "./.model-cache"
    match_weight_text: float = 0.32
    match_weight_image: float = 0.28
    match_weight_category: float = 0.12
    match_weight_color: float = 0.08
    match_weight_time: float = 0.10
    match_weight_location: float = 0.10
    time_decay_days: float = 14.0

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
