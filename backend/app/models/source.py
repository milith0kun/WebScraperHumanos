"""
Modelo para fuentes de datos configurables
"""
from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Tipos de fuentes de datos"""
    FACEBOOK_GROUP = "facebook_group"
    INSTAGRAM_HASHTAG = "instagram_hashtag"
    INSTAGRAM_PROFILE = "instagram_profile"
    TRIPADVISOR_FORUM = "tripadvisor_forum"
    TIKTOK_HASHTAG = "tiktok_hashtag"
    COMPETITOR_WEBSITE = "competitor_website"
    CUSTOM = "custom"


class Source(Document):
    """Configuración de fuente de datos para scraping"""
    
    # Identificación
    name: str = Indexed()
    source_type: SourceType
    
    # URL y configuración
    url: str
    selectors: Dict[str, str] = Field(default_factory=dict)  # CSS/XPath selectors
    
    # Configuración de extracción
    extract_emails: bool = True
    extract_phones: bool = True
    extract_usernames: bool = True
    
    # Keywords a buscar
    target_keywords: List[str] = []
    negative_keywords: List[str] = []  # Keywords que indican bajo interés
    
    # Rate limiting
    requests_per_minute: int = 10
    delay_between_requests_ms: int = 2000
    
    # Estado
    is_active: bool = True
    last_scraped_at: Optional[datetime] = None
    total_leads_extracted: int = 0
    
    # Programación
    scrape_frequency_hours: int = 24  # Cada cuántas horas hacer scraping
    
    # Notas
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "sources"
        indexes = [
            "name",
            "source_type",
            "is_active"
        ]
    
    def should_scrape(self) -> bool:
        """Determina si es momento de hacer scraping"""
        if not self.is_active:
            return False
        
        if self.last_scraped_at is None:
            return True
        
        hours_since_last = (datetime.utcnow() - self.last_scraped_at).total_seconds() / 3600
        return hours_since_last >= self.scrape_frequency_hours
    
    def mark_scraped(self, leads_found: int):
        """Marca la fuente como scrapeada"""
        self.last_scraped_at = datetime.utcnow()
        self.total_leads_extracted += leads_found
        self.updated_at = datetime.utcnow()
