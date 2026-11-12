from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Knowledge Hub"
    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/knowledge_hub"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    OPENAI_API_KEY: str = ""
    jwt_expire_minutes: int = 30 
    
    # 👈 AGREGA ESTAS DOS LÍNEAS EXACTAS AQUÍ:
    jwt_secret: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    @property
    def cors_origin_list(self) -> list[str]:
       return ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()