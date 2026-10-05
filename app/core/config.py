from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "local"
    DATABASE_URL: str | None = None  # unused for now
    LLM_API_KEY: str | None = None
    LLM_DAILY_CALL_LIMIT: int = 100


settings = Settings()
