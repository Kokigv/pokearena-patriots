"""Configuración de la aplicación, leída de variables de entorno."""

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _csv(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pokearena"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me-at-least-32-bytes!!"
    jwt_issuer: str = "pokearena"
    access_token_minutes: int = 15
    admin_subjects: frozenset[str] = field(default_factory=frozenset)
    storage_backend: str = "local"  # "local" o "s3"
    storage_local_path: str = "./data/images"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "pokearena-images"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    idempotency_ttl_seconds: int = 86_400
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            app_env=env.get("APP_ENV", cls.app_env),
            database_url=env.get("DATABASE_URL", cls.database_url),
            redis_url=env.get("REDIS_URL", cls.redis_url),
            jwt_secret=env.get("JWT_SECRET", cls.jwt_secret),
            access_token_minutes=int(env.get("ACCESS_TOKEN_MINUTES", cls.access_token_minutes)),
            admin_subjects=_csv(env.get("ADMIN_SUBJECTS", "")),
            storage_backend=env.get("STORAGE_BACKEND", cls.storage_backend),
            storage_local_path=env.get("STORAGE_LOCAL_PATH", cls.storage_local_path),
            s3_endpoint_url=env.get("S3_ENDPOINT_URL") or None,
            s3_bucket=env.get("S3_BUCKET", cls.s3_bucket),
            s3_access_key=env.get("S3_ACCESS_KEY") or None,
            s3_secret_key=env.get("S3_SECRET_KEY") or None,
            cors_origins=tuple(_csv(env.get("CORS_ORIGINS", "http://localhost:5173"))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
