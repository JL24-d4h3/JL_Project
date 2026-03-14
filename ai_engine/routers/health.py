"""
routers/health.py — Health check endpoint
Usado en la verificación §12 de la guía de inicio.
"""
from fastapi import APIRouter
from ai_engine.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    """
    Retorna el estado del AI Engine.
    Usado para verificar que todos los componentes cargaron correctamente.
    """
    from ai_engine.services.thermal_manager import thermal_manager
    from ai_engine.services.hybrid_retriever import retriever
    from ai_engine.services.llm_engine import llm_engine
    from ai_engine.services import stt

    chunk_count = await retriever.chunk_count() if retriever.is_ready else 0

    return {
        "status":   "ok",
        "platform": settings.PLATFORM,
        "components": {
            "llm_engine":     "ready" if llm_engine.is_ready else "not_ready",
            "retriever":      "ready" if retriever.is_ready else "not_ready",
            "stt":            "ready" if stt.is_ready else "not_ready",
            "thermal":        thermal_manager.current_profile,
            "chroma_chunks":  chunk_count,
        },
        "config": {
            "speculative":    settings.SPECULATIVE_DECODING,
            "gamma":          settings.SPECULATIVE_GAMMA,
            "max_context":    settings.MAX_CONTEXT_TOKENS,
            "max_gen":        settings.MAX_GENERATION_TOKENS,
            "hyde":           settings.HYDE_ENABLED,
            "cross_encoder":  settings.CROSS_ENCODER_ENABLED,
            "chroma_max":     settings.CHROMA_MAX_CHUNKS,
        },
    }
