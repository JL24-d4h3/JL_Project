"""
services/ingestion/pipeline.py — Pipeline principal de ingesta de contenido al índice vectorial.
GTR-PUCP CDN Educativa Offline

Flujo completo de ingesta (ver docs/ai-search-engine-plan.md §9):

  1. Consultar PostgreSQL (CDN backend) → obtener metadata del contenido
  2. Extraer texto según tipo:
       video   → STT con Whisper Small (stt.transcribe_for_ingest)
       pdf/doc → extracción de texto con PyMuPDF / python-docx
       audio   → STT con Whisper Small
       image   → usar title + description (sin extracción)
  3. Chunkear en 3 niveles jerárquicos (chunker.py)
  4. Generar embeddings con multilingual-e5-small y persistir en ChromaDB
  5. Actualizar índice BM25 en memoria
  6. Generar miniatura si no existe (thumbnail_generator.py)
  7. Notificar al CDN backend → PATCH /api/content/{id}?indexed=true

La función pública es `ingest_content(content_id)`.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from pathlib import Path

from ai_engine.config import settings
from ai_engine.services import stt
from ai_engine.services.ingestion.chunker import (
    TextChunk,
    chunk_text,
    chunk_transcript,
)
from ai_engine.services.ingestion.pdf_extractor import extract_text
from ai_engine.services.ingestion.thumbnail_generator import generate_thumbnail

logger = logging.getLogger(__name__)

# Semáforo para limitar la concurrencia durante la ingesta
# (evita saturar CPU/GPU mientras se sirven búsquedas en tiempo real)
_MAX_CONCURRENT_INGEST = 1 if settings.INGESTION_MODE == "semaphore_cautious" else 2
_ingest_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_INGEST)


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------

async def ingest_content(content_id: str) -> dict:
    """
    Ingesta completa de un contenido al índice vectorial.

    Args:
        content_id: UUID del contenido en PostgreSQL / CDN backend.

    Returns:
        {
          "content_id": str,
          "status": "ok" | "error",
          "chunks_added": int,
          "thumbnail_url": str,
          "error": str | None,
        }
    """
    async with _ingest_semaphore:
        logger.info("[INGEST] Iniciando ingesta de content_id=%s", content_id)
        try:
            result = await _run_pipeline(content_id)
            logger.info(
                "[INGEST] Completado content_id=%s — %d chunks, thumbnail=%s",
                content_id, result.get("chunks_added", 0), result.get("thumbnail_url")
            )
            return result
        except Exception as exc:
            logger.exception("[INGEST] Error en content_id=%s: %s", content_id, exc)
            return {
                "content_id": content_id,
                "status": "error",
                "chunks_added": 0,
                "thumbnail_url": None,
                "error": str(exc),
            }


# ---------------------------------------------------------------------------
# Pipeline interno
# ---------------------------------------------------------------------------

async def _run_pipeline(content_id: str) -> dict:
    # ── 1. Obtener metadata desde el CDN backend ──────────────────────────────
    meta = await _fetch_content_metadata(content_id)
    if not meta:
        raise RuntimeError(f"Contenido {content_id} no encontrado en el CDN backend")

    content_type: str  = meta.get("type", "document").lower()   # video|audio|pdf|document|image
    title:        str  = meta.get("title", "")
    description:  str  = meta.get("description", "") or ""
    category:     str  = meta.get("category", "general")
    file_name:    str  = meta.get("file_name", "")
    file_path:    str  = _resolve_file_path(meta)
    thumbnail_url: Optional[str] = meta.get("thumbnail_url")

    logger.info(
        "[INGEST] %s | tipo=%s | archivo=%s",
        title[:60], content_type, file_name
    )

    # ── 2. Extraer texto / transcripción ──────────────────────────────────────
    chunks: list[TextChunk] = []

    if content_type == "video":
        chunks = await _extract_video(file_path, title, description)
    elif content_type == "audio":
        chunks = await _extract_audio(file_path, title, description)
    elif content_type in ("pdf", "document"):
        chunks = await _extract_document(file_path, title, description)
    elif content_type == "image":
        # Imágenes: solo indexar title + description
        combined = f"{title}. {description}".strip()
        if combined:
            chunks = chunk_text(combined, source_type="description")
    else:
        logger.warning("[INGEST] Tipo desconocido '%s' — indexando solo metadata", content_type)
        combined = f"{title}. {description}".strip()
        if combined:
            chunks = chunk_text(combined, source_type="description")

    logger.info("[INGEST] %d chunks generados para %s", len(chunks), content_id)

    # ── 3. Persistir chunks en ChromaDB ───────────────────────────────────────
    chunks_added = 0
    if chunks:
        chunks_added = await _index_chunks(content_id, meta, chunks)

    # ── 4. Actualizar índice BM25 ─────────────────────────────────────────────
    if chunks:
        await _update_bm25([c.text for c in chunks])

    # ── 5. Generar miniatura si no existe ─────────────────────────────────────
    if not thumbnail_url:
        thumbnail_url = await generate_thumbnail(
            content_id=content_id,
            content_type=content_type,
            file_path=file_path,
            category=category,
        )

    # ── 6. Notificar al CDN backend que el contenido fue indexado ─────────────
    await _notify_indexed(content_id, thumbnail_url=thumbnail_url)

    return {
        "content_id":   content_id,
        "status":       "ok",
        "chunks_added": chunks_added,
        "thumbnail_url": thumbnail_url,
        "error":        None,
    }


# ---------------------------------------------------------------------------
# Extracción por tipo de contenido
# ---------------------------------------------------------------------------

async def _extract_video(file_path: str, title: str, description: str) -> list[TextChunk]:
    """Transcribe el video con Whisper Small y aplica chunk_transcript."""
    if not file_path or not Path(file_path).exists():
        logger.warning("[INGEST] Archivo de video no encontrado: %s", file_path)
        # Fallback: indexar solo metadatos
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    try:
        segments = await stt.transcribe_for_ingest(file_path)
    except Exception as exc:
        logger.error("[INGEST] Error STT video %s: %s — indexando solo metadata", file_path, exc)
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    if not segments:
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    chunks = chunk_transcript(segments)

    # Agregar chunk extra con title+description para mejorar la búsqueda por título
    if title:
        meta_text = f"{title}. {description}".strip()
        meta_chunks = chunk_text(meta_text, source_type="description")
        chunks = meta_chunks[:1] + chunks  # solo el summary de metadata

    return chunks


async def _extract_audio(file_path: str, title: str, description: str) -> list[TextChunk]:
    """Igual que video pero el archivo es audio puro (MP3/WAV/M4A)."""
    return await _extract_video(file_path, title, description)


async def _extract_document(file_path: str, title: str, description: str) -> list[TextChunk]:
    """Extrae texto del PDF/DOCX y genera chunks jerárquicos."""
    if not file_path or not Path(file_path).exists():
        logger.warning("[INGEST] Archivo de documento no encontrado: %s", file_path)
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    text = await extract_text(file_path)
    if not text:
        # PDF sin texto extraíble: indexar solo metadata
        logger.warning("[INGEST] Sin texto extraído de %s — indexando solo metadata", file_path)
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    # Prefijar con title para mejorar relevancia en búsquedas por título
    full_text = f"{title}\n\n{description}\n\n{text}" if title else text
    return chunk_text(full_text, source_type="pdf_text")


# ---------------------------------------------------------------------------
# ChromaDB — indexación de chunks
# ---------------------------------------------------------------------------

async def _index_chunks(
    content_id: str,
    meta: dict,
    chunks: list[TextChunk],
) -> int:
    """
    Pide al hybrid_retriever que indexe los chunks en ChromaDB.
    Cada chunk se almacena con su metadata para permitir deep links.

    Returns:
        Número de chunks efectivamente añadidos.
    """
    from ai_engine.services.hybrid_retriever import retriever

    if not retriever.is_ready:
        logger.error("[INGEST] Retriever no inicializado — no se pueden indexar chunks")
        return 0

    # Eliminar chunks anteriores del mismo content_id (reindexado)
    try:
        await retriever.delete_by_content_id(content_id)
    except Exception as exc:
        logger.warning("[INGEST] No se pudieron borrar chunks anteriores de %s: %s", content_id, exc)

    ids:        list[str]  = []
    texts:      list[str]  = []
    metadatas:  list[dict] = []

    for chunk in chunks:
        chunk_id = f"{content_id}_{chunk.chunk_index}"
        ids.append(chunk_id)
        texts.append(chunk.text)
        meta_entry = {
            "content_id":    content_id,
            "chunk_index":   chunk.chunk_index,
            "chunk_type":    chunk.chunk_type,
            "total_chunks":  chunk.total_chunks,
            "source_type":   chunk.source_type,
            "title":         meta.get("title", "")[:200],
            "category":      meta.get("category", ""),
            "content_type":  meta.get("type", ""),
        }
        if chunk.timestamp_start is not None:
            meta_entry["timestamp_start"] = chunk.timestamp_start
            meta_entry["timestamp_end"]   = chunk.timestamp_end or chunk.timestamp_start
        metadatas.append(meta_entry)

    try:
        added = await retriever.add_chunks(ids=ids, texts=texts, metadatas=metadatas)
        return added
    except Exception as exc:
        logger.error("[INGEST] Error indexando en ChromaDB content_id=%s: %s", content_id, exc)
        return 0


async def _update_bm25(texts: list[str]) -> None:
    """Solicita al retriever que actualice su índice BM25."""
    from ai_engine.services.hybrid_retriever import retriever
    try:
        await retriever.update_bm25(texts)
    except Exception as exc:
        logger.warning("[INGEST] Error actualizando BM25: %s", exc)


# ---------------------------------------------------------------------------
# Comunicación con el CDN backend (Node/Express)
# ---------------------------------------------------------------------------

async def _fetch_content_metadata(content_id: str) -> Optional[dict]:
    """
    Llama a GET /api/content/{content_id} del CDN backend para obtener la metadata.
    Retorna None si el contenido no existe o hay un error de red.
    """
    import httpx
    url = f"{settings.CDN_BACKEND_URL}/api/content/{content_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            # El backend puede retornar { content: {...} } o directamente {...}
            return data.get("content", data)
        logger.warning(
            "[INGEST] CDN backend retornó %d para content_id=%s",
            resp.status_code, content_id
        )
        return None
    except Exception as exc:
        logger.error("[INGEST] Error consultando metadata de %s: %s", content_id, exc)
        return None


async def _notify_indexed(content_id: str, thumbnail_url: Optional[str] = None) -> None:
    """
    PATCH /api/content/{content_id} → marca el contenido como indexado
    y actualiza la URL de miniatura si se generó una nueva.
    """
    import httpx
    url = f"{settings.CDN_BACKEND_URL}/api/content/{content_id}"
    payload: dict = {"ai_indexed": True}
    if thumbnail_url:
        payload["thumbnail_url"] = thumbnail_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=payload)
        if resp.status_code not in (200, 204):
            logger.warning(
                "[INGEST] Notificación al CDN backend falló (%d) para %s",
                resp.status_code, content_id
            )
    except Exception as exc:
        logger.warning("[INGEST] No se pudo notificar al CDN backend: %s", exc)


def _resolve_file_path(meta: dict) -> str:
    """
    Convierte la metadata del contenido en una ruta absoluta al archivo.
    Busca en STORAGE_PATH según el tipo de contenido.
    """
    storage  = Path(settings.STORAGE_PATH)
    file_name = meta.get("file_name") or meta.get("filename") or ""
    content_type = meta.get("type", "document").lower()

    if content_type == "video":
        subdir = "videos"
    elif content_type == "audio":
        subdir = "audio"
    elif content_type in ("pdf", "document"):
        subdir = "documents"
    elif content_type == "image":
        subdir = "images"
    else:
        subdir = "documents"

    if not file_name:
        return ""

    return str(storage / subdir / file_name)
