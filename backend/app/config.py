from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    tavily_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./me1ody.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    app_env: str = "local"
    log_level: str = "INFO"
    demo_mode: bool = False
    public_test_token: str = ""
    rate_limit_per_minute: int = 6
    rate_limit_per_day: int = 80

    model_config = {"env_file": ".env"}


settings = Settings()
