"""Azure and app configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Loads config from environment / .env file."""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

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
