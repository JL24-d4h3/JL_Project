"""
services/ingestion/thumbnail_generator.py — Generación de miniaturas para todos los tipos.
GTR-PUCP CDN Educativa Offline

- Video:    extrae frame al segundo 10 con FFmpeg → JPG 320×180
- PDF/Doc:  renderiza primera página con PyMuPDF → JPG 320×180
- Audio:    copia ícono genérico de categoría (no hay frame visual)

Ver docs/ai-search-engine-plan.md §9.2
"""
from __future__ import annotations
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from ai_engine.config import settings

logger = logging.getLogger(__name__)

THUMB_W = 320
THUMB_H = 180
STORAGE_PATH = Path(settings.STORAGE_PATH)
THUMBNAILS_DIR = STORAGE_PATH / "thumbnails"
STATIC_ICONS_DIR = Path(__file__).parent.parent.parent / "static" / "icons"


def _ensure_thumbnails_dir() -> None:
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


async def generate_thumbnail(
    content_id: str,
    content_type: str,
    file_path: str,
    category: str = "general",
) -> str:
    """
    Genera la miniatura para un contenido y la guarda en /storage/thumbnails/{content_id}.jpg.

    Args:
        content_id:   UUID del contenido (se usa como nombre del archivo de salida)
        content_type: "video" | "pdf" | "document" | "audio" | "image"
        file_path:    Ruta absoluta al archivo fuente
        category:     Categoría del contenido (para elegir ícono en audio)

    Returns:
        URL relativa de la miniatura: "/storage/thumbnails/{content_id}.jpg"
    """
    _ensure_thumbnails_dir()
    output = THUMBNAILS_DIR / f"{content_id}.jpg"

    # Si ya existe (generada por el CDN backend), reutilizar
    if output.exists():
        logger.debug("Thumbnail ya existe para %s — reutilizando", content_id)
        return f"/storage/thumbnails/{content_id}.jpg"

    loop = asyncio.get_event_loop()

    if content_type == "video":
        await loop.run_in_executor(None, _video_thumbnail, file_path, str(output))
    elif content_type in ("pdf", "document"):
        await loop.run_in_executor(None, _pdf_thumbnail, file_path, str(output))
    elif content_type == "audio":
        await loop.run_in_executor(None, _audio_thumbnail, category, str(output))
    elif content_type == "image":
        # Para imágenes se hace una versión reducida de la misma imagen
        await loop.run_in_executor(None, _image_thumbnail, file_path, str(output))
    else:
        # Tipo desconocido: copiar ícono genérico
        _copy_fallback_icon("general", str(output))

    if not output.exists():
        # Si la generación falló (FFmpeg/PyMuPDF no disponible), usar fallback
        logger.warning(
            "No se pudo generar thumbnail para %s (%s) — usando fallback",
            content_id, content_type
        )
        _copy_fallback_icon(category, str(output))

    return f"/storage/thumbnails/{content_id}.jpg"


def _video_thumbnail(file_path: str, output: str) -> None:
    """FFmpeg: extrae frame representativo al segundo 10."""
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-ss", "00:00:10",
        "-vframes", "1",
        "-vf", f"scale={THUMB_W}:{THUMB_H}:force_original_aspect_ratio=decrease,"
               f"pad={THUMB_W}:{THUMB_H}:(ow-iw)/2:(oh-ih)/2:black",
        "-q:v", "3",
        output,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            logger.warning("FFmpeg returncode %d para %s", result.returncode, file_path)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.error("Error generando thumbnail de video: %s", exc)


def _pdf_thumbnail(file_path: str, output: str) -> None:
    """PyMuPDF: renderiza la primera página como JPG 320×180."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page = doc[0]
        # Escalar al tamaño deseado manteniendo proporción
        scale_x = THUMB_W / page.rect.width
        scale_y = THUMB_H / page.rect.height
        mat = fitz.Matrix(min(scale_x, scale_y), min(scale_x, scale_y))
        pix = page.get_pixmap(matrix=mat)
        pix.save(output)
        doc.close()
    except ImportError:
        logger.warning("PyMuPDF no disponible — no se puede generar thumbnail de PDF")
    except Exception as exc:
        logger.error("Error generando thumbnail de PDF: %s", exc)


def _audio_thumbnail(category: str, output: str) -> None:
    """Para audio: copia ícono estático de la categoría."""
    _copy_fallback_icon(category, output)


def _image_thumbnail(file_path: str, output: str) -> None:
    """Para imágenes: redimensiona a 320×180 con FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-vf", f"scale={THUMB_W}:{THUMB_H}:force_original_aspect_ratio=decrease,"
               f"pad={THUMB_W}:{THUMB_H}:(ow-iw)/2:(oh-ih)/2:white",
        "-q:v", "3",
        output,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=15, check=True)
    except Exception as exc:
        logger.warning("Error generando thumbnail de imagen: %s", exc)


def _copy_fallback_icon(category: str, output: str) -> None:
    """Copia el ícono genérico de una categoría como miniatura."""
    # Intentar ícono de la categoría, luego el genérico
    for name in (f"audio_{category}.jpg", "audio_general.jpg", "placeholder.jpg"):
        icon = STATIC_ICONS_DIR / name
        if icon.exists():
            shutil.copy(str(icon), output)
            return
    # Si no hay ningún ícono disponible, crear un JPG negro mínimo con FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=black:size={THUMB_W}x{THUMB_H}:rate=1",
        "-vframes", "1", output,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass  # Mejor que nada: el archivo no se crea y la URL retorna 404
