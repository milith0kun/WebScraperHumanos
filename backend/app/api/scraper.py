"""
Rutas API para controlar el Scraper
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from loguru import logger
import asyncio

from app.scraper import get_scraper, close_scraper, GenericWebScraper, TripAdvisorScraper
from app.scraper.extractors import DataExtractor
from app.models.scraping_job import ScrapingJob, JobStatus
from app.models.lead import Lead, LeadPhase, ContactInfo, LeadInteraction
from app.services.lead_scorer import get_scorer


router = APIRouter(prefix="/scraper", tags=["Scraper"])


# Schemas
class ScrapeRequest(BaseModel):
    """Request para iniciar scraping"""
    url: str
    source_type: str = "generic"  # generic, tripadvisor, competitor
    config: dict = {}


class QuickExtractRequest(BaseModel):
    """Request para extracción rápida de texto"""
    text: str
    source_url: Optional[str] = None


class ScrapeResponse(BaseModel):
    """Response de scraping"""
    job_id: str
    status: str
    message: str


class JobResponse(BaseModel):
    """Response de estado de job"""
    id: str
    status: str
    progress: int
    leads_found: int
    leads_qualified: int
    logs: List[str]
    errors: List[str] = []
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# Estado del scraper
_scraper_running = False


async def run_scraping_job(job_id: str, url: str, source_type: str, config: dict):
    """
    Ejecuta un trabajo de scraping en background
    """
    global _scraper_running
    
    try:
        _scraper_running = True
        
        # Obtener job
        job = await ScrapingJob.get(job_id)
        if not job:
            return
        
        job.start()
        job.add_log(f"Iniciando scraping de: {url}")
        await job.save()
        
        # Obtener scraper
        scraper = await get_scraper()
        
        # Seleccionar scraper específico
        if source_type == "tripadvisor":
            source_scraper = TripAdvisorScraper(scraper)
        else:
            source_scraper = GenericWebScraper(scraper)
        
        job.add_log(f"Usando scraper: {source_type}")
        job.update_progress(10)
        await job.save()
        
        # Ejecutar scraping
        results = await source_scraper.scrape(url, config)
        
        job.add_log(f"Extracción completada: {len(results)} resultados")
        job.update_progress(50)
        await job.save()
        
        # Procesar resultados y crear leads
        scorer = get_scorer()
        leads_created = 0
        leads_qualified = 0
        
        for i, result in enumerate(results):
            try:
                # Verificar si tiene información de contacto
                contacts = result.get("contacts", {})
                
                if not contacts.get("phones") and not contacts.get("emails"):
                    continue
                
                # Crear ContactInfo
                contact = ContactInfo()
                
                if contacts.get("phones"):
                    phone_data = contacts["phones"][0]
                    contact.phone = phone_data.normalized
                    contact.whatsapp_available = phone_data.is_whatsapp_compatible
                    contact.phone_country_code = phone_data.country_code
                
                if contacts.get("emails"):
                    email_data = contacts["emails"][0]
                    contact.email = email_data.normalized
                
                # Crear Lead
                lead = Lead(
                    contact=contact,
                    username=result.get("author"),
                    profile_url=result.get("author_url"),
                    source_platform=source_type,
                    source_url=result.get("source_url") or url,
                    detected_keywords=result.get("keywords", []),
                    interested_destinations=result.get("destinations", []),
                    language=result.get("language", "es")
                )
                
                # Determinar fase
                phase = result.get("phase", "dreaming")
                lead.phase = LeadPhase(phase) if phase in ["booking", "planning", "dreaming"] else LeadPhase.DREAMING
                
                # Agregar interacción
                if result.get("content"):
                    lead.add_interaction(LeadInteraction(
                        platform=source_type,
                        content=result["content"][:500],
                        url=result.get("thread_url") or url
                    ))
                
                # Calcular score
                score, breakdown = scorer.calculate_score(lead)
                lead.update_score(score, breakdown)
                
                # Guardar lead
                await lead.save()
                leads_created += 1
                
                if score >= 50:
                    leads_qualified += 1
                
                # Actualizar progreso
                progress = 50 + int((i + 1) / len(results) * 45)
                job.update_progress(progress)
                
            except Exception as e:
                job.add_log(f"Error procesando resultado: {e}")
                logger.error(f"Error creando lead: {e}")
        
        # Completar job
        job.complete(leads_created, leads_qualified)
        job.add_log(f"✅ Completado: {leads_created} leads creados, {leads_qualified} calificados")
        await job.save()
        
        logger.success(f"Job {job_id} completado: {leads_created} leads")
        
    except Exception as e:
        logger.error(f"Error en job {job_id}: {e}")
        
        job = await ScrapingJob.get(job_id)
        if job:
            job.fail(str(e))
            await job.save()
    
    finally:
        _scraper_running = False


@router.post("/start", response_model=ScrapeResponse)
async def start_scraping(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Inicia un trabajo de scraping en background
    """
    global _scraper_running
    
    if _scraper_running:
        raise HTTPException(
            status_code=409,
            detail="Ya hay un trabajo de scraping en ejecución"
        )
    
    # Crear job
    job = ScrapingJob(
        source_type=request.source_type,
        target_url=request.url,
        config=request.config
    )
    await job.save()
    
    logger.info(f"Job creado: {job.id} para {request.url}")
    
    # Iniciar en background
    background_tasks.add_task(
        run_scraping_job,
        str(job.id),
        request.url,
        request.source_type,
        request.config
    )
    
    return ScrapeResponse(
        job_id=str(job.id),
        status="pending",
        message="Trabajo de scraping iniciado"
    )


@router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = None,
    limit: int = 10
):
    """
    Obtiene lista de trabajos de scraping
    """
    query = {}
    if status:
        query["status"] = status
    
    jobs = await ScrapingJob.find(query).sort(
        [("created_at", -1)]
    ).limit(limit).to_list()
    
    return [
        JobResponse(
            id=str(job.id),
            status=job.status,
            progress=job.progress,
            leads_found=job.leads_found,
            leads_qualified=job.leads_qualified,
            logs=job.logs[-10:],  # Últimos 10 logs
            errors=job.errors,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Obtiene estado de un trabajo específico
    """
    from beanie import PydanticObjectId
    
    try:
        job = await ScrapingJob.get(PydanticObjectId(job_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    return JobResponse(
        id=str(job.id),
        status=job.status,
        progress=job.progress,
        leads_found=job.leads_found,
        leads_qualified=job.leads_qualified,
        logs=job.logs,
        errors=job.errors,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@router.post("/extract")
async def quick_extract(request: QuickExtractRequest):
    """
    Extrae datos de contacto y keywords de un texto sin hacer scraping
    Útil para testing y procesamiento de datos existentes
    """
    extractor = DataExtractor()
    
    result = extractor.extract_lead_data(
        request.text,
        request.source_url or ""
    )
    
    # Convertir objetos a diccionarios
    contacts = result.get("contacts", {})
    serialized_contacts = {
        "emails": [vars(e) for e in contacts.get("emails", [])],
        "phones": [vars(p) for p in contacts.get("phones", [])],
        "usernames": [vars(u) for u in contacts.get("usernames", [])]
    }
    
    return {
        "contacts": serialized_contacts,
        "phase": result.get("phase"),
        "intent_score": result.get("intent_score"),
        "destinations": result.get("destinations"),
        "keywords": result.get("keywords"),
        "language": result.get("language"),
        "initial_score": result.get("initial_score")
    }


@router.get("/status")
async def get_scraper_status():
    """
    Obtiene el estado actual del scraper
    """
    return {
        "is_running": _scraper_running,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test")
async def test_scraper():
    """
    Prueba rápida del scraper con una página de ejemplo
    """
    try:
        scraper = await get_scraper()
        
        context = await scraper.create_context()
        page = await scraper.new_page(context)
        
        # Probar con una página simple
        test_url = "https://example.com"
        success = await scraper.safe_goto(page, test_url)
        
        if success:
            title = await page.title()
            content = await scraper.get_page_content(page)
            
            await scraper.close_context(context)
            
            return {
                "success": True,
                "message": "Scraper funcionando correctamente",
                "test_url": test_url,
                "page_title": title,
                "content_length": len(content)
            }
        else:
            await scraper.close_context(context)
            return {
                "success": False,
                "message": "No se pudo cargar la página de prueba"
            }
            
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Error en test del scraper: {error_msg}")
        return {
            "success": False,
            "message": error_msg
        }
