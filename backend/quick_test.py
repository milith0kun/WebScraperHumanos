"""
Test rápido del scraper
"""
import asyncio
from app.scraper.engine import PlaywrightScraper

async def test():
    print("Iniciando test de Playwright...")
    
    scraper = PlaywrightScraper()
    await scraper.initialize()
    
    context = await scraper.create_context()
    page = await scraper.new_page(context)
    
    success = await scraper.safe_goto(page, "https://example.com")
    
    if success:
        title = await page.title()
        print(f"✅ Página cargada: {title}")
    else:
        print("❌ Error cargando página")
    
    await scraper.close()
    print("Test completado!")

if __name__ == "__main__":
    asyncio.run(test())
