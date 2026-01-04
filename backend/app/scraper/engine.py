"""
Motor de Web Scraping con Playwright
Implementación resiliente con auto-wait y gestión de contextos
"""
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional, List, Dict, Any, Callable
from loguru import logger
from datetime import datetime
import asyncio
import random

from app.config import settings


class PlaywrightScraper:
    """
    Motor principal de scraping usando Playwright
    Características:
    - Multi-navegador (Chromium, Firefox, WebKit)
    - Auto-wait inteligente
    - Gestión de contextos múltiples
    - Rotación de User-Agents
    - Detección anti-bot
    """
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self._is_initialized = False
    
    async def initialize(self, browser_type: str = "chromium"):
        """Inicializa el navegador"""
        if self._is_initialized:
            return
        
        logger.info(f"Inicializando Playwright con {browser_type}...")
        
        self.playwright = await async_playwright().start()
        
        # Seleccionar tipo de navegador
        browser_launcher = getattr(self.playwright, browser_type)
        
        self.browser = await browser_launcher.launch(
            headless=settings.headless_mode,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        self._is_initialized = True
        logger.success(f"✅ Playwright inicializado ({browser_type})")
    
    async def create_context(self, with_stealth: bool = True) -> BrowserContext:
        """
        Crea un nuevo contexto de navegación aislado
        Cada contexto tiene su propio almacenamiento y cookies
        """
        if not self.browser:
            raise RuntimeError("Browser no inicializado. Llama a initialize() primero.")
        
        user_agent = random.choice(self.USER_AGENTS)
        
        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="es-PE",
            timezone_id="America/Lima",
            permissions=["geolocation"],
            geolocation={"latitude": -13.5319, "longitude": -71.9675},  # Cusco
        )
        
        if with_stealth:
            # Inyectar scripts anti-detección
            await context.add_init_script("""
                // Ocultar webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Ocultar plugins de automatización
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Ocultar chrome automation
                window.chrome = {
                    runtime: {}
                };
                
                // Simular permisos normales
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
        
        self.contexts.append(context)
        logger.debug(f"Contexto creado (Total: {len(self.contexts)})")
        
        return context
    
    async def new_page(self, context: Optional[BrowserContext] = None) -> Page:
        """Crea una nueva página en el contexto dado"""
        if context is None:
            context = await self.create_context()
        
        page = await context.new_page()
        
        # Configurar timeouts por defecto
        page.set_default_timeout(30000)  # 30 segundos
        page.set_default_navigation_timeout(60000)  # 60 segundos
        
        return page
    
    async def safe_goto(
        self, 
        page: Page, 
        url: str, 
        wait_until: str = "domcontentloaded"
    ) -> bool:
        """
        Navega a una URL de forma segura con reintentos
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Navegando a: {url} (intento {attempt + 1})")
                
                response = await page.goto(url, wait_until=wait_until)
                
                if response and response.ok:
                    logger.success(f"✅ Página cargada: {url}")
                    return True
                else:
                    logger.warning(f"Respuesta no OK: {response.status if response else 'None'}")
                    
            except Exception as e:
                logger.error(f"Error navegando a {url}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial
        
        return False
    
    async def extract_text(self, page: Page, selector: str) -> Optional[str]:
        """Extrae texto de un elemento"""
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                return await element.text_content()
        except Exception:
            pass
        return None
    
    async def extract_all_text(self, page: Page, selector: str) -> List[str]:
        """Extrae texto de todos los elementos que coinciden"""
        try:
            elements = await page.query_selector_all(selector)
            texts = []
            for el in elements:
                text = await el.text_content()
                if text:
                    texts.append(text.strip())
            return texts
        except Exception:
            return []
    
    async def extract_attribute(
        self, 
        page: Page, 
        selector: str, 
        attribute: str
    ) -> Optional[str]:
        """Extrae un atributo de un elemento"""
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                return await element.get_attribute(attribute)
        except Exception:
            pass
        return None
    
    async def scroll_page(
        self, 
        page: Page, 
        scroll_count: int = 3,
        delay_ms: int = 1000
    ):
        """Hace scroll en la página para cargar contenido dinámico"""
        for i in range(scroll_count):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay_ms / 1000)
            logger.debug(f"Scroll {i + 1}/{scroll_count}")
    
    async def human_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Simula un delay humano aleatorio"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    async def take_screenshot(self, page: Page, filename: str):
        """Toma una captura de pantalla"""
        await page.screenshot(path=filename, full_page=True)
        logger.info(f"Screenshot guardado: {filename}")
    
    async def get_page_content(self, page: Page) -> str:
        """Obtiene todo el contenido HTML de la página"""
        return await page.content()
    
    async def close_context(self, context: BrowserContext):
        """Cierra un contexto específico"""
        if context in self.contexts:
            self.contexts.remove(context)
        await context.close()
    
    async def close(self):
        """Cierra el navegador y limpia recursos"""
        logger.info("Cerrando Playwright...")
        
        for context in self.contexts:
            try:
                await context.close()
            except Exception:
                pass
        
        self.contexts.clear()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        self._is_initialized = False
        logger.success("✅ Playwright cerrado correctamente")


# Singleton del scraper
_scraper_instance: Optional[PlaywrightScraper] = None


async def get_scraper() -> PlaywrightScraper:
    """Obtiene la instancia singleton del scraper"""
    global _scraper_instance
    
    if _scraper_instance is None:
        _scraper_instance = PlaywrightScraper()
        await _scraper_instance.initialize()
    elif not _scraper_instance._is_initialized:
        await _scraper_instance.initialize()
    
    return _scraper_instance


async def close_scraper():
    """Cierra el scraper singleton"""
    global _scraper_instance
    
    if _scraper_instance:
        await _scraper_instance.close()
        _scraper_instance = None
