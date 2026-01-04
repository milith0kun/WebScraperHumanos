"""
Sistema de Lead Scoring automatizado
Implementa el Pilar III del documento de arquitectura
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from datetime import datetime

from app.models.lead import Lead, LeadPhase, LeadStatus
from app.config import settings


@dataclass
class ScoreComponent:
    """Componente individual del score"""
    name: str
    points: int
    reason: str


class LeadScorer:
    """
    Sistema de Lead Scoring automatizado
    
    Criterios basados en:
    - Información de contacto (WhatsApp > Email)
    - Fase del viaje (Booking > Planning > Dreaming)
    - Keywords de alta intención
    - Destinos de interés
    - Señales negativas (emails desechables, etc.)
    """
    
    # Configuración de puntos
    SCORING_RULES = {
        # Contacto - WhatsApp es prioritario
        "phone_whatsapp": 35,
        "phone_regular": 25,
        "email_valid": 15,
        "email_disposable": -15,
        "username_social": 10,
        
        # Fase del viaje
        "phase_booking": 30,
        "phase_planning": 20,
        "phase_dreaming": 10,
        
        # Keywords de alta intención
        "keyword_price": 10,
        "keyword_book": 10,
        "keyword_availability": 8,
        "keyword_dates": 8,
        
        # Destinos
        "destination_machu_picchu": 10,
        "destination_popular": 5,
        "destination_niche": 8,
        
        # Engagement
        "multiple_interactions": 10,
        "recent_activity": 5,
        
        # Señales negativas
        "suspected_bot": -50,
        "spam_indicators": -20,
        "no_contact_info": -10,
    }
    
    # Destinos premium (alta conversión)
    PREMIUM_DESTINATIONS = [
        "machu picchu", "vinicunca", "salkantay",
        "rainbow mountain", "camino inca", "inca trail"
    ]
    
    # Destinos de nicho (buena conversión)
    NICHE_DESTINATIONS = [
        "choquequirao", "ausangate", "lares trek",
        "humantay", "palccoyo"
    ]
    
    def calculate_score(self, lead: Lead) -> Tuple[int, Dict[str, ScoreComponent]]:
        """
        Calcula el score total de un lead
        Retorna el score y el breakdown detallado
        """
        components: Dict[str, ScoreComponent] = {}
        total = 0
        
        # 1. Evaluar información de contacto
        contact_score = self._score_contact_info(lead)
        for comp in contact_score:
            components[comp.name] = comp
            total += comp.points
        
        # 2. Evaluar fase del viaje
        phase_score = self._score_travel_phase(lead)
        components[phase_score.name] = phase_score
        total += phase_score.points
        
        # 3. Evaluar keywords
        keyword_scores = self._score_keywords(lead)
        for comp in keyword_scores:
            components[comp.name] = comp
            total += comp.points
        
        # 4. Evaluar destinos
        destination_scores = self._score_destinations(lead)
        for comp in destination_scores:
            components[comp.name] = comp
            total += comp.points
        
        # 5. Evaluar engagement
        engagement_scores = self._score_engagement(lead)
        for comp in engagement_scores:
            components[comp.name] = comp
            total += comp.points
        
        # 6. Aplicar penalizaciones
        penalties = self._apply_penalties(lead)
        for comp in penalties:
            components[comp.name] = comp
            total += comp.points
        
        # Normalizar entre 0-100
        final_score = max(0, min(100, total))
        
        logger.debug(f"Lead score calculado: {final_score} ({len(components)} componentes)")
        
        return final_score, {k: vars(v) for k, v in components.items()}
    
    def _score_contact_info(self, lead: Lead) -> List[ScoreComponent]:
        """Evalúa la información de contacto"""
        scores = []
        
        if lead.contact.phone:
            if lead.contact.whatsapp_available:
                scores.append(ScoreComponent(
                    name="whatsapp_available",
                    points=self.SCORING_RULES["phone_whatsapp"],
                    reason="Número de WhatsApp disponible - alta probabilidad de contacto"
                ))
            else:
                scores.append(ScoreComponent(
                    name="phone_available",
                    points=self.SCORING_RULES["phone_regular"],
                    reason="Número de teléfono disponible"
                ))
        
        if lead.contact.email:
            # Verificar si es email desechable
            domain = lead.contact.email.split("@")[1].lower() if "@" in lead.contact.email else ""
            disposable_domains = ["mailinator.com", "tempmail.com", "yopmail.com"]
            
            if domain in disposable_domains:
                scores.append(ScoreComponent(
                    name="disposable_email",
                    points=self.SCORING_RULES["email_disposable"],
                    reason="Email desechable detectado - baja calidad"
                ))
            else:
                scores.append(ScoreComponent(
                    name="valid_email",
                    points=self.SCORING_RULES["email_valid"],
                    reason="Email válido disponible"
                ))
        
        if not lead.contact.phone and not lead.contact.email:
            scores.append(ScoreComponent(
                name="no_contact",
                points=self.SCORING_RULES["no_contact_info"],
                reason="Sin información de contacto directo"
            ))
        
        return scores
    
    def _score_travel_phase(self, lead: Lead) -> ScoreComponent:
        """Evalúa la fase del viaje"""
        phase_scores = {
            LeadPhase.BOOKING: (
                self.SCORING_RULES["phase_booking"],
                "Fase de reserva - alta intención de compra inmediata"
            ),
            LeadPhase.PLANNING: (
                self.SCORING_RULES["phase_planning"],
                "Fase de planificación - interés activo"
            ),
            LeadPhase.DREAMING: (
                self.SCORING_RULES["phase_dreaming"],
                "Fase de sueño - interés inicial"
            ),
        }
        
        points, reason = phase_scores.get(lead.phase, (0, "Fase desconocida"))
        
        return ScoreComponent(
            name=f"phase_{lead.phase.value}",
            points=points,
            reason=reason
        )
    
    def _score_keywords(self, lead: Lead) -> List[ScoreComponent]:
        """Evalúa keywords de alta intención"""
        scores = []
        
        high_intent_keywords = {
            "precio": ("keyword_price", "Búsqueda de precios"),
            "price": ("keyword_price", "Price inquiry"),
            "reservar": ("keyword_book", "Intención de reservar"),
            "book": ("keyword_book", "Booking intent"),
            "disponibilidad": ("keyword_availability", "Consulta de disponibilidad"),
            "availability": ("keyword_availability", "Availability check"),
        }
        
        for keyword in lead.detected_keywords:
            kw_lower = keyword.lower()
            if kw_lower in high_intent_keywords:
                name, reason = high_intent_keywords[kw_lower]
                scores.append(ScoreComponent(
                    name=f"{name}_{kw_lower}",
                    points=self.SCORING_RULES.get(name, 5),
                    reason=reason
                ))
        
        return scores
    
    def _score_destinations(self, lead: Lead) -> List[ScoreComponent]:
        """Evalúa destinos de interés"""
        scores = []
        
        for dest in lead.interested_destinations:
            dest_lower = dest.lower()
            
            if any(p in dest_lower for p in self.PREMIUM_DESTINATIONS):
                scores.append(ScoreComponent(
                    name=f"destination_{dest_lower.replace(' ', '_')}",
                    points=self.SCORING_RULES["destination_machu_picchu"],
                    reason=f"Interés en destino premium: {dest}"
                ))
            elif any(n in dest_lower for n in self.NICHE_DESTINATIONS):
                scores.append(ScoreComponent(
                    name=f"destination_niche_{dest_lower.replace(' ', '_')}",
                    points=self.SCORING_RULES["destination_niche"],
                    reason=f"Interés en destino de nicho: {dest}"
                ))
            else:
                scores.append(ScoreComponent(
                    name=f"destination_{dest_lower.replace(' ', '_')}",
                    points=self.SCORING_RULES["destination_popular"],
                    reason=f"Interés en: {dest}"
                ))
        
        return scores
    
    def _score_engagement(self, lead: Lead) -> List[ScoreComponent]:
        """Evalúa el nivel de engagement"""
        scores = []
        
        # Múltiples interacciones
        if len(lead.interactions) > 3:
            scores.append(ScoreComponent(
                name="multiple_interactions",
                points=self.SCORING_RULES["multiple_interactions"],
                reason=f"Múltiples interacciones detectadas ({len(lead.interactions)})"
            ))
        
        # Actividad reciente
        if lead.last_interaction_at:
            days_since = (datetime.utcnow() - lead.last_interaction_at).days
            if days_since <= 7:
                scores.append(ScoreComponent(
                    name="recent_activity",
                    points=self.SCORING_RULES["recent_activity"],
                    reason="Actividad en los últimos 7 días"
                ))
        
        return scores
    
    def _apply_penalties(self, lead: Lead) -> List[ScoreComponent]:
        """Aplica penalizaciones por señales negativas"""
        penalties = []
        
        if lead.is_bot or lead.bot_probability > 0.7:
            penalties.append(ScoreComponent(
                name="suspected_bot",
                points=self.SCORING_RULES["suspected_bot"],
                reason="Actividad sospechosa de bot detectada"
            ))
        
        return penalties
    
    def get_lead_priority(self, score: int) -> str:
        """Determina la prioridad del lead basada en el score"""
        if score >= settings.hot_lead_threshold:
            return "HOT"
        elif score >= settings.warm_lead_threshold:
            return "WARM"
        else:
            return "COLD"
    
    def should_notify_sales(self, lead: Lead) -> bool:
        """Determina si se debe notificar al equipo de ventas"""
        return (
            lead.score >= settings.hot_lead_threshold and
            lead.phase == LeadPhase.BOOKING and
            lead.contact.whatsapp_available
        )


# Singleton del scorer
_scorer_instance: Optional[LeadScorer] = None


def get_scorer() -> LeadScorer:
    """Obtiene la instancia singleton del scorer"""
    global _scorer_instance
    
    if _scorer_instance is None:
        _scorer_instance = LeadScorer()
    
    return _scorer_instance
