# Cusco Lead Scraper - Backend

## 🚀 Inicio Rápido

### 1. Crear entorno virtual
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Instalar navegadores de Playwright
```bash
playwright install chromium
```

### 4. Configurar MongoDB Atlas
1. Ve a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) y crea una cuenta/cluster gratuito
2. Obtén tu connection string
3. Edita el archivo `.env` y coloca tu URI:
```
MONGODB_URI=mongodb+srv://tu_usuario:tu_password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### 5. Ejecutar tests
```bash
python test_scraper.py
```

### 6. Iniciar servidor
```bash
python main.py
# o
uvicorn main:app --reload --port 8000
```

### 7. Acceder a la documentación
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── api/               # Endpoints REST
│   │   ├── leads.py      # CRUD de leads
│   │   └── scraper.py    # Control del scraper
│   ├── models/            # Modelos MongoDB
│   │   ├── lead.py       # Modelo de Lead
│   │   ├── scraping_job.py
│   │   └── source.py
│   ├── scraper/           # Motor de scraping
│   │   ├── engine.py     # Playwright wrapper
│   │   ├── extractors.py # Regex extractors
│   │   └── sources.py    # Scrapers específicos
│   ├── services/          # Lógica de negocio
│   │   └── lead_scorer.py
│   ├── config.py          # Configuración
│   └── database.py        # Conexión MongoDB
├── main.py                # Entry point
├── test_scraper.py        # Tests
├── requirements.txt
└── .env
```

---

## 🔧 API Endpoints

### Leads
- `GET /api/v1/leads` - Listar leads con filtros
- `GET /api/v1/leads/stats` - Estadísticas
- `GET /api/v1/leads/hot` - Leads calientes
- `GET /api/v1/leads/{id}` - Detalle de lead
- `POST /api/v1/leads` - Crear lead manual
- `PATCH /api/v1/leads/{id}` - Actualizar lead
- `DELETE /api/v1/leads/{id}` - Eliminar lead

### Scraper
- `POST /api/v1/scraper/start` - Iniciar scraping
- `GET /api/v1/scraper/jobs` - Listar trabajos
- `GET /api/v1/scraper/jobs/{id}` - Estado de trabajo
- `POST /api/v1/scraper/extract` - Extracción rápida de texto
- `POST /api/v1/scraper/test` - Probar scraper

---

## 📊 Lead Scoring

El sistema califica leads de 0-100 basado en:

| Factor | Puntos |
|--------|--------|
| WhatsApp disponible | +35 |
| Email válido | +15 |
| Fase Booking | +30 |
| Fase Planning | +20 |
| Destino Machu Picchu | +10 |
| Keywords de precio | +10 |
| Email desechable | -15 |
| Sospecha de bot | -50 |

### Prioridades
- 🔥 **HOT** (80-100): Contactar inmediatamente
- 🌡️ **WARM** (50-79): Nutrir con información
- ❄️ **COLD** (0-49): Mantener en pipeline
