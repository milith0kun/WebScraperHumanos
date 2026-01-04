"""
Scrapers específicos para diferentes fuentes de datos
"""
from typing import List, Dict, Optional, Any
from playwright.async_api import Page, BrowserContext
from loguru import logger
from datetime import datetime
import asyncio

from app.scraper.engine import PlaywrightScraper
from app.scraper.extractors import DataExtractor
from app.models.lead import Lead, LeadPhase, ContactInfo, LeadInteraction


class BaseScraper:
    """Base para todos los scrapers específicos"""
    
    def __init__(self, engine: PlaywrightScraper):
        self.engine = engine
        self.extractor = DataExtractor()
    
    async def scrape(self, url: str, config: Dict = None) -> List[Dict]:
        """Método abstracto para scraping"""
        raise NotImplementedError


class TripAdvisorScraper(BaseScraper):
    """
    Scraper específico para foros de TripAdvisor
    Extrae discusiones y perfiles de usuarios interesados en Cusco
    """
    
    BASE_URL = "https://www.tripadvisor.com"
    FORUM_SELECTORS = {
        "thread_list": "div.forum-list a.title",
        "thread_title": "h1.title",
        "posts": "div.post",
        "post_content": "div.postBody",
        "post_author": "a.username",
        "post_date": "span.postDate",
        "next_page": "a.next",
    }
    
    async def scrape_forum(
        self, 
        forum_url: str,
        max_threads: int = 20,
        max_posts_per_thread: int = 50
    ) -> List[Dict]:
        """
        Scrapea un foro de TripAdvisor
        """
        logger.info(f"Iniciando scraping de TripAdvisor: {forum_url}")
        results = []
        
        context = await self.engine.create_context()
        page = await self.engine.new_page(context)
        
        try:
            # Navegar al foro
            success = await self.engine.safe_goto(page, forum_url)
            if not success:
                logger.error("No se pudo cargar el foro")
                return results
            
            # Esperar carga de contenido
            await page.wait_for_load_state("networkidle")
            await self.engine.human_delay(1000, 2000)
            
            # Obtener lista de threads
            thread_links = await page.query_selector_all(
                self.FORUM_SELECTORS["thread_list"]
            )
            
            logger.info(f"Encontrados {len(thread_links)} threads")
            
            # Limitar threads
            thread_links = thread_links[:max_threads]
            
            # Extraer URLs de threads
            thread_urls = []
            for link in thread_links:
                href = await link.get_attribute("href")
                if href:
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    thread_urls.append(full_url)
            
            # Procesar cada thread
            for i, thread_url in enumerate(thread_urls):
                logger.info(f"Procesando thread {i+1}/{len(thread_urls)}")
                
                thread_data = await self._scrape_thread(
                    page, 
                    thread_url,
                    max_posts_per_thread
                )
                
                if thread_data:
                    results.extend(thread_data)
                
                await self.engine.human_delay(2000, 4000)
            
        except Exception as e:
            logger.error(f"Error en scraping de TripAdvisor: {e}")
        finally:
            await self.engine.close_context(context)
        
        logger.success(f"✅ TripAdvisor: {len(results)} posts procesados")
        return results
    
    async def _scrape_thread(
        self, 
        page: Page, 
        thread_url: str,
        max_posts: int
    ) -> List[Dict]:
        """Scrapea un thread individual"""
        results = []
        
        success = await self.engine.safe_goto(page, thread_url)
        if not success:
            return results
        
        await page.wait_for_load_state("networkidle")
        
        # Obtener título del thread
        title = await self.engine.extract_text(
            page, 
            self.FORUM_SELECTORS["thread_title"]
        )
        
        # Scroll para cargar más contenido
        await self.engine.scroll_page(page, scroll_count=3)
        
        # Obtener posts
        posts = await page.query_selector_all(self.FORUM_SELECTORS["posts"])
        posts = posts[:max_posts]
        
        for post in posts:
            try:
                # Extraer contenido
                content_el = await post.query_selector(
                    self.FORUM_SELECTORS["post_content"]
                )
                content = await content_el.text_content() if content_el else ""
                
                # Extraer autor
                author_el = await post.query_selector(
                    self.FORUM_SELECTORS["post_author"]
                )
                author = await author_el.text_content() if author_el else "Unknown"
                author_url = await author_el.get_attribute("href") if author_el else None
                
                if content:
                    # Extraer datos del lead
                    lead_data = self.extractor.extract_lead_data(
                        content, 
                        thread_url
                    )
                    
                    # Solo agregar si tiene potencial
                    if lead_data["initial_score"] > 20 or lead_data["contacts"]["phones"]:
                        results.append({
                            "platform": "tripadvisor",
                            "thread_title": title,
                            "thread_url": thread_url,
                            "author": author,
                            "author_url": f"{self.BASE_URL}{author_url}" if author_url else None,
                            "content": content[:1000],
                            **lead_data
                        })
                        
            except Exception as e:
                logger.debug(f"Error procesando post: {e}")
        
        return results
    
    async def scrape(self, url: str, config: Dict = None) -> List[Dict]:
        """Implementación del método abstracto"""
        config = config or {}
        return await self.scrape_forum(
            url,
            max_threads=config.get("max_threads", 20),
            max_posts_per_thread=config.get("max_posts", 50)
        )


class GenericWebScraper(BaseScraper):
    """
    Scraper genérico para sitios web
    Útil para analizar páginas de competidores
    """
    
    async def scrape_page(self, url: str) -> Dict:
        """Scrapea una página web genérica"""
        logger.info(f"Scraping página: {url}")
        
        context = await self.engine.create_context()
        page = await self.engine.new_page(context)
        
        try:
            success = await self.engine.safe_goto(page, url)
            if not success:
                return {"error": "No se pudo cargar la página"}
            
            await page.wait_for_load_state("networkidle")
            await self.engine.scroll_page(page, scroll_count=5)
            
            # Obtener todo el texto visible
            body_text = await page.evaluate("""
                () => document.body.innerText
            """)
            
            # Obtener título
            title = await page.title()
            
            # Obtener todos los links
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({
                        text: a.innerText.trim(),
                        href: a.href
                    }))
                    .filter(l => l.text.length > 0)
            """)
            
            # Buscar formularios de contacto
            forms = await page.evaluate("""
                () => Array.from(document.querySelectorAll('form'))
                    .map(f => ({
                        action: f.action,
                        method: f.method,
                        fields: Array.from(f.querySelectorAll('input, textarea, select'))
                            .map(i => ({
                                name: i.name,
                                type: i.type,
                                placeholder: i.placeholder
                            }))
                    }))
            """)
            
            # Buscar botones de WhatsApp
            whatsapp_buttons = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href*="wa.me"], a[href*="whatsapp"]'))
                    .map(a => a.href)
            """)
            
            # Extraer datos con el extractor
            lead_data = self.extractor.extract_lead_data(body_text, url)
            
            return {
                "url": url,
                "title": title,
                "links_count": len(links),
                "forms": forms,
                "whatsapp_buttons": whatsapp_buttons,
                **lead_data
            }
            
        except Exception as e:
            logger.error(f"Error en scraping genérico: {e}")
            return {"error": str(e)}
        finally:
            await self.engine.close_context(context)
    
    async def scrape(self, url: str, config: Dict = None) -> List[Dict]:
        """Implementación del método abstracto"""
        result = await self.scrape_page(url)
        return [result] if "error" not in result else []


class CompetitorAnalyzer(BaseScraper):
    """
    Analizador de sitios de competidores
    Extrae estrategias de conversión y puntos de contacto
    """
    
    async def analyze_competitor(self, url: str) -> Dict:
        """Analiza un sitio de competidor"""
        logger.info(f"Analizando competidor: {url}")
        
        context = await self.engine.create_context()
        page = await self.engine.new_page(context)
        
        analysis = {
            "url": url,
            "contact_points": [],
            "conversion_elements": [],
            "services": [],
            "pricing_found": False,
            "whatsapp_integration": False,
            "chat_widget": False,
        }
        
        try:
            success = await self.engine.safe_goto(page, url)
            if not success:
                return {"error": "No se pudo cargar la página"}
            
            await page.wait_for_load_state("networkidle")
            await self.engine.scroll_page(page, scroll_count=5)
            
            # Detectar elementos de conversión
            cta_buttons = await page.evaluate("""
                () => Array.from(document.querySelectorAll('button, a.btn, .cta, [class*="button"]'))
                    .map(el => el.innerText.trim())
                    .filter(text => text.length > 0 && text.length < 50)
            """)
            analysis["conversion_elements"] = list(set(cta_buttons))[:20]
            
            # Detectar WhatsApp
            whatsapp = await page.query_selector('a[href*="wa.me"], a[href*="whatsapp"]')
            analysis["whatsapp_integration"] = whatsapp is not None
            
            # Detectar chat widgets
            chat_selectors = [
                '[class*="chat"]', '[id*="chat"]',
                '[class*="intercom"]', '[class*="zendesk"]',
                '[class*="tawk"]', '[class*="crisp"]'
            ]
            for selector in chat_selectors:
                chat = await page.query_selector(selector)
                if chat:
                    analysis["chat_widget"] = True
                    break
            
            # Detectar precios
            pricing_text = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    return text.includes('price') || text.includes('precio') || 
                           text.includes('$') || text.includes('usd') ||
                           text.includes('desde') || text.includes('from');
                }
            """)
            analysis["pricing_found"] = pricing_text
            
            # Extraer servicios mencionados
            body_text = await page.evaluate("() => document.body.innerText")
            lead_data = self.extractor.extract_lead_data(body_text, url)
            analysis["services"] = lead_data.get("destinations", [])
            analysis["contacts"] = lead_data.get("contacts", {})
            
        except Exception as e:
            logger.error(f"Error analizando competidor: {e}")
            analysis["error"] = str(e)
        finally:
            await self.engine.close_context(context)
        
        return analysis
    
    async def scrape(self, url: str, config: Dict = None) -> List[Dict]:
        """Implementación del método abstracto"""
        result = await self.analyze_competitor(url)
        return [result] if "error" not in result else []
