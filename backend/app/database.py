"""
Conexión y configuración de MongoDB Atlas
"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger
from typing import Optional

from app.config import settings
from app.models.lead import Lead
from app.models.scraping_job import ScrapingJob
from app.models.source import Source


class Database:
    """Gestor de conexión a MongoDB"""
    
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect(cls):
        """Establece conexión con MongoDB Atlas"""
        try:
            logger.info(f"Conectando a MongoDB: {settings.mongodb_db_name}")
            
            cls.client = AsyncIOMotorClient(settings.mongodb_uri)
            
            # Inicializar Beanie con los modelos de documento
            await init_beanie(
                database=cls.client[settings.mongodb_db_name],
                document_models=[
                    Lead,
                    ScrapingJob,
                    Source
                ]
            )
            
            # Verificar conexión
            await cls.client.admin.command('ping')
            logger.success("✅ Conexión a MongoDB establecida correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """Cierra la conexión con MongoDB"""
        if cls.client:
            cls.client.close()
            logger.info("Conexión a MongoDB cerrada")
    
    @classmethod
    def get_database(cls):
        """Obtiene la instancia de la base de datos"""
        return cls.client[settings.mongodb_db_name]


async def init_db():
    """Inicializa la base de datos"""
    await Database.connect()


async def close_db():
    """Cierra la conexión a la base de datos"""
    await Database.disconnect()
