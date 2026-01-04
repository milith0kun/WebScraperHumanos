"""
Módulo de Scraping
"""
from app.scraper.engine import PlaywrightScraper, get_scraper, close_scraper
from app.scraper.extractors import DataExtractor, ContactExtractor
from app.scraper.sources import TripAdvisorScraper, GenericWebScraper

__all__ = [
    "PlaywrightScraper",
    "get_scraper",
    "close_scraper",
    "DataExtractor",
    "ContactExtractor",
    "TripAdvisorScraper",
    "GenericWebScraper"
]
