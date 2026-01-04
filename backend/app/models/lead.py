"""
Modelo de Lead para MongoDB
"""
from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    """Estado del lead en el pipeline"""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class LeadPhase(str, Enum):
    """Fase del viaje del turista"""
    DREAMING = "dreaming"      # Fase de sueño - baja prioridad
    PLANNING = "planning"      # Fase de planificación - media prioridad
    BOOKING = "booking"        # Fase de reserva - ALTA prioridad


class ContactInfo(BaseModel):
    """Información de contacto del lead"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    whatsapp_available: bool = False
    preferred_channel: str = "whatsapp"


class LeadInteraction(BaseModel):
    """Registro de interacción detectada"""
    platform: str
    content: str
    url: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment_score: float = 0.0
    intent_keywords: List[str] = []


class Lead(Document):
    """Modelo principal de Lead"""
    
    # Identificación
    external_id: Optional[str] = None  # ID de la plataforma origen
    
    # Información de contacto
    contact: ContactInfo = Field(default_factory=ContactInfo)
    
    # Información del perfil (si está disponible)
    name: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    location: Optional[str] = None
    
    # Clasificación del lead
    phase: LeadPhase = LeadPhase.DREAMING
    status: LeadStatus = LeadStatus.NEW
    
    # Lead Scoring
    score: int = Indexed(default=0)  # 0-100
    score_breakdown: dict = Field(default_factory=dict)
    
    # Fuente y detección
    source_platform: str = Indexed(default="unknown")
    source_url: Optional[str] = None
    
    # Interacciones detectadas
    interactions: List[LeadInteraction] = []
    
    # Keywords e intereses detectados
    detected_keywords: List[str] = []
    interests: List[str] = []
    
    # Destinos de interés en Cusco
    interested_destinations: List[str] = []
    
    # Fechas estimadas de viaje
    estimated_travel_start: Optional[datetime] = None
    estimated_travel_end: Optional[datetime] = None
    
    # Metadata
    is_bot: bool = False
    bot_probability: float = 0.0
    language: str = "es"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction_at: Optional[datetime] = None
    
    # Notas del equipo de ventas
    notes: List[str] = []
    
    class Settings:
        name = "leads"
        indexes = [
            "score",
            "source_platform",
            "phase",
            "status",
            "created_at"
        ]
    
    def update_score(self, new_score: int, breakdown: dict):
        """Actualiza el score del lead"""
        self.score = max(0, min(100, new_score))
        self.score_breakdown = breakdown
        self.updated_at = datetime.utcnow()
        
        # Actualizar fase basada en score
        if self.score >= 70:
            self.phase = LeadPhase.BOOKING
        elif self.score >= 40:
            self.phase = LeadPhase.PLANNING
        else:
            self.phase = LeadPhase.DREAMING
    
    def add_interaction(self, interaction: LeadInteraction):
        """Agrega una nueva interacción"""
        self.interactions.append(interaction)
        self.last_interaction_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def is_hot_lead(self) -> bool:
        """Verifica si es un lead caliente"""
        return self.score >= 80 and self.phase == LeadPhase.BOOKING
    
    def get_priority_level(self) -> str:
        """Obtiene el nivel de prioridad"""
        if self.score >= 80:
            return "🔥 HOT"
        elif self.score >= 50:
            return "🌡️ WARM"
        else:
            return "❄️ COLD"
