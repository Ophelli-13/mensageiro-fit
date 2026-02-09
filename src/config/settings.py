from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, Field
from typing import Optional

class Settings(BaseSettings):
    # Configurações do Banco de Dados (Individuais)
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    # Configurações do Telegram
    TELEGRAM_BOT_TOKEN: str

    # Configurações do Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    USER_EMAIL: str

    # Monta a URL de conexão automaticamente
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Permite ler de um arquivo .env local se existir, 
    # mas prioriza as variáveis de ambiente do Portainer
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()