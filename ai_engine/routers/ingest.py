"""
routers/ingest.py — Ingesta de contenido al índice vectorial.
GTR-PUCP CDN Educativa Offline

Endpoints:
  POST /ingest             → ingesta de un contenido por content_id
  POST /ingest/reindex-all → reindexado completo (admin)
  GET  /ingest/status/{id} → estado del job de ingesta

Ver ai-search-engine-plan.md §9 para el pipeline completo.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ai_engine.services.ingestion.pipeline import ingest_content

logger = logging.getLogger(__name__)
router = APIRouter()

# Registro en memoria del estado de cada job (content_id → estado)
# En producción esto puede moverse a Redis o a la BD del CDN backend.
_job_status: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    content_id: str   # UUID del contenido en PostgreSQL / CDN backend


class ReindexRequest(BaseModel):
    confirm: bool = False


class IngestResponse(BaseModel):
    content_id:  str
    status:      str          # "queued" | "running" | "ok" | "error"
    chunks_added: Optional[int]   = None
    thumbnail_url: Optional[str]  = None
    error:        Optional[str]   = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _run_ingest_job(content_id: str) -> None:
    """Tarea de background: ejecuta el pipeline y guarda el resultado."""
    _job_status[content_id] = {"status": "running", "content_id": content_id}
    try:
        result = await ingest_content(content_id)
        _job_status[content_id] = result
    except Exception as exc:
        logger.exception("Error en job de ingesta content_id=%s", content_id)
        _job_status[content_id] = {
            "content_id": content_id,
            "status": "error",
            "chunks_added": 0,
            "error": str(exc),
        }


async def _reindex_all_job() -> None:
    """
    Consulta todos los content_ids del CDN backend y los reindexar en secuencia.
    Usa la misma semáforo que ingest_content para no saturar el sistema.
    """
    import httpx
    from ai_engine.config import settings

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{settings.CDN_BACKEND_URL}/api/content?limit=5000")
        if resp.status_code != 200:
            logger.error("reindex-all: no se pudo obtener listado de contenidos (%d)", resp.status_code)
            return
        data    = resp.json()
        items   = data.get("content", data) if isinstance(data, dict) else data
        ids     = [item.get("id") or item.get("content_id") for item in items if item.get("id") or item.get("content_id")]
        logger.info("reindex-all: %d contenidos a reindexar", len(ids))
        for cid in ids:
            try:
                await ingest_content(str(cid))
            except Exception as exc:
                logger.warning("reindex-all: error en %s: %s", cid, exc)
        logger.info("reindex-all completado")
    except Exception as exc:
        logger.exception("reindex-all: error general: %s", exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    """
    Encola la ingesta de un contenido al índice vectorial.

    El procesamiento se ejecuta en background (BackgroundTasks de FastAPI).
    La llamada retorna inmediatamente con status="queued".
    El CDN backend recibirá una notificación PATCH cuando el proceso termine.

    Llamado automáticamente desde uploadController.ts al completar la subida.
    """
    content_id = req.content_id.strip()
    if not content_id:
        raise HTTPException(status_code=422, detail="content_id no puede estar vacío")

    # Si ya hay un job corriendo para este contenido, no duplicar
    current = _job_status.get(content_id, {})
    if current.get("status") == "running":
        return IngestResponse(content_id=content_id, status="running")

    _job_status[content_id] = {"content_id": content_id, "status": "queued"}
    background_tasks.add_task(_run_ingest_job, content_id)
    logger.info("[INGEST] content_id=%s encolado", content_id)

    return IngestResponse(content_id=content_id, status="queued")


@router.get("/ingest/status/{content_id}", response_model=IngestResponse)
async def ingest_status(content_id: str):
    """
    Retorna el estado del job de ingesta para un content_id.

    Estados posibles:
      - "queued"   → esperando en la cola
      - "running"  → pipeline ejecutándose
      - "ok"       → completado con éxito
      - "error"    → falló (ver campo `error`)
      - "unknown"  → no hay registro (content_id no fue pedido aún)
    """
    if content_id not in _job_status:
        return IngestResponse(content_id=content_id, status="unknown")
    job = _job_status[content_id]
    return IngestResponse(
        content_id=content_id,
        status=job.get("status", "unknown"),
        chunks_added=job.get("chunks_added"),
        thumbnail_url=job.get("thumbnail_url"),
        error=job.get("error"),
    )


@router.post("/ingest/reindex-all")
async def reindex_all(req: ReindexRequest, background_tasks: BackgroundTasks):
    """
    Re-indexa todo el contenido del CDN desde cero.

    Pasos:
      1. Obtiene todos los content_ids del CDN backend
      2. Llama a ingest_content() para cada uno en secuencia (respetando semáforo)

    Requiere body: `{"confirm": true}` para evitar ejecuciones accidentales.

    Uso: migración Fase 1 → Fase 2 o recuperación de ChromaDB corrompida.
    """
    if not req.confirm:
        return {
            "error": "Enviar confirm: true para ejecutar reindexado completo",
            "warning": "Esta operación puede tardar horas dependiendo del volumen de contenidos",
        }
    background_tasks.add_task(_reindex_all_job)
    logger.info("[INGEST] reindex-all encolado")
    return {"status": "queued", "message": "Reindexado completo iniciado en background"}
