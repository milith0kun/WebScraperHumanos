"""
Rutas API para gestión de Leads
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from beanie import PydanticObjectId
from loguru import logger

from app.models.lead import Lead, LeadStatus, LeadPhase, ContactInfo, LeadInteraction
from app.services.lead_scorer import get_scorer


router = APIRouter(prefix="/leads", tags=["Leads"])


# Schemas de request/response
class LeadCreate(BaseModel):
    """Schema para crear un lead manualmente"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source_platform: str = "manual"
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    """Schema para actualizar un lead"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None


class LeadResponse(BaseModel):
    """Schema de respuesta de lead"""
    id: str
    name: Optional[str]
    contact: ContactInfo
    phase: LeadPhase
    status: LeadStatus
    score: int
    priority: str
    source_platform: str
    interested_destinations: List[str]
    created_at: datetime
    last_interaction_at: Optional[datetime]


class LeadStats(BaseModel):
    """Estadísticas de leads"""
    total: int
    hot: int
    warm: int
    cold: int
    by_phase: dict
    by_status: dict
    by_platform: dict


@router.get("/", response_model=List[LeadResponse])
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    phase: Optional[LeadPhase] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    platform: Optional[str] = None,
    sort_by: str = Query("score", regex="^(score|created_at|updated_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Obtiene lista de leads con filtros y paginación
    """
    # Construir query
    query = {}
    
    if status:
        query["status"] = status
    if phase:
        query["phase"] = phase
    if min_score is not None:
        query["score"] = {"$gte": min_score}
    if platform:
        query["source_platform"] = platform
    
    # Determinar orden
    sort_direction = -1 if sort_order == "desc" else 1
    
    # Ejecutar query
    leads = await Lead.find(query).sort(
        [(sort_by, sort_direction)]
    ).skip(skip).limit(limit).to_list()
    
    scorer = get_scorer()
    
    return [
        LeadResponse(
            id=str(lead.id),
            name=lead.name,
            contact=lead.contact,
            phase=lead.phase,
            status=lead.status,
            score=lead.score,
            priority=scorer.get_lead_priority(lead.score),
            source_platform=lead.source_platform,
            interested_destinations=lead.interested_destinations,
            created_at=lead.created_at,
            last_interaction_at=lead.last_interaction_at
        )
        for lead in leads
    ]


@router.get("/stats", response_model=LeadStats)
async def get_lead_stats():
    """
    Obtiene estadísticas generales de leads
    """
    # Beanie count syntax
    total = await Lead.find_all().count()
    
    # Por score (HOT/WARM/COLD)
    hot = await Lead.find(Lead.score >= 80).count()
    warm = await Lead.find(Lead.score >= 50, Lead.score < 80).count()
    cold = await Lead.find(Lead.score < 50).count()
    
    # Por fase - simplificado
    by_phase = {}
    for phase in LeadPhase:
        count = await Lead.find(Lead.phase == phase).count()
        by_phase[phase.value] = count
    
    # Por status - simplificado  
    by_status = {}
    for status in LeadStatus:
        count = await Lead.find(Lead.status == status).count()
        by_status[status.value] = count
    
    # Por plataforma - usar aggregation con lista
    by_platform = {}
    try:
        pipeline = [
            {"$group": {"_id": "$source_platform", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        platform_results = await Lead.aggregate(pipeline).to_list()
        by_platform = {r["_id"]: r["count"] for r in platform_results if r["_id"]}
    except Exception:
        by_platform = {}
    
    return LeadStats(
        total=total,
        hot=hot,
        warm=warm,
        cold=cold,
        by_phase=by_phase,
        by_status=by_status,
        by_platform=by_platform
    )


@router.get("/hot", response_model=List[LeadResponse])
async def get_hot_leads(limit: int = Query(10, ge=1, le=50)):
    """
    Obtiene los leads más calientes (prioridad para ventas)
    """
    leads = await Lead.find(
        {"score": {"$gte": 80}}
    ).sort([("score", -1)]).limit(limit).to_list()
    
    scorer = get_scorer()
    
    return [
        LeadResponse(
            id=str(lead.id),
            name=lead.name,
            contact=lead.contact,
            phase=lead.phase,
            status=lead.status,
            score=lead.score,
            priority="HOT",
            source_platform=lead.source_platform,
            interested_destinations=lead.interested_destinations,
            created_at=lead.created_at,
            last_interaction_at=lead.last_interaction_at
        )
        for lead in leads
    ]


@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    """
    Obtiene un lead específico con todos sus detalles
    """
    try:
        lead = await Lead.get(PydanticObjectId(lead_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    scorer = get_scorer()
    
    return {
        "id": str(lead.id),
        "name": lead.name,
        "username": lead.username,
        "profile_url": lead.profile_url,
        "contact": lead.contact.model_dump(),
        "phase": lead.phase.value,
        "status": lead.status.value,
        "score": lead.score,
        "score_breakdown": lead.score_breakdown,
        "priority": scorer.get_lead_priority(lead.score),
        "source_platform": lead.source_platform,
        "source_url": lead.source_url,
        "detected_keywords": lead.detected_keywords,
        "interests": lead.interests,
        "interested_destinations": lead.interested_destinations,
        "interactions": [i.model_dump() for i in lead.interactions],
        "language": lead.language,
        "is_bot": lead.is_bot,
        "bot_probability": lead.bot_probability,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
        "last_interaction_at": lead.last_interaction_at.isoformat() if lead.last_interaction_at else None
    }


@router.post("/", response_model=LeadResponse)
async def create_lead(data: LeadCreate):
    """
    Crea un lead manualmente
    """
    contact = ContactInfo(
        email=data.email,
        phone=data.phone,
        whatsapp_available=bool(data.phone)
    )
    
    lead = Lead(
        name=data.name,
        contact=contact,
        source_platform=data.source_platform,
        notes=[data.notes] if data.notes else []
    )
    
    # Calcular score inicial
    scorer = get_scorer()
    score, breakdown = scorer.calculate_score(lead)
    lead.update_score(score, breakdown)
    
    await lead.save()
    
    logger.info(f"Lead creado manualmente: {lead.id} (score: {lead.score})")
    
    return LeadResponse(
        id=str(lead.id),
        name=lead.name,
        contact=lead.contact,
        phase=lead.phase,
        status=lead.status,
        score=lead.score,
        priority=scorer.get_lead_priority(lead.score),
        source_platform=lead.source_platform,
        interested_destinations=lead.interested_destinations,
        created_at=lead.created_at,
        last_interaction_at=lead.last_interaction_at
    )


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, data: LeadUpdate):
    """
    Actualiza un lead existente
    """
    try:
        lead = await Lead.get(PydanticObjectId(lead_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    # Actualizar campos
    if data.name is not None:
        lead.name = data.name
    if data.email is not None:
        lead.contact.email = data.email
    if data.phone is not None:
        lead.contact.phone = data.phone
        lead.contact.whatsapp_available = True
    if data.status is not None:
        lead.status = data.status
    if data.notes is not None:
        lead.notes.append(data.notes)
    
    lead.updated_at = datetime.utcnow()
    
    # Recalcular score
    scorer = get_scorer()
    score, breakdown = scorer.calculate_score(lead)
    lead.update_score(score, breakdown)
    
    await lead.save()
    
    logger.info(f"Lead actualizado: {lead_id}")
    
    return {"message": "Lead actualizado", "new_score": lead.score}


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str):
    """
    Elimina un lead
    """
    try:
        lead = await Lead.get(PydanticObjectId(lead_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    await lead.delete()
    
    logger.info(f"Lead eliminado: {lead_id}")
    
    return {"message": "Lead eliminado"}


@router.post("/{lead_id}/recalculate-score")
async def recalculate_score(lead_id: str):
    """
    Recalcula el score de un lead
    """
    try:
        lead = await Lead.get(PydanticObjectId(lead_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    scorer = get_scorer()
    old_score = lead.score
    
    score, breakdown = scorer.calculate_score(lead)
    lead.update_score(score, breakdown)
    
    await lead.save()
    
    return {
        "old_score": old_score,
        "new_score": lead.score,
        "breakdown": breakdown,
        "priority": scorer.get_lead_priority(lead.score)
    }
