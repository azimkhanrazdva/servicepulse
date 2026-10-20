from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
    database_url: str = "postgresql+asyncpg://servicepulse:local-development-only@db/servicepulse"
    simulator_origin: str = ""
    concurrency: int = Field(default=50, ge=1, le=100)
    max_body_bytes: int = Field(default=1048576, ge=1024, le=10485760)
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_sender: str = "servicepulse@example.com"
    smtp_timeout_seconds: float = Field(default=5, ge=0.1, le=10)


settings = Settings()
