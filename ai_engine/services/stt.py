"""
services/stt.py — Speech-to-Text con Whisper (faster-whisper / CTranslate2)
GTR-PUCP CDN Educativa Offline

Dos modelos según el contexto de uso:
  QUERY  → Whisper Tiny  (39 MB,  CPU, ~0.8 s en Jetson) — consultas en tiempo real
  INGEST → Whisper Small (244 MB, CPU, ~1 min por 10 min de video) — ingesta batch

Ver docs/ai-search-engine-plan.md §4 para detalles.
"""
import asyncio
import logging
import tempfile
from pathlib import Path

from ai_engine.config import settings

logger = logging.getLogger(__name__)

is_ready: bool = False
_query_model   = None   # Whisper Tiny — STT de consultas en tiempo real
_ingest_model  = None   # Whisper Small — STT de videos en ingesta (lazy load)


async def init() -> None:
    """
    Carga Whisper Tiny en CPU. Llamado una vez en el lifespan de main.py.
    Whisper Small para ingesta se carga de forma lazy (solo cuando se necesite).
    """
    global is_ready, _query_model
    logger.info(
        "Cargando Whisper %s para STT de consultas — device: cpu | cache: %s",
        settings.WHISPER_QUERY_MODEL,
        settings.WHISPER_MODEL_DIR,
    )
    try:
        from faster_whisper import WhisperModel
        _query_model = WhisperModel(
            model_size_or_path=settings.WHISPER_QUERY_MODEL,   # "tiny"
            device="cpu",
            compute_type="int8",       # cuantización int8 en CPU: más rápido y menos RAM
            download_root=settings.WHISPER_MODEL_DIR,
            cpu_threads=4,
            num_workers=1,
        )
        is_ready = True
        logger.info("✓ Whisper Tiny listo para STT de consultas")
    except Exception as exc:
        logger.error("Error cargando Whisper Tiny: %s", exc)
        is_ready = False


async def _get_ingest_model():
    """Carga Whisper Small de forma lazy (solo cuando se llama por primera vez)."""
    global _ingest_model
    if _ingest_model is not None:
        return _ingest_model
    logger.info(
        "Cargando Whisper %s para ingesta batch — device: cpu",
        settings.WHISPER_INGEST_MODEL,
    )
    from faster_whisper import WhisperModel
    _ingest_model = WhisperModel(
        model_size_or_path=settings.WHISPER_INGEST_MODEL,   # "small"
        device="cpu",
        compute_type="int8",
        download_root=settings.WHISPER_MODEL_DIR,
        cpu_threads=4,
        num_workers=1,
    )
    logger.info("✓ Whisper Small cargado")
    return _ingest_model


async def transcribe(audio_path: str) -> dict:
    """
    Transcribe audio WAV/WebM → texto (modo consulta — Whisper Tiny).

    Args:
        audio_path: ruta absoluta al archivo de audio (WAV o WebM, máx 15 s).

    Returns:
        {"text": str, "language": str}

    Raises:
        RuntimeError: si el STT no fue inicializado.
    """
    if not is_ready or _query_model is None:
        raise RuntimeError("STT no inicializado — llamar a stt.init() primero")

    # Ejecutar en un executor para no bloquear el event loop de FastAPI
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _transcribe_sync,
        _query_model,
        audio_path,
    )
    return result


async def transcribe_for_ingest(audio_path: str) -> list[dict]:
    """
    Transcribe audio de un video completo con timestamps (Whisper Small).
    Retorna segmentos con timestamps para el chunking jerárquico.

    Returns:
        List de {"text": str, "start": float, "end": float}
    """
    model = await _get_ingest_model()

    loop = asyncio.get_event_loop()
    segments = await loop.run_in_executor(
        None,
        _transcribe_with_timestamps_sync,
        model,
        audio_path,
    )
    return segments


def _transcribe_sync(model, audio_path: str) -> dict:
    """Transcripción síncrona para ejecutar en executor."""
    segments, info = model.transcribe(
        audio_path,
        language=None,                      # auto-detect español + quechua
        task="transcribe",
        beam_size=1,                        # beam_size=1 en Tiny: velocidad > precisión
        vad_filter=True,                    # Silences VAD: descarta silencios automáticamente
        condition_on_previous_text=False,   # evita alucinaciones en audios cortos
    )
    text = " ".join(seg.text.strip() for seg in segments)
    return {
        "text":     text.strip(),
        "language": info.language or "es",
    }


def _transcribe_with_timestamps_sync(model, audio_path: str) -> list[dict]:
    """Transcripción con timestamps para ingesta de video completo."""
    segments, info = model.transcribe(
        audio_path,
        language=None,
        task="transcribe",
        beam_size=5,            # más preciso para ingesta (no hay urgencia de tiempo real)
        vad_filter=True,
        word_timestamps=False,  # segmentos de oración son suficientes para chunking
        condition_on_previous_text=True,
    )
    result = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            result.append({
                "text":  text,
                "start": round(seg.start, 2),
                "end":   round(seg.end, 2),
            })
    return result


async def transcribe_bytes(audio_bytes: bytes, suffix: str = ".webm") -> dict:
    """
    Conveniencia: transcribe desde bytes (sin necesidad de guardar un archivo antes).
    Crea un archivo temporal, lo transcribe y lo elimina.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        return await transcribe(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

