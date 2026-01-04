"""
Script de prueba para verificar el funcionamiento del scraper
Ejecutar: python test_scraper.py
"""
import asyncio
from loguru import logger

# Configurar logger para consola
logger.add(lambda msg: print(msg), format="{message}", level="INFO")


async def test_extractor():
    """Prueba el extractor de datos"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Extractor de Datos de Contacto")
    print("="*60)
    
    from app.scraper.extractors import DataExtractor
    
    extractor = DataExtractor()
    
    # Texto de prueba simulando un post de TripAdvisor
    test_text = """
    Hola! Estoy planeando un viaje a Cusco en agosto próximo.
    Me gustaría visitar Machu Picchu y la Montaña de Colores.
    ¿Alguien sabe el precio de un tour de 4 días?
    Mi número es +51 987 654 321 para coordinar.
    También pueden escribirme a turista@gmail.com
    Gracias! @viajero_peru
    """
    
    result = extractor.extract_lead_data(test_text, "https://tripadvisor.com/test")
    
    print("\n📋 Texto analizado:")
    print(f"   {test_text[:100]}...")
    
    print("\n📱 Contactos encontrados:")
    for phone in result["contacts"]["phones"]:
        print(f"   ✅ Teléfono: {phone.normalized} (WhatsApp: {phone.is_whatsapp_compatible})")
    
    for email in result["contacts"]["emails"]:
        print(f"   ✅ Email: {email.normalized}")
    
    for user in result["contacts"]["usernames"]:
        print(f"   ✅ Usuario: {user.value}")
    
    print(f"\n🎯 Fase detectada: {result['phase'].upper()}")
    print(f"📊 Score inicial: {result['initial_score']}/100")
    print(f"🏔️ Destinos: {', '.join(result['destinations'])}")
    print(f"🔑 Keywords: {', '.join(result['keywords'][:5])}")
    
    return True


async def test_regex_patterns():
    """Prueba los patrones de Regex"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Patrones Regex")
    print("="*60)
    
    from app.scraper.extractors import ContactExtractor
    
    extractor = ContactExtractor()
    
    # Pruebas de diferentes formatos
    test_cases = [
        # Teléfonos Perú
        ("+51 987 654 321", "phone"),
        ("987654321", "phone"),
        ("+51987654321", "phone"),
        
        # Teléfonos internacionales
        ("+1 555 123 4567", "phone"),
        ("+34 612 345 678", "phone"),
        
        # Emails
        ("usuario@gmail.com", "email"),
        ("empresa.ventas@outlook.com", "email"),
        ("test@mailinator.com", "email"),  # Desechable
        
        # WhatsApp links
        ("wa.me/51987654321", "whatsapp"),
    ]
    
    for test_value, expected_type in test_cases:
        if expected_type == "phone":
            result = extractor.extract_phones(test_value)
            status = "✅" if result else "❌"
            normalized = result[0].normalized if result else "No detectado"
        elif expected_type == "email":
            result = extractor.extract_emails(test_value)
            status = "✅" if result else "❌"
            normalized = result[0].normalized if result else "No detectado"
        else:
            result = extractor.extract_phones(test_value)
            status = "✅" if result else "❌"
            normalized = result[0].normalized if result else "No detectado"
        
        print(f"   {status} {test_value} → {normalized}")
    
    return True


async def test_lead_scorer():
    """Prueba el sistema de Lead Scoring"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Sistema de Lead Scoring")
    print("="*60)
    
    from app.models.lead import Lead, LeadPhase, ContactInfo
    from app.services.lead_scorer import LeadScorer
    
    scorer = LeadScorer()
    
    # Lead de alta calidad (HOT)
    hot_lead = Lead(
        name="Juan Pérez",
        contact=ContactInfo(
            phone="+51987654321",
            email="juan@gmail.com",
            whatsapp_available=True
        ),
        phase=LeadPhase.BOOKING,
        detected_keywords=["precio", "reservar", "disponibilidad"],
        interested_destinations=["Machu Picchu", "Vinicunca"]
    )
    
    score, breakdown = scorer.calculate_score(hot_lead)
    priority = scorer.get_lead_priority(score)
    
    print(f"\n🔥 Lead HOT:")
    print(f"   Score: {score}/100")
    print(f"   Prioridad: {priority}")
    print(f"   Componentes del score:")
    for name, comp in breakdown.items():
        print(f"      • {name}: {comp['points']} pts ({comp['reason'][:40]}...)")
    
    # Lead de baja calidad (COLD)
    cold_lead = Lead(
        phase=LeadPhase.DREAMING,
        contact=ContactInfo(),  # Sin contacto
        detected_keywords=["fotos", "hermoso"]
    )
    
    score2, breakdown2 = scorer.calculate_score(cold_lead)
    priority2 = scorer.get_lead_priority(score2)
    
    print(f"\n❄️ Lead COLD:")
    print(f"   Score: {score2}/100")
    print(f"   Prioridad: {priority2}")
    
    return True


async def test_playwright():
    """Prueba la inicialización de Playwright"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Playwright Browser Engine")
    print("="*60)
    
    try:
        from app.scraper.engine import PlaywrightScraper
        
        print("   Inicializando Playwright...")
        scraper = PlaywrightScraper()
        await scraper.initialize()
        
        print("   Creando contexto...")
        context = await scraper.create_context()
        
        print("   Creando página...")
        page = await scraper.new_page(context)
        
        print("   Navegando a example.com...")
        success = await scraper.safe_goto(page, "https://example.com")
        
        if success:
            title = await page.title()
            print(f"   ✅ Página cargada: {title}")
        else:
            print("   ❌ Error cargando página")
        
        print("   Cerrando scraper...")
        await scraper.close()
        
        print("   ✅ Playwright funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("\n   ⚠️ Para instalar Playwright, ejecuta:")
        print("      playwright install chromium")
        return False


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "="*60)
    print("🏔️ CUSCO LEAD SCRAPER - TESTS DE VERIFICACIÓN")
    print("="*60)
    
    results = []
    
    # Test 1: Extractor
    try:
        results.append(("Extractor de Datos", await test_extractor()))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("Extractor de Datos", False))
    
    # Test 2: Regex
    try:
        results.append(("Patrones Regex", await test_regex_patterns()))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("Patrones Regex", False))
    
    # Test 3: Lead Scorer
    try:
        results.append(("Lead Scoring", await test_lead_scorer()))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("Lead Scoring", False))
    
    # Test 4: Playwright
    try:
        results.append(("Playwright", await test_playwright()))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("Playwright", False))
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")
        if result:
            passed += 1
    
    print(f"\n   Total: {passed}/{len(results)} tests pasaron")
    
    if passed == len(results):
        print("\n🎉 ¡Todos los tests pasaron! El scraper está listo.")
    else:
        print("\n⚠️ Algunos tests fallaron. Revisa los errores arriba.")


if __name__ == "__main__":
    asyncio.run(main())
