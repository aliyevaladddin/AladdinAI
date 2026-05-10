from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./aladdinai.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    fernet_key: str = ""  # Set in .env — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
