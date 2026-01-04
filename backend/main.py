"""
Cusco Tourism Lead Scraper - API Principal
Sistema de Web Scraping y Automatización de Leads Turísticos
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.database import init_db, close_db
from app.scraper import close_scraper
from app.api import leads_router, scraper_router
import asyncio

# Configurar Policy para Windows antes de cualquier loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# Configurar logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.debug else "INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando Cusco Lead Scraper...")
    
    try:
        await init_db()
        logger.success("✅ Base de datos conectada")
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando aplicación...")
    await close_db()
    await close_scraper()
    logger.info("👋 Aplicación cerrada correctamente")


# Crear aplicación FastAPI
app = FastAPI(
    title="Cusco Tourism Lead Scraper",
    description="""
    ## 🏔️ Sistema de Web Scraping y Automatización de Leads Turísticos para Cusco
    
    Esta API permite:
    - 🔍 **Scraping** de múltiples fuentes (TripAdvisor, redes sociales, competidores)
    - 📊 **Lead Scoring** automatizado basado en intención de compra
    - 📱 **Detección de contactos** (WhatsApp prioritario)
    - 🎯 **Clasificación** por fase del viaje (Dreaming → Planning → Booking)
    
    ### Endpoints principales:
    - `/api/v1/leads` - Gestión de leads
    - `/api/v1/scraper` - Control del scraper
    
    ### Desarrollado siguiendo los 3 pilares:
    1. OSINT + NLP para detección de intención
    2. Scraping resiliente con Playwright
    3. Lead Scoring automatizado
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registrar routers
app.include_router(leads_router, prefix="/api/v1")
app.include_router(scraper_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    """Endpoint de bienvenida"""
    return {
        "message": "🏔️ Cusco Tourism Lead Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check del sistema
    """
    return {
        "status": "healthy",
        "database": "connected",
        "scraper": "ready"
    }


if __name__ == "__main__":
    import uvicorn
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
