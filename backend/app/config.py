from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://boses:boses_secret@localhost:5432/boses"
    OPENAI_API_KEY: str = ""
    UPLOAD_DIR: str = "app/uploads"
    OPENAI_MODEL: str = "gpt-4o"
    SENTRY_DSN: str = ""

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # Email (Resend)
    RESEND_API_KEY: str = ""

    # Supabase Storage (for persistent avatar hosting)
    SUPABASE_URL: str = ""           # e.g. https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY: str = ""   # service_role key (not anon key)
    SUPABASE_AVATARS_BUCKET: str = "avatars"

    # File uploads
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_KEY)

    @property
    def openai_api_key(self) -> str:
        return self.OPENAI_API_KEY.strip()

    @property
    def database_url_psycopg(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        # Enforce SSL for non-local connections
        if self.ENVIRONMENT in ("production", "staging"):
            separator = "&" if "?" in url else "?"
            if "sslmode" not in url:
                url = f"{url}{separator}sslmode=require"
        return url

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def use_secure_cookies(self) -> bool:
        """True for any deployed environment (staging or production) — not local dev."""
        return self.ENVIRONMENT in ("production", "staging")


settings = Settings()

if settings.JWT_SECRET == "change-me-in-production":
    raise RuntimeError(
        "JWT_SECRET is set to the default placeholder. "
        "Set a strong random value in your environment before starting the server."
    )
