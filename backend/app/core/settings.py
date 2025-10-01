from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 정의 안 된 ENV는 무시 (DATABASE_URL 등)
    )
    KAKAO_REST_API_KEY: str = Field(..., alias="KAKAO_REST_API_KEY")
    MOLIT_SERVICE_KEY: str | None = Field(None, alias="MOLIT_SERVICE_KEY")
    DATABASE_URL: str | None = Field(None, alias="DATABASE_URL")

settings = Settings()
