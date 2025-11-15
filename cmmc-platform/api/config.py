"""
Configuration Management
Loads settings from environment variables with fallback defaults
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = Field(
        default="postgresql://cmmc_user:cmmc_password@localhost:5432/cmmc_platform",
        alias="DATABASE_URL"
    )
    database_pool_min_size: int = Field(default=5, alias="DATABASE_POOL_MIN_SIZE")
    database_pool_max_size: int = Field(default=20, alias="DATABASE_POOL_MAX_SIZE")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=True, alias="RELOAD")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # JWT
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # File Storage
    storage_path: str = Field(default="/var/cmmc/evidence", alias="STORAGE_PATH")
    max_upload_size: int = Field(default=104857600, alias="MAX_UPLOAD_SIZE")  # 100MB

    # AI/ML
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = Field(
        default="text-embedding-ada-002",
        alias="EMBEDDING_MODEL"
    )
    ai_model: str = Field(default="gpt-4", alias="AI_MODEL")
    vector_dimensions: int = Field(default=3072, alias="VECTOR_DIMENSIONS")

    # AWS (Optional)
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_s3_bucket: str = Field(default="", alias="AWS_S3_BUCKET")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    # Email (Optional)
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    email_from: str = Field(default="", alias="EMAIL_FROM")

    # Application
    app_name: str = Field(default="CMMC Compliance Platform", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100, alias="RATE_LIMIT_PER_MINUTE")

    # Session
    session_secret_key: str = Field(
        default="dev-session-secret",
        alias="SESSION_SECRET_KEY"
    )

    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret is secure in production"""
        environment = values.get('environment', 'development')

        # Allow dev secret in development mode only
        if environment == 'production':
            if v == "dev-secret-key-change-in-production":
                raise ValueError(
                    "CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be changed in production! "
                    "Generate a secure secret with: openssl rand -hex 32"
                )
            if len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters for production use"
                )

        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create global settings instance
settings = Settings()
