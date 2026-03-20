"""
routers/search.py — Búsqueda híbrida con SSE streaming.
GTR-PUCP CDN Educativa Offline

Pipeline completo:
  1. hybrid_retriever.search(query) → chunks rerankeados
  2. Triaje adaptativo L1..L4 según cobertura de resultados
  3. Construir prompt con fuentes formateadas
  4. llm_engine.generate_stream(prompt) → tokens SSE
  5. Emitir: cdn_results → tokens → done

Contrato SSE (ver docs/ai-search-engine-plan.md §12):
  data: {"type":"cdn_results","data":[...]}
  data: {"type":"token","text":"..."}
  data: {"type":"done","suggestions":[...]}

Ver ai-search-engine-plan.md §12 para el contrato completo.
"""
from __future__ import annotations
import json
import logging
import asyncio
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai_engine.config import settings, prompts
from ai_engine.services.hybrid_retriever import retriever
from ai_engine.services.llm_engine import llm_engine
from ai_engine.services.classifier import classify_query
from ai_engine.services.adaptive_learning import record_search_event, record_feedback_event

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    context: dict = {}


class SearchFeedbackRequest(BaseModel):
    event_type: str
    query: str
    content_id: str | None = None
    corrected_query: str | None = None
    notes: str | None = None


# ── Triage thresholds ────────────────────────────────────────────────────────
_L1_MIN_SCORE  = 0.70   # chunks con score >= L1_MIN → nivel L1 (solo fuentes)
_L2_MIN_CHUNKS = 1      # al menos 1 chunk con score aceptable → nivel L2

# Umbral para filtrar resultados poco relevantes.
# Balance: 0.86 permite variantes (algoritmia→algoritmo) pero filtra irrelevantes (agricultura)
# Con cross-encoder ON: el reranking normaliza mejor, threshold más bajo (0.45)
_MIN_SCORE     = 0.86 if not settings.CROSS_ENCODER_ENABLED else 0.45  

_AMBIGUOUS_LEN = 3      # query de <= 3 palabras sin chunks → L4 (aclarar)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _triage(chunks: list[dict]) -> str:
    """Determina el nivel de triaje L1..L4 según los chunks recuperados."""
    if not chunks:
        return "L4" if True else "L3"   # simplificado; L4 si query muy corta

    high_quality = [c for c in chunks if c.get("score", 0) >= _L1_MIN_SCORE]
    any_quality  = [c for c in chunks if c.get("score", 0) >= _MIN_SCORE]

    if high_quality:
        return "L1"
    if any_quality:
        return "L2"
    return "L3"


def _triage_from_query_and_chunks(query: str, chunks: list[dict]) -> str:
    """Triage más detallado que también considera la longitud de la query."""
    words = query.strip().split()
    if not chunks:
        # Query muy corta sin resultados → pedir aclaración
        return "L4" if len(words) <= _AMBIGUOUS_LEN else "L3"
    return _triage(chunks)


def _format_sources(chunks: list[dict]) -> str:
    """Formatea chunks como bloque de fuentes para el prompt del LLM."""
    lines: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        ts_start = chunk.get("timestamp_start")
        time_info = f"Tiempo: {ts_start:.0f}s\n" if ts_start is not None else ""
        lines.append(
            prompts.SOURCE_TEMPLATE.format(
                index=i,
                title=chunk.get("title", "Sin título")[:120],
                content_type=chunk.get("content_type", chunk.get("type", "desconocido")),
                time_info=time_info,
                text=chunk.get("text", "")[:600],
            )
        )
    return prompts.CONTEXT_TEMPLATE.format(sources="\n".join(lines))


def _build_prompt(query: str, chunks: list[dict], level: str) -> str:
    """Construye el prompt completo (system + context + user)."""
    system_map = {
        "L1": prompts.SYSTEM_PROMPT_L1,
        "L2": prompts.SYSTEM_PROMPT_L2,
        "L3": prompts.SYSTEM_PROMPT_L3,
        "L4": prompts.SYSTEM_PROMPT_L4_CLARIFICATION,
    }
    system = system_map.get(level, prompts.SYSTEM_PROMPT_L3)

    if level in ("L1", "L2") and chunks:
        sources_block = _format_sources(chunks)
        anti_hall = prompts.ANTI_HALLUCINATION_REMINDER if level == "L1" else ""
        return (
            f"{system}\n\n"
            f"CONTEXTO DE LA RED LOCAL:\n{sources_block}\n"
            f"{anti_hall}\n\n"
            f"PREGUNTA: {query}"
        )
    return f"{system}\n\nPREGUNTA: {query}"


def _chunks_to_cdn_cards(chunks: list[dict]) -> list[dict]:
    """
    Convierte los chunks recuperados en tarjetas para el frontend.
    Deduplica por content_id y preserva el chunk de mayor score.
    """
    seen:  dict[str, dict] = {}
    for chunk in chunks:
        cid   = chunk.get("content_id", "")
        score = float(chunk.get("score", 0.0))

        # Filtrar resultados poco relevantes (threshold estricto)
        if score < _MIN_SCORE:
            continue
            
        if cid not in seen or score > seen[cid].get("relevance_score", 0):
            ts = chunk.get("timestamp_start")
            viewer_suffix = f"?t={ts:.0f}" if ts is not None else ""
            ctype = chunk.get("content_type", chunk.get("type", "document"))
            viewer_base = f"/viewer/{'video' if ctype == 'video' else 'document'}/{cid}"
            seen[cid] = {
                "content_id":      cid,
                "content_type":    ctype,
                "title":           chunk.get("title", ""),
                "snippet":         chunk.get("text", "")[:200],
                "thumbnail_url":   f"/storage/thumbnails/{cid}.jpg",
                "viewer_url":      viewer_base + viewer_suffix,
                "relevance_score": round(score, 4),
            }
    # Ordenar por relevancia descendente
    return sorted(seen.values(), key=lambda c: c["relevance_score"], reverse=True)


def _generate_suggestions(query: str, level: str) -> list[str]:
    """Genera sugerencias de búsqueda relacionadas (heurística simple)."""
    words = [w for w in query.lower().split() if len(w) > 3]
    if not words:
        return []
    base = words[0].capitalize()
    suggestions = []
    if level in ("L1", "L2"):
        suggestions = [
            f"¿Cómo funciona {base}?",
            f"Ejercicios sobre {base}",
            f"Ejemplos de {query}",
        ]
    else:
        suggestions = [
            f"¿Qué es {base}?",
            f"{base} definición",
        ]
    return suggestions[:3]


def _sse(data: dict) -> str:
    """Serializa un evento SSE."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Core async generator ──────────────────────────────────────────────────────

async def _search_generator(query: str, context: dict) -> AsyncIterator[str]:
    """
    Generador principal del stream SSE.
    Orden de eventos: cdn_results → tokens → done
    """
    query = query.strip()
    if not query:
        yield _sse({"type": "error", "message": "Query vacía"})
        return

    query_class = classify_query(query)
    effective_query = query_class.get("query_corrected") or query

    # Gate con Llama 3.2-1B solo en ambigüedad o baja confianza
    if (
        (query_class.get("confidence", 0.0) < 0.62 or query_class.get("domain") is None)
        and llm_engine.can_adapt_queries()
    ):
        llm_adapt = await llm_engine.classify_and_expand_query(effective_query)
        if llm_adapt and llm_adapt.get("rewrites"):
            effective_query = llm_adapt["rewrites"][0]
            logger.info(
                "[SEARCH] Query adaptada por LLM: '%s' -> '%s' (domain=%s conf=%.2f)",
                query,
                effective_query,
                llm_adapt.get("domain"),
                llm_adapt.get("confidence", 0.0),
            )

    # 1. Recuperar chunks
    try:
        chunks = await retriever.search(effective_query, top_k=settings.TOP_K_FINAL)
    except Exception as exc:
        logger.warning("Retriever falló para query='%s': %s — usando resultados vacíos", query, exc)
        chunks = []

    # 2. Construir tarjetas CDN y emitirlas primero (el frontend las muestra de inmediato)
    cards = _chunks_to_cdn_cards(chunks)

    # Segundo intento con LLM si aún no hay resultados
    if not cards and llm_engine.can_adapt_queries():
        llm_adapt = await llm_engine.classify_and_expand_query(effective_query)
        if llm_adapt and llm_adapt.get("rewrites"):
            retry_query = llm_adapt["rewrites"][0]
            if retry_query and retry_query != effective_query:
                retry_chunks = await retriever.search(retry_query, top_k=settings.TOP_K_FINAL)
                retry_cards = _chunks_to_cdn_cards(retry_chunks)
                if retry_cards:
                    effective_query = retry_query
                    chunks = retry_chunks
                    cards = retry_cards
    yield _sse({"type": "cdn_results", "data": cards})

    # Pequeño delay para que el frontend renderice las tarjetas antes del streaming
    await asyncio.sleep(0.05)

    # 3. Triage
    level = _triage_from_query_and_chunks(effective_query, chunks)
    logger.debug("search query='%s' level=%s chunks=%d cards=%d", query, level, len(chunks), len(cards))

    record_search_event(
        query=query,
        effective_query=effective_query,
        query_domain=query_class.get("domain"),
        query_confidence=query_class.get("confidence", 0.0),
        result_count=len(cards),
        top_content_ids=[c.get("content_id", "") for c in cards],
    )

    record_search_event(
        query=query,
        effective_query=effective_query,
        query_domain=query_class.get("domain"),
        query_confidence=query_class.get("confidence", 0.0),
        result_count=len(cards),
        top_content_ids=[c.get("content_id", "") for c in cards],
    )

    # 4. Construir prompt y streamear LLM (solo si hay resultados y no estamos en laptop/CPU)
    should_generate_overview = bool(cards) and settings.PLATFORM != "laptop"

    if should_generate_overview:
        prompt = _build_prompt(effective_query, chunks, level)
        try:
            async for token in llm_engine.generate_stream(prompt):
                yield _sse({"type": "token", "text": token})
        except Exception as exc:
            logger.error("LLM generate_stream falló: %s", exc)
            # Emitir mensaje de fallback en lugar de silencio
            fallback = (
                "No se pudo generar una respuesta en este momento. "
                "Por favor, revisa los recursos de la CDN en los resultados anteriores."
            )
            for word in fallback.split():
                yield _sse({"type": "token", "text": word + " "})
                await asyncio.sleep(0.02)
    else:
        # No generar overview en CPU (evita sobrecalentamiento)
        if not cards:
            yield _sse({"type": "token", "text": "No se encontraron resultados relevantes para tu búsqueda."})
        else:
            yield _sse({"type": "token", "text": "Resultados encontrados. Revisa las tarjetas anteriores."})

    # 5. Evento de cierre
    yield _sse({
        "type":        "done",
        "level":       level,
        "suggestions": _generate_suggestions(query, level),
        "grounding": {
            "coverage_score": round(len([c for c in chunks if c.get("score", 0) >= _L1_MIN_SCORE]) / max(len(chunks), 1), 2),
            "is_grounded":    level in ("L1", "L2") and bool(chunks),
        },
    })


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/search")
async def search(req: SearchRequest):
    """
    Búsqueda híbrida — versión no-streaming.
    Agrega todos los tokens antes de responder.
    Útil para testing y clientes que no soportan SSE.
    """
    query = req.query.strip()
    if not query:
        return {"error": "Query vacía"}

    query_class = classify_query(query)
    effective_query = query_class.get("query_corrected") or query

    if (
        (query_class.get("confidence", 0.0) < 0.62 or query_class.get("domain") is None)
        and llm_engine.can_adapt_queries()
    ):
        llm_adapt = await llm_engine.classify_and_expand_query(effective_query)
        if llm_adapt and llm_adapt.get("rewrites"):
            effective_query = llm_adapt["rewrites"][0]

    chunks  = await retriever.search(effective_query, top_k=settings.TOP_K_FINAL)
    cards   = _chunks_to_cdn_cards(chunks)
    level   = _triage_from_query_and_chunks(effective_query, chunks)
    prompt  = _build_prompt(effective_query, chunks, level)

    record_search_event(
        query=query,
        effective_query=effective_query,
        query_domain=query_class.get("domain"),
        query_confidence=query_class.get("confidence", 0.0),
        result_count=len(cards),
        top_content_ids=[c.get("content_id", "") for c in cards],
    )

    tokens: list[str] = []
    # No generar overview en laptop/CPU para evitar sobrecalentamiento
    # Solo generar si hay resultados para evitar alucinaciones
    should_generate_overview = bool(cards) and settings.PLATFORM != "laptop"

    if should_generate_overview:
        try:
            async for tok in llm_engine.generate_stream(prompt):
                tokens.append(tok)
        except Exception as exc:
            logger.error("LLM falló en /search: %s", exc)

    return {
        "query":       query,
        "effective_query": effective_query,
        "cdn_results": cards,
        "ai_overview": {
            "text":    "".join(tokens),
            "level":   level,
            "grounding": {
                "coverage_score": round(len([c for c in chunks if c.get("score", 0) >= _L1_MIN_SCORE]) / max(len(chunks), 1), 2),
                "is_grounded":    level in ("L1", "L2") and bool(chunks),
            },
            "language_detected": "es",
        },
        "suggestions": _generate_suggestions(query, level),
    }


@router.post("/search/feedback")
async def search_feedback(req: SearchFeedbackRequest):
    record_feedback_event(
        event_type=req.event_type,
        query=req.query,
        content_id=req.content_id,
        corrected_query=req.corrected_query,
        notes=req.notes,
    )
    return {"status": "ok"}


@router.post("/search/stream")
async def search_stream(req: SearchRequest):
    """
    Búsqueda híbrida con streaming SSE — endpoint principal del buscador.

    Formato de respuesta (text/event-stream):
      data: {"type":"cdn_results","data":[{content_id, title, snippet, ...}, ...]}
      data: {"type":"token","text":"palabra "}
      ...
      data: {"type":"done","level":"L1","suggestions":[...], "grounding":{...}}

    El frontend (useSSESearch.ts) consume este stream.
    """
    return StreamingResponse(
        _search_generator(req.query, req.context),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",   # deshabilitar buffering en Nginx
        },
    )
