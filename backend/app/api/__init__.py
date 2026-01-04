"""
Rutas API
"""
from app.api.leads import router as leads_router
from app.api.scraper import router as scraper_router

__all__ = ["leads_router", "scraper_router"]
