"""Application configuration using environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = "test-key-not-set"  # Default for testing
    openai_base_url: str = "https://api.openai.com"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # Budget Configuration
    default_budget: float = 10.00  # USD
    
    # Operation Mode
    strict_mode: bool = False  # Reject requests without session_id
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()

