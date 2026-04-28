"""Pydantic settings for baseball prediction warehouse.

Provides centralized configuration management with environment variable
support, validation, and sensible defaults.

Example:
    >>> from baseball.core.settings import settings
    >>> print(settings.database_url)
    postgresql://localhost:5432/retrosheet
    >>> print(settings.mlb_stats_api_timeout)
    30
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="PG",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="retrosheet", description="Database name")
    user: str | None = Field(default=None, description="Database user")
    password: str | None = Field(default=None, description="Database password")
    url: str | None = Field(default=None, description="Full DATABASE_URL override")

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        if self.url:
            return self.url
        user_part = f"{self.user}:" if self.user else ""
        password_part = f"{self.password}@" if self.password else ""
        return f"postgresql://{user_part}{password_part}{self.host}:{self.port}/{self.database}"


class MLBStatsAPISettings(BaseSettings):
    """MLB Stats API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MLB_",
        extra="ignore",
    )

    base_url: str = Field(
        default="https://statsapi.mlb.com/api/v1",
        description="MLB Stats API base URL",
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retry attempts")
    rate_limit_per_minute: int = Field(
        default=100,
        description="API rate limit per minute",
    )


class DataPathsSettings(BaseSettings):
    """File system paths for data storage."""

    model_config = SettingsConfigDict(
        env_prefix="DATA_",
        extra="ignore",
    )

    root: Path = Field(
        default=Path("./data"),
        description="Root data directory",
    )
    raw: Path = Field(
        default=Path("./data/raw"),
        description="Raw ingested data",
    )
    processed: Path = Field(
        default=Path("./data/processed"),
        description="Processed/transformed data",
    )
    models: Path = Field(
        default=Path("./data/models"),
        description="Trained model artifacts",
    )
    cache: Path = Field(
        default=Path("./data/cache"),
        description="Temporary cache files",
    )

    @field_validator("root", "raw", "processed", "models", "cache", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Convert string to Path and create if needed."""
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format",
    )
    file: Path | None = Field(
        default=None,
        description="Optional log file path",
    )


class ModelSettings(BaseSettings):
    """Model training and inference settings."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        extra="ignore",
    )

    default_model_dir: Path = Field(
        default=Path("./data/models"),
        description="Default directory for model storage",
    )
    training_test_size: float = Field(
        default=0.2,
        description="Fraction of data for test split",
    )
    training_random_state: int = Field(
        default=42,
        description="Random seed for reproducibility",
    )


class Settings(BaseSettings):
    """Main application settings container.

    Aggregates all settings subsections and provides global configuration.
    Environment variables override defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-settings
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    mlb: MLBStatsAPISettings = Field(default_factory=MLBStatsAPISettings)
    paths: DataPathsSettings = Field(default_factory=DataPathsSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)

    # Global settings
    debug: bool = Field(default=False, description="Enable debug mode")
    env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Runtime environment",
    )

    @property
    def database_url(self) -> str:
        """Convenience accessor for database URL."""
        return self.db.database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache to avoid re-parsing environment on every call.

    Returns:
        Settings: Configured settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()


__all__ = [
    "Settings",
    "DatabaseSettings",
    "MLBStatsAPISettings",
    "DataPathsSettings",
    "LoggingSettings",
    "ModelSettings",
    "get_settings",
    "settings",
]
