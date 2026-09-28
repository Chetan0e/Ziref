from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "Ziref"
    APP_ENV: str = "development"
    DEBUG: bool = True
    BASE_DOMAIN: str = "localhost:8080"
    API_PUBLIC_URL: str = "http://localhost:8000"
    DASHBOARD_PUBLIC_URL: str = "http://localhost:3000"

    # Canonical deployment URL base — the SINGLE source of truth for all deployment URLs.
    # In development: http://localhost:8000/sites
    # In production:  https://ziref.app/sites  (or https://{slug}.ziref.app with empty prefix)
    PUBLIC_SITE_BASE_URL: str = "http://localhost:8000/sites"
    # Domain suffix for subdomain-style routing in production (e.g. .ziref.app)
    PUBLIC_DOMAIN_SUFFIX: str = ""

    # Databases
    MONGODB_URI: str = "mongodb://localhost:27017/ziref"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET: str = "ziref_super_secret_jwt_key_replace_in_production_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ENCRYPTION_KEY: str = "D7p04p0RzD5zJ1oWwVbM6tF3mGk4q9S2l7U8xP0nL1c="

    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_PATH: str = str(Path(__file__).resolve().parents[3] / "storage")

    # Build Limits & Constraints
    BUILD_CPU_LIMIT: float = 1.0
    BUILD_MEMORY_LIMIT: str = "1024m"
    BUILD_TIMEOUT_SECONDS: int = 300
    WORKER_CONCURRENCY: int = 4
    SANDBOX_IMAGE: str = "node:20-alpine"

    # Upload Security
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_EXTRACTED_SIZE_BYTES: int = 250 * 1024 * 1024  # 250 MB
    MAX_ARCHIVE_FILE_COUNT: int = 10000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure local storage path exists
os.makedirs(settings.STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "uploads"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "artifacts"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "deployments"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "mobile"), exist_ok=True)
