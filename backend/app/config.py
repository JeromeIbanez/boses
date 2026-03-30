from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://boses:boses_secret@localhost:5432/boses"
    OPENAI_API_KEY: str
    UPLOAD_DIR: str = "app/uploads"
    OPENAI_MODEL: str = "gpt-4o"


settings = Settings()
