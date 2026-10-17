from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "local"
    DATABASE_URL: str | None = None  # unused for now
    LLM_API_KEY: str | None = None
    LLM_DAILY_CALL_LIMIT: int = 100
    SUPABASE_URL: str | None = None
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    @property
    def supabase_issuer(self) -> str | None:
        if not self.SUPABASE_URL:
            return None
        return self.SUPABASE_URL.rstrip("/") + "/auth/v1"

    @property
    def supabase_jwks_url(self) -> str | None:
        issuer = self.supabase_issuer
        return None if issuer is None else issuer + "/.well-known/jwks.json"


settings = Settings()
