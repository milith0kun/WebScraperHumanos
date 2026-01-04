"""
Test de conexión a MongoDB Atlas
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def test_connection():
    print("🔌 Probando conexión a MongoDB Atlas...")
    print(f"   Base de datos: {settings.mongodb_db_name}")
    
    try:
        client = AsyncIOMotorClient(settings.mongodb_uri)
        
        # Ping para verificar conexión
        await client.admin.command('ping')
        print("✅ Conexión exitosa a MongoDB Atlas!")
        
        # Listar bases de datos
        dbs = await client.list_database_names()
        print(f"   Bases de datos disponibles: {dbs}")
        
        # Verificar/crear nuestra BD
        db = client[settings.mongodb_db_name]
        collections = await db.list_collection_names()
        print(f"   Colecciones en '{settings.mongodb_db_name}': {collections}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    if result:
        print("\n🎉 MongoDB Atlas está listo para usar!")
    else:
        print("\n⚠️ Revisa tu configuración de MongoDB")
