"""
Modelos de datos para MongoDB
"""
from app.models.lead import Lead, LeadStatus, LeadPhase, ContactInfo
from app.models.scraping_job import ScrapingJob, JobStatus
from app.models.source import Source, SourceType

__all__ = [
    "Lead",
    "LeadStatus", 
    "LeadPhase",
    "ContactInfo",
    "ScrapingJob",
    "JobStatus",
    "Source",
    "SourceType"
]
