from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Knowledge Hub"
    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/knowledge_hub"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    OPENAI_API_KEY: str = ""
    embedding_dim: int = 1536
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    jwt_expire_minutes: int = 30

    jwt_secret: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    @property
    def openai_api_key(self) -> str:
        return self.OPENAI_API_KEY

    @property
    def cors_origin_list(self) -> list[str]:
       return ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()