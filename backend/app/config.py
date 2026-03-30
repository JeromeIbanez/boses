from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://boses:boses_secret@localhost:5432/boses"
    OPENAI_API_KEY: str = ""

    @property
    def openai_api_key(self) -> str:
        return self.OPENAI_API_KEY.strip()
    UPLOAD_DIR: str = "app/uploads"
    OPENAI_MODEL: str = "gpt-4o"

    @property
    def database_url_psycopg(self) -> str:
        # Render provides postgres:// or postgresql:// — normalize to psycopg v3 scheme
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
