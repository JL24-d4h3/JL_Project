"""
services/ingestion/pipeline.py — Pipeline principal de ingesta de contenido al índice vectorial.
GTR-PUCP CDN Educativa Offline

Flujo completo de ingesta (actualizado con clasificación automática):

  1. Consultar PostgreSQL (CDN backend) → obtener metadata del contenido
  2. Extraer texto según tipo:
       video   → STT con Whisper Small (stt.transcribe_for_ingest)
       pdf/doc → extracción de texto con PyMuPDF / python-docx
       audio   → STT con Whisper Small
       code    → lectura directa del archivo fuente
       image   → usar title + description (sin extracción)
  3. Clasificación automática con IA:
       → Analizar texto + código con ContentClassifier
       → Extraer dominio (AI, DB, NET, etc.), área, confianza y tags
       → Los metadatos se usan para pre-filtrado en búsqueda
  4. Chunkear en 3 niveles jerárquicos (chunker.py)
  5. Generar embeddings con multilingual-e5-small y persistir en ChromaDB
       → Cada chunk incluye metadatos de clasificación automática
  6. Actualizar índice BM25 en memoria
  7. Generar miniatura si no existe (thumbnail_generator.py)
  8. Notificar al CDN backend → PATCH /api/content/{id}?indexed=true

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
from ai_engine.services.classifier import classify_content

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
    extracted_text: str = ""
    extracted_code: str = ""

    if content_type == "video":
        chunks = await _extract_video(file_path, title, description)
        # Para clasificación, extraer texto de los chunks
        extracted_text = "\n".join(c.text for c in chunks)
    elif content_type == "audio":
        chunks = await _extract_audio(file_path, title, description)
        extracted_text = "\n".join(c.text for c in chunks)
    elif content_type in ("pdf", "document"):
        chunks = await _extract_document(file_path, title, description)
        extracted_text = "\n".join(c.text for c in chunks)
    elif content_type == "code":
        chunks = await _extract_code(file_path, title, description)
        # Para código, separar texto descriptivo de código fuente
        extracted_text = f"{title}\n{description}"
        extracted_code = "\n".join(c.text for c in chunks)
    elif content_type == "image":
        # Imágenes: solo indexar title + description
        combined = f"{title}. {description}".strip()
        if combined:
            chunks = chunk_text(combined, source_type="description")
        extracted_text = combined
    else:
        logger.warning("[INGEST] Tipo desconocido '%s' — indexando solo metadata", content_type)
        combined = f"{title}. {description}".strip()
        if combined:
            chunks = chunk_text(combined, source_type="description")
        extracted_text = combined

    logger.info("[INGEST] %d chunks generados para %s", len(chunks), content_id)

    # ── 3. Clasificación automática de contenido ─────────────────────────────
    classification = {}
    if extracted_text or extracted_code:
        try:
            classification = classify_content(
                text=extracted_text[:5000],  # Limitar para performance
                code=extracted_code[:5000] if extracted_code else None,
                title=title,
                description=description,
            )
            logger.info(
                "[INGEST] Clasificación: domain=%s, area=%s, confidence=%.2f",
                classification.get("domain", "OTHER"),
                classification.get("area", "unknown"),
                classification.get("confidence", 0.0),
            )
        except Exception as exc:
            logger.warning("[INGEST] Error en clasificación: %s", exc)
            classification = {
                "domain": "OTHER",
                "area": "unknown",
                "confidence": 0.0,
                "tags": [],
            }

    # ── 4. Persistir chunks en ChromaDB ───────────────────────────────────────
    chunks_added = 0
    if chunks:
        chunks_added = await _index_chunks(content_id, meta, chunks, classification)

    # ── 5. Actualizar índice BM25 ─────────────────────────────────────────────
    if chunks:
        await _update_bm25([c.text for c in chunks])

    # ── 6. Generar miniatura si no existe ─────────────────────────────────────
    if not thumbnail_url:
        thumbnail_url = await generate_thumbnail(
            content_id=content_id,
            content_type=content_type,
            file_path=file_path,
            category=category,
        )

    # ── 7. Notificar al CDN backend que el contenido fue indexado ─────────────
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


async def _extract_code(file_path: str, title: str, description: str) -> list[TextChunk]:
    """Lee el archivo de código fuente como texto plano y genera chunks."""
    if not file_path or not Path(file_path).exists():
        logger.warning("[INGEST] Archivo de código no encontrado: %s", file_path)
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    try:
        code_text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.error("[INGEST] Error leyendo código %s: %s", file_path, exc)
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    if not code_text.strip():
        return chunk_text(f"{title}. {description}".strip(), source_type="description")

    full_text = f"{title}\n\n{description}\n\n{code_text}" if title else code_text
    return chunk_text(full_text, source_type="code")


# ---------------------------------------------------------------------------
# ChromaDB — indexación de chunks
# ---------------------------------------------------------------------------

async def _index_chunks(
    content_id: str,
    meta: dict,
    chunks: list[TextChunk],
    classification: dict,
) -> int:
    """
    Pide al hybrid_retriever que indexe los chunks en ChromaDB.
    Cada chunk se almacena con su metadata para permitir deep links
    y con metadatos de clasificación automática para pre-filtrado.

    Returns:
        Número de chunks efectivamente añadidos.
    """
    from ai_engine.services.hybrid_retriever import retriever

    # Asegurar que el retriever está inicializado
    if not retriever.is_ready:
        logger.info("[INGEST] Inicializando retriever (no estaba listo)...")
        await retriever.init()
    
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
            # Metadatos de clasificación automática
            "auto_domain":      classification.get("domain", "OTHER"),
            "auto_area":        classification.get("area", "unknown"),
            "auto_confidence":  classification.get("confidence", 0.0),
            "auto_tags":        ",".join(classification.get("tags", [])[:10]),
            "auto_semantic_terms": ",".join(classification.get("semantic_terms", [])[:20]),
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

    El backend retorna: { success: true, data: { id, title, file_path, type, ... } }
    """
    import httpx
    url = f"{settings.CDN_BACKEND_URL}/api/content/{content_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            body = resp.json()
            # El backend retorna { success, data: {...} }
            return body.get("data", body.get("content", body))
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

    El backend almacena file_path como ruta relativa al STORAGE_PATH,
    p.ej. "code/abc123.py", "videos/abc123.mp4", "documents/abc123.pdf".
    """
    storage = Path(settings.STORAGE_PATH)

    # Preferir file_path del backend (ya es ruta relativa correcta)
    file_path = meta.get("file_path", "")
    if file_path:
        full = storage / file_path
        if full.exists():
            return str(full)
        logger.warning("[INGEST] file_path '%s' no encontrado en disco", full)

    # Fallback: construir desde file_name + tipo
    file_name = meta.get("file_name") or meta.get("filename") or ""
    if not file_name:
        return ""

    content_type = meta.get("type", "document").lower()
    subdir_map = {
        "video": "videos",
        "audio": "audio",
        "pdf": "documents",
        "document": "documents",
        "image": "images",
        "code": "code",
    }
    subdir = subdir_map.get(content_type, "documents")
    return str(storage / subdir / file_name)
