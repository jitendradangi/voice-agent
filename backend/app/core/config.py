from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Voice AI Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str | None = None

    GEMINI_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()