from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "landing"
    docs_api_url: str = "http://docs_dev_app:8000"
    auth_api_url: str = "http://auth:8014"
    log_level: str = "info"


settings = Settings()
