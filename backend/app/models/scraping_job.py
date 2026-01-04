"""
Modelo para trabajos de scraping
"""
from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Estado del trabajo de scraping"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapingJob(Document):
    """Modelo para trabajos de scraping"""
    
    # Configuración del job
    source_type: str = "unknown"  # facebook, instagram, tripadvisor, etc.
    target_url: str
    search_query: Optional[str] = None
    
    # Estado - usar string para evitar problemas de serialización
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: int = 0  # 0-100
    
    # Resultados
    leads_found: int = 0
    leads_qualified: int = 0
    errors: List[str] = Field(default_factory=list)
    
    # Configuración de scraping
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Tiempos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Logs
    logs: List[str] = []
    
    class Settings:
        name = "scraping_jobs"
        indexes = [
            "status",
            "source_type",
            "created_at"
        ]
    
    def start(self):
        """Marca el job como iniciado"""
        self.status = "running"
        self.started_at = datetime.utcnow()
    
    def complete(self, leads_found: int, leads_qualified: int):
        """Marca el job como completado"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.leads_found = leads_found
        self.leads_qualified = leads_qualified
        self.progress = 100
    
    def fail(self, error: str):
        """Marca el job como fallido"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.errors.append(error)
    
    def add_log(self, message: str):
        """Agrega un log al job"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
    
    def update_progress(self, progress: int):
        """Actualiza el progreso del job"""
        self.progress = max(0, min(100, progress))
    
    def get_duration(self) -> Optional[float]:
        """Obtiene la duración en segundos"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
