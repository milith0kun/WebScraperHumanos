"""
Configuración central de la aplicación
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""
    
    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="URI de conexión a MongoDB Atlas"
    )
    mongodb_db_name: str = Field(
        default="cusco_leads",
        description="Nombre de la base de datos"
    )
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=True)
    
    # NLP Settings
    nlp_model: str = Field(
        default="dccuchile/bert-base-spanish-wwm-cased",
        description="Modelo BETO para español"
    )
    use_gpu: bool = Field(default=False)
    
    # Scraping Settings
    headless_mode: bool = Field(default=True)
    max_concurrent_scrapers: int = Field(default=3)
    request_delay_ms: int = Field(default=2000)
    
    # OpenAI (opcional)
    openai_api_key: Optional[str] = Field(default=None)
    
    # Lead Scoring Thresholds
    hot_lead_threshold: int = Field(default=80)
    warm_lead_threshold: int = Field(default=50)
    cold_lead_threshold: int = Field(default=20)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Singleton para obtener la configuración"""
    return Settings()


settings = get_settings()
