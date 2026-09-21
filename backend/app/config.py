from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    test_database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 1440
    seed_admin_username: str = "admin"
    seed_admin_password: str
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
