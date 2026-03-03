"""
routers/voice_search.py — STT + búsqueda semántica en un solo endpoint.
GTR-PUCP CDN Educativa Offline

Flujo:
  1. Recibir audio WAV/WebM (máx 15 s) como UploadFile
  2. stt.transcribe(temp_path) → texto transcrito con Whisper Tiny
  3. Ejecutar el mismo pipeline que POST /search (retriever + LLM)
  4. Retornar JSON normal (no SSE) con query_transcribed + resultados completos

Ver ai-search-engine-plan.md §4 para el diseño completo.
"""
from __future__ import annotations
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ai_engine.config import settings
from ai_engine.services import stt
from ai_engine.services.hybrid_retriever import retriever
from ai_engine.services.llm_engine import llm_engine
from ai_engine.routers.search import (
    _triage_from_query_and_chunks,
    _build_prompt,
    _chunks_to_cdn_cards,
    _generate_suggestions,
    _L1_MIN_SCORE,
)

logger = logging.getLogger(__name__)
router  = APIRouter()

_MAX_AUDIO_BYTES = 5 * 1024 * 1024   # 5 MB — ~15 s en webm/opus
_ALLOWED_SUFFIX  = {".webm", ".wav", ".ogg", ".mp3", ".m4a", ".flac"}


@router.post("/voice-search")
async def voice_search(
    audio:   UploadFile = File(..., description="Audio WAV/WebM, máx 15 s"),
    context: str        = Form(default="{}"),
):
    """
    Transcribe audio con Whisper Tiny y ejecuta el pipeline de búsqueda completo.

    Respuesta:
    ```json
    {
      "query_transcribed": "¿qué es una red LAN?",
      "language_detected": "es",
      "cdn_results": [...],
      "ai_overview": { "text": "...", "level": "L1", "grounding": {...} },
      "suggestions": [...]
    }
    ```
    """
    # ── 1. Validar el archivo ───────────────────────────────────────────────
    if not stt.is_ready:
        raise HTTPException(status_code=503, detail="STT no inicializado — reintentar en unos segundos")

    content_type = (audio.content_type or "").lower()
    filename_ext = Path(audio.filename or "audio.webm").suffix.lower()

    if filename_ext not in _ALLOWED_SUFFIX and "audio" not in content_type:
        raise HTTPException(
            status_code=415,
            detail=f"Formato de audio no soportado: {filename_ext or content_type}. "
                   f"Usar: {', '.join(_ALLOWED_SUFFIX)}",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio demasiado grande ({len(audio_bytes) // 1024} KB). Máximo: {_MAX_AUDIO_BYTES // 1024} KB",
        )
    if len(audio_bytes) < 512:
        raise HTTPException(status_code=422, detail="Audio demasiado corto o vacío")

    # ── 2. Guardar en temp y transcribir ────────────────────────────────────
    suffix = filename_ext if filename_ext in _ALLOWED_SUFFIX else ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        stt_result = await stt.transcribe(tmp_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Error en STT voice-search: %s", exc)
        raise HTTPException(status_code=500, detail="Error al transcribir el audio")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    query    = stt_result.get("text", "").strip()
    language = stt_result.get("language", "es")

    logger.info("voice-search STT: '%s' (lang=%s, %d bytes)", query[:80], language, len(audio_bytes))

    if not query:
        raise HTTPException(
            status_code=422,
            detail="No se detectó voz en el audio. Intenta hablar más cerca del micrófono.",
        )

    # ── 3. Pipeline de búsqueda ─────────────────────────────────────────────
    try:
        chunks = await retriever.search(query, top_k=settings.TOP_K_FINAL)
    except Exception as exc:
        logger.warning("Retriever falló en voice-search: %s", exc)
        chunks = []

    cards  = _chunks_to_cdn_cards(chunks)
    level  = _triage_from_query_and_chunks(query, chunks)
    prompt = _build_prompt(query, chunks, level)

    # Para voice-search usamos la versión no-streaming (el cliente espera JSON)
    tokens: list[str] = []
    try:
        async for tok in llm_engine.generate_stream(prompt):
            tokens.append(tok)
    except Exception as exc:
        logger.error("LLM falló en voice-search: %s", exc)
        tokens = ["No se pudo generar una respuesta. Revisa los recursos en los resultados."]

    coverage = round(
        len([c for c in chunks if c.get("score", 0) >= _L1_MIN_SCORE]) / max(len(chunks), 1),
        2,
    )

    return {
        "query_transcribed": query,
        "language_detected": language,
        "cdn_results":       cards,
        "ai_overview": {
            "text":    "".join(tokens),
            "level":   level,
            "grounding": {
                "coverage_score": coverage,
                "is_grounded":    level in ("L1", "L2") and bool(chunks),
            },
        },
        "suggestions": _generate_suggestions(query, level),
    }
