"""
Extractores de datos usando Regex y patrones
Implementa los patrones del Pilar II del documento
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import phonenumbers
from email_validator import validate_email, EmailNotValidError


@dataclass
class ExtractedContact:
    """Contacto extraído"""
    type: str  # email, phone, username
    value: str
    normalized: str
    country_code: Optional[str] = None
    is_whatsapp_compatible: bool = False
    confidence: float = 1.0


class ContactExtractor:
    """
    Extractor de información de contacto usando Regex
    Basado en los patrones del documento de arquitectura
    """
    
    # Patrones Regex del documento
    PATTERNS = {
        # Emails - Patrón mejorado
        "email": re.compile(
            r'[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}',
            re.IGNORECASE
        ),
        
        # Teléfonos Perú - Móviles (+51 9XX XXX XXX)
        "phone_peru": re.compile(
            r'(?:\+51\s?)?9\d{2}[-.\s]?\d{3}[-.\s]?\d{3}',
            re.IGNORECASE
        ),
        
        # Formato Internacional genérico
        "phone_international": re.compile(
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}',
            re.IGNORECASE
        ),
        
        # WhatsApp links
        "whatsapp_link": re.compile(
            r'wa\.me/(\d+)|api\.whatsapp\.com/send\?phone=(\d+)',
            re.IGNORECASE
        ),
        
        # Usernames de redes sociales
        "instagram_username": re.compile(
            r'@([a-zA-Z0-9._]{1,30})',
            re.IGNORECASE
        ),
    }
    
    # Emails desechables a filtrar (scoring negativo)
    DISPOSABLE_EMAIL_DOMAINS = [
        "mailinator.com", "tempmail.com", "throwaway.email",
        "guerrillamail.com", "10minutemail.com", "yopmail.com",
        "trashmail.com", "fakeinbox.com"
    ]
    
    def extract_emails(self, text: str) -> List[ExtractedContact]:
        """Extrae y valida emails del texto"""
        emails = []
        matches = self.PATTERNS["email"].findall(text)
        
        for match in matches:
            try:
                # Validar email
                valid = validate_email(match, check_deliverability=False)
                normalized = valid.normalized
                
                # Detectar emails desechables
                domain = normalized.split("@")[1].lower()
                is_disposable = domain in self.DISPOSABLE_EMAIL_DOMAINS
                
                confidence = 0.3 if is_disposable else 1.0
                
                emails.append(ExtractedContact(
                    type="email",
                    value=match,
                    normalized=normalized,
                    confidence=confidence
                ))
                
                if is_disposable:
                    logger.warning(f"⚠️ Email desechable detectado: {normalized}")
                    
            except EmailNotValidError:
                logger.debug(f"Email inválido ignorado: {match}")
        
        return emails
    
    def extract_phones(self, text: str) -> List[ExtractedContact]:
        """Extrae y valida números de teléfono"""
        phones = []
        seen = set()
        
        # Buscar teléfonos peruanos primero (alta prioridad)
        peru_matches = self.PATTERNS["phone_peru"].findall(text)
        for match in peru_matches:
            normalized = self._normalize_phone(match, "PE")
            if normalized and normalized not in seen:
                seen.add(normalized)
                phones.append(ExtractedContact(
                    type="phone",
                    value=match,
                    normalized=normalized,
                    country_code="PE",
                    is_whatsapp_compatible=True,  # Móviles peruanos usan WhatsApp
                    confidence=1.0
                ))
        
        # Buscar teléfonos internacionales
        intl_matches = self.PATTERNS["phone_international"].findall(text)
        for match in intl_matches:
            normalized = self._normalize_phone(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                
                # Intentar determinar país
                country = self._detect_country(normalized)
                
                phones.append(ExtractedContact(
                    type="phone",
                    value=match,
                    normalized=normalized,
                    country_code=country,
                    is_whatsapp_compatible=True,
                    confidence=0.9
                ))
        
        # Buscar links de WhatsApp
        wa_matches = self.PATTERNS["whatsapp_link"].findall(text)
        for match in wa_matches:
            number = match[0] or match[1]  # Una de las dos capturas
            if number and number not in seen:
                seen.add(number)
                phones.append(ExtractedContact(
                    type="phone",
                    value=f"wa.me/{number}",
                    normalized=f"+{number}",
                    is_whatsapp_compatible=True,
                    confidence=1.0
                ))
        
        return phones
    
    def extract_usernames(self, text: str) -> List[ExtractedContact]:
        """Extrae usernames de redes sociales"""
        usernames = []
        seen = set()
        
        matches = self.PATTERNS["instagram_username"].findall(text)
        for match in matches:
            if match.lower() not in seen and len(match) > 2:
                seen.add(match.lower())
                usernames.append(ExtractedContact(
                    type="username",
                    value=f"@{match}",
                    normalized=match.lower(),
                    confidence=0.8
                ))
        
        return usernames
    
    def extract_all(self, text: str) -> Dict[str, List[ExtractedContact]]:
        """Extrae todos los tipos de contacto"""
        return {
            "emails": self.extract_emails(text),
            "phones": self.extract_phones(text),
            "usernames": self.extract_usernames(text)
        }
    
    def _normalize_phone(self, phone: str, default_country: str = None) -> Optional[str]:
        """Normaliza un número de teléfono al formato E.164"""
        try:
            # Limpiar caracteres no numéricos excepto +
            cleaned = re.sub(r'[^\d+]', '', phone)
            
            # Parsear con phonenumbers
            parsed = phonenumbers.parse(cleaned, default_country)
            
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, 
                    phonenumbers.PhoneNumberFormat.E164
                )
        except Exception:
            pass
        
        return None
    
    def _detect_country(self, phone: str) -> Optional[str]:
        """Detecta el país de un número de teléfono"""
        try:
            parsed = phonenumbers.parse(phone)
            return phonenumbers.region_code_for_number(parsed)
        except Exception:
            return None


class DataExtractor:
    """
    Extractor de datos estructurados de páginas web
    """
    
    # Keywords de alta intención (Fase Booking)
    HIGH_INTENT_KEYWORDS = [
        "precio", "price", "costo", "cost",
        "reservar", "book", "booking", "reserva",
        "disponibilidad", "availability", "available",
        "cuánto cuesta", "how much",
        "entradas", "tickets", "boletos",
        "agosto", "septiembre", "julio",  # Meses de alta temporada
        "próximo mes", "next month",
        "este año", "this year",
    ]
    
    # Keywords de planificación (Fase Planning)
    PLANNING_KEYWORDS = [
        "itinerario", "itinerary",
        "cuántos días", "how many days",
        "mejor época", "best time",
        "clima", "weather",
        "salkantay", "camino inca", "inca trail",
        "vs", "o mejor", "or better",
        "recomendaciones", "recommendations",
        "qué llevar", "what to bring",
    ]
    
    # Keywords de sueño (Fase Dreaming)
    DREAMING_KEYWORDS = [
        "fotos", "photos", "pictures",
        "hermoso", "beautiful", "amazing",
        "increíble", "incredible",
        "algún día", "someday", "one day",
        "sueño con", "dream of",
        "bucket list",
    ]
    
    # Destinos de Cusco
    CUSCO_DESTINATIONS = [
        "machu picchu", "machupicchu",
        "montaña de colores", "rainbow mountain", "vinicunca",
        "valle sagrado", "sacred valley",
        "ollantaytambo", "pisac", "chinchero",
        "sacsayhuaman", "qenqo", "tambomachay",
        "moray", "maras", "salineras",
        "salkantay", "choquequirao",
        "humantay", "laguna humantay",
        "cusco", "cuzco", "plaza de armas",
    ]
    
    def __init__(self):
        self.contact_extractor = ContactExtractor()
    
    def extract_lead_data(self, text: str, url: str = "") -> Dict:
        """
        Extrae todos los datos relevantes de un texto
        Retorna un diccionario con la información del lead potencial
        """
        text_lower = text.lower()
        
        # Extraer contactos
        contacts = self.contact_extractor.extract_all(text)
        
        # Detectar fase del viaje
        phase, intent_score = self._detect_travel_phase(text_lower)
        
        # Detectar destinos de interés
        destinations = self._detect_destinations(text_lower)
        
        # Extraer keywords encontradas
        keywords = self._extract_keywords(text_lower)
        
        # Detectar idioma (simple)
        language = self._detect_language(text)
        
        # Calcular score inicial
        initial_score = self._calculate_initial_score(
            contacts=contacts,
            phase=phase,
            destinations=destinations,
            keywords=keywords
        )
        
        return {
            "contacts": contacts,
            "phase": phase,
            "intent_score": intent_score,
            "destinations": destinations,
            "keywords": keywords,
            "language": language,
            "initial_score": initial_score,
            "source_url": url,
            "raw_text": text[:500]  # Primeros 500 caracteres
        }
    
    def _detect_travel_phase(self, text: str) -> Tuple[str, float]:
        """Detecta la fase del viaje basada en keywords"""
        high_intent_count = sum(1 for kw in self.HIGH_INTENT_KEYWORDS if kw in text)
        planning_count = sum(1 for kw in self.PLANNING_KEYWORDS if kw in text)
        dreaming_count = sum(1 for kw in self.DREAMING_KEYWORDS if kw in text)
        
        total = high_intent_count + planning_count + dreaming_count
        
        if total == 0:
            return "unknown", 0.0
        
        if high_intent_count >= planning_count and high_intent_count >= dreaming_count:
            return "booking", min(1.0, high_intent_count * 0.2)
        elif planning_count >= dreaming_count:
            return "planning", min(1.0, planning_count * 0.15)
        else:
            return "dreaming", min(1.0, dreaming_count * 0.1)
    
    def _detect_destinations(self, text: str) -> List[str]:
        """Detecta destinos de Cusco mencionados"""
        found = []
        for dest in self.CUSCO_DESTINATIONS:
            if dest in text:
                # Normalizar nombre
                normalized = dest.title().replace("Machu Picchu", "Machu Picchu")
                if normalized not in found:
                    found.append(normalized)
        return found
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae todas las keywords encontradas"""
        found = []
        all_keywords = (
            self.HIGH_INTENT_KEYWORDS + 
            self.PLANNING_KEYWORDS + 
            self.DREAMING_KEYWORDS
        )
        
        for kw in all_keywords:
            if kw in text and kw not in found:
                found.append(kw)
        
        return found
    
    def _detect_language(self, text: str) -> str:
        """Detección simple de idioma"""
        spanish_words = ["el", "la", "de", "que", "en", "para", "con", "por"]
        english_words = ["the", "is", "to", "in", "for", "with", "on", "at"]
        
        text_lower = text.lower()
        spanish_count = sum(1 for w in spanish_words if f" {w} " in text_lower)
        english_count = sum(1 for w in english_words if f" {w} " in text_lower)
        
        return "es" if spanish_count >= english_count else "en"
    
    def _calculate_initial_score(
        self,
        contacts: Dict,
        phase: str,
        destinations: List[str],
        keywords: List[str]
    ) -> int:
        """
        Calcula el score inicial del lead
        Basado en el sistema de Lead Scoring del Pilar III
        """
        score = 0
        
        # Puntaje por contactos
        if contacts.get("phones"):
            score += 30  # Teléfono es muy valioso (WhatsApp)
            # Bonus por WhatsApp compatible
            if any(c.is_whatsapp_compatible for c in contacts["phones"]):
                score += 10
        
        if contacts.get("emails"):
            score += 15
            # Penalización por emails desechables
            if any(c.confidence < 1.0 for c in contacts["emails"]):
                score -= 10
        
        # Puntaje por fase
        phase_scores = {
            "booking": 30,
            "planning": 20,
            "dreaming": 10,
            "unknown": 5
        }
        score += phase_scores.get(phase, 0)
        
        # Puntaje por destinos
        score += min(15, len(destinations) * 5)
        
        # Puntaje por keywords de alta intención
        high_intent_found = sum(
            1 for kw in keywords 
            if kw in self.HIGH_INTENT_KEYWORDS
        )
        score += min(15, high_intent_found * 5)
        
        return max(0, min(100, score))
