"""
services/ingestion/pdf_extractor.py — Extracción de texto de PDFs y documentos.
GTR-PUCP CDN Educativa Offline

Estrategia de dos niveles:
  1. PyMuPDF (fitz)  — extracción directa de texto embebido (rápida, sin GPU)
  2. Tesseract OCR   — fallback si la página tiene texto escaneado (lento, solo si necesario)

Ver docs/ai-search-engine-plan.md §9.1 para el diseño.
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Umbral de caracteres por página para decidir si usar OCR
OCR_THRESHOLD = 50   # Si la página tiene < 50 chars de texto embebido → OCR
OCR_LANG      = "spa"   # Idioma Tesseract (español)


async def extract_text_from_pdf(file_path: str) -> str:
    """
    Extrae texto de un PDF usando PyMuPDF con fallback a OCR por Tesseract.

    Args:
        file_path: Ruta absoluta al PDF.

    Returns:
        Texto completo del documento (todas las páginas concatenadas).
        Cadena vacía si no se puede extraer texto.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_sync, file_path)


def _extract_sync(file_path: str) -> str:
    """Versión síncrona — se ejecuta en un executor para no bloquear el event loop."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF no disponible — no se puede extraer texto de PDF")
        return ""

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("No se puede abrir el PDF %s: %s", file_path, exc)
        return ""

    pages_text: list[str] = []
    ocr_pages = 0

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        if len(text) >= OCR_THRESHOLD:
            # Texto embebido suficiente — usar directamente
            pages_text.append(text)
        else:
            # Página escaneada o sin texto — intentar OCR
            ocr_text = _ocr_page(page, page_num)
            if ocr_text:
                pages_text.append(ocr_text)
                ocr_pages += 1
            else:
                # Si OCR tampoco produce texto, agregar lo que haya (puede ser nada)
                if text:
                    pages_text.append(text)

    doc.close()

    combined = "\n\n".join(pages_text)
    logger.debug(
        "Extracción PDF %s: %d páginas, %d con OCR, %d chars totales",
        Path(file_path).name, len(pages_text), ocr_pages, len(combined)
    )
    return combined


def _ocr_page(page, page_num: int) -> str:
    """
    OCR de una página con Tesseract a través de pytesseract.
    Renderiza la página a imagen y luego aplica OCR.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Renderizar página como imagen (150 DPI es suficiente para Tesseract)
        mat = page.get_pixmap(dpi=150)
        img_bytes = mat.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))

        text = pytesseract.image_to_string(img, lang=OCR_LANG)
        text = text.strip()
        if text:
            logger.debug("OCR página %d: %d chars extraídos", page_num, len(text))
        return text
    except ImportError:
        logger.debug("pytesseract/PIL no disponibles — sin OCR para página %d", page_num)
        return ""
    except Exception as exc:
        logger.warning("Error OCR página %d: %s", page_num, exc)
        return ""


async def extract_text_from_docx(file_path: str) -> str:
    """
    Extrae texto de un archivo DOCX con python-docx.
    También acepta ODT si se usa python-docx con soporte extendido o LibreOffice.

    Args:
        file_path: Ruta absoluta al archivo .docx.

    Returns:
        Texto completo del documento.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_docx_sync, file_path)


def _extract_docx_sync(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        logger.debug(
            "Extracción DOCX %s: %d párrafos, %d chars",
            Path(file_path).name, len(paragraphs), len(text)
        )
        return text
    except ImportError:
        logger.warning("python-docx no disponible — no se puede extraer DOCX")
        return ""
    except Exception as exc:
        logger.error("Error extrayendo DOCX %s: %s", file_path, exc)
        return ""


async def extract_text(file_path: str, mime_type: str = "") -> str:
    """
    Punto de entrada unificado — detecta el tipo por extensión o mime_type.

    Args:
        file_path: Ruta absoluta al archivo.
        mime_type: MIME type opcional para distinguir formatos sin extensión clara.

    Returns:
        Texto extraído o cadena vacía.
    """
    path = Path(file_path)
    ext  = path.suffix.lower()

    if ext == ".pdf" or "pdf" in mime_type:
        return await extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc") or "word" in mime_type or "docx" in mime_type:
        return await extract_text_from_docx(file_path)
    elif ext in (".txt", ".md", ".rst", ".csv"):
        # Texto plano — leer directamente
        try:
            return path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            logger.error("Error leyendo texto plano %s: %s", file_path, exc)
            return ""
    else:
        logger.warning("Tipo no soportado para extracción de texto: ext=%s mime=%s", ext, mime_type)
        return ""
