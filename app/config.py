"""
Application configuration via environment variables.
"""

from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://rag:rag@127.0.0.1:5433/enterprise_rag"

    # JWT
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True

    # Celery (Phase 2) — broker/result on separate Redis DBs
    celery_enabled: bool = True
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # MinIO object storage (Phase 2)
    use_minio: bool = True
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "enterprise-rag"
    minio_secure: bool = False

    # Auth — set REQUIRE_AUTH=false for local dev without login
    require_auth: bool = True

    # Phase 3 — quotas, audit, monitoring
    quotas_enabled: bool = True
    prometheus_enabled: bool = True

    # Phase 4 — agentic AI
    agent_enabled: bool = True
    agent_max_iterations: int = 5
    agent_recursion_limit: int = 25
    agent_memory_turns: int = 10
    agent_memory_ttl_seconds: int = 60 * 60 * 24

    @field_validator(
        "require_auth",
        "redis_enabled",
        "celery_enabled",
        "use_minio",
        "minio_secure",
        "quotas_enabled",
        "prometheus_enabled",
        "agent_enabled",
        mode="before",
    )
    @classmethod
    def parse_bool(cls, value):
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes")
        return value

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
