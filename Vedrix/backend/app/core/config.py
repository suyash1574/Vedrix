from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vedrix"
    APP_VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = "change-me-in-production-use-env-file"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes for access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days for refresh token
    CSRF_SECRET: str = "change-me-csrf-secret-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vedrix"
    # PostgreSQL SSL mode: "disable", "require", "verify-full".
    DB_SSL_MODE: str = "disable"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True
    LANGGRAPH_CHECKPOINT_ENABLED: bool = True
    LANGGRAPH_CHECKPOINT_RETENTION_DAYS: int = 30
    
    # AI API Keys
    GROQ_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    APIFREE_API_KEY: str = ""

    # NVIDIA Object-Oriented Agents (NOOA) migration flag
    NOOA_ENABLED: bool = False
    NOOA_MODEL: str = "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    
    # OpenRouter Base URLs
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    APIFREE_BASE_URL: str = "https://apifreellm.com/api/v1"

    # Email
    EMAIL_BACKEND: str = "console"  # Options: 'console', 'smtp', 'sendgrid'
    SENDGRID_API_KEY: str = ""
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM_NAME: str = "Vedrix AI"
    FRONTEND_URL: str = "http://localhost:5173"

    # Judge0 Code Execution
    JUDGE0_URL: str = "https://judge0-ce.p.rapidapi.com"
    JUDGE0_API_KEY: str = ""

    # Supabase (optional — mirrors data to Postgres when configured)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""   # use the publishable/anon key or service key

    # Redis for caching
    REDIS_URL: str = "redis://localhost:6379/0"

    # Social Login (OAuth2)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # CORS
    ALLOWED_ORIGINS: str = ""  # Comma-separated origins, e.g. "http://localhost:5173,https://vedrix.io"

    # Environment
    ENVIRONMENT: str = "development"  # "development" or "production"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

# PostgreSQL is the only supported application database. Fail fast rather than
# silently creating a local SQLite database that cannot support production scale.
if not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise ValueError(
        "DATABASE_URL must use postgresql+asyncpg://; SQLite is retired for Vedrix."
    )

# Ensure SECRET_KEY is secure if default or empty
if settings.SECRET_KEY == "change-me-in-production-use-env-file" or not settings.SECRET_KEY:
    import secrets
    import logging
    settings.SECRET_KEY = secrets.token_hex(32)
    logging.warning(
        "config.py: SECRET_KEY was not configured or is set to default. "
        "Generating a temporary random hex key for session safety. "
        "Note: This will invalidate existing tokens/sessions if the server restarts."
    )

# Ensure CSRF_SECRET is secure if default or empty
if settings.CSRF_SECRET == "change-me-csrf-secret-in-production" or not settings.CSRF_SECRET:
    import secrets
    import logging
    settings.CSRF_SECRET = secrets.token_hex(32)
    logging.warning(
        "config.py: CSRF_SECRET was not configured or is set to default. "
        "Generating a temporary random hex key for CSRF safety."
    )
