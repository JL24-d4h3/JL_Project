"""
main.py — AI Engine Entry Point
GTR-PUCP CDN Educativa Offline

Arrancar:
  AI_PLATFORM=orin_nano_8gb uvicorn ai_engine.main:app --host 0.0.0.0 --port 8000
  o bien: uvicorn ai_engine.main:app --env-file ai_engine/.env --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_engine.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cierre de recursos pesados."""
    logger.info("=== AI Engine iniciando — Platform: %s ===", settings.PLATFORM)

    # 0) Database connection pool
    from ai_engine.services.database import init_db_pool, close_db_pool
    await init_db_pool()
    logger.info("✓ Database pool initialized")

    # 1) Gestor térmico (DEBE ser lo primero)
    from ai_engine.services.thermal_manager import thermal_manager
    await thermal_manager.start()
    logger.info("✓ Thermal manager activo — perfil: %s", settings.THERMAL_PROFILE)

    # 2) Embedder (GPU)
    from ai_engine.services.hybrid_retriever import retriever
    await retriever.init()
    logger.info("✓ Retriever listo — ChromaDB: %d chunks", await retriever.chunk_count())

    # 3) LLM Engine (TensorRT-LLM — carga más larga)
    from ai_engine.services.llm_engine import llm_engine
    await llm_engine.init()
    logger.info(
        "✓ LLM engine listo — draft: %s, target: %s, speculative: %s γ=%d",
        settings.DRAFT_MODEL_DIR,
        settings.TARGET_MODEL_DIR,
        settings.SPECULATIVE_DECODING,
        settings.SPECULATIVE_GAMMA,
    )

    # 4) Whisper Tiny para STT de consultas
    from ai_engine.services import stt
    await stt.init()
    logger.info("✓ Whisper Tiny listo (STT de consultas)")

    logger.info("=== AI Engine listo para recibir peticiones ===")
    yield

    # Cierre limpio
    logger.info("=== AI Engine cerrando ===")
    await thermal_manager.stop()
    await llm_engine.shutdown()
    from ai_engine.services.database import close_db_pool
    await close_db_pool()
    logger.info("✓ Database pool closed")


app = FastAPI(
    title="GTR-PUCP AI Engine",
    description="Motor de búsqueda IA offline para CDN educativa",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — solo permite el CDN backend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.CDN_BACKEND_URL,
        "http://localhost:3000",
        "http://localhost:5174",  # search_ui
        "http://localhost:5176",  # receiver
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from ai_engine.routers import search, voice_search, ingest, health, auth  # noqa: E402

app.include_router(health.router,       prefix="/api",         tags=["health"])
app.include_router(auth.router,         tags=["authentication"])
app.include_router(search.router,       prefix="/api",         tags=["search"])
app.include_router(voice_search.router, prefix="/api",         tags=["voice"])
app.include_router(ingest.router,       prefix="/api",         tags=["ingest"])


@app.get("/")
async def root():
    return {
        "service":  "GTR-PUCP AI Engine",
        "platform": settings.PLATFORM,
        "status":   "running",
        "docs":     "/docs",
    }
