"""Azure and app configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Loads config from environment / .env file."""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = ""
    azure_openai_api_version: str = "2025-04-14"

    # Telegram (for future webhook integration)
    telegram_bot_token: str = ""
    webhook_secret: str = ""
    webhook_url: str = ""

    # Cafe owner — Telegram user ID allowed to run admin commands
    owner_telegram_id: str = ""

    # App
    app_port: int = 8000
    app_host: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
