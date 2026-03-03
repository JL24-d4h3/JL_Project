"""
services/ingestion/chunker.py — Chunking jerárquico de texto para indexación vectorial.
GTR-PUCP CDN Educativa Offline

Produce tres niveles de chunks por documento:
  SUMMARY  (≤ 256 tokens)  — representación completa; para ranking inicial
  SECTION  (≤ 512 tokens, overlap 64) — párrafos/fragmentos; para contexto RAG
  SENTENCE (≤ 128 tokens)  — oraciones individuales; para grounding y snippets

Ver docs/ai-search-engine-plan.md §8.3 para el diseño completo.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Límites en "tokens" estimados (1 token ≈ 4 caracteres en español)
CHARS_PER_TOKEN = 4
SUMMARY_MAX_TOKENS  = 256
SECTION_MAX_TOKENS  = 512
SECTION_OVERLAP_TOKENS = 64
SENTENCE_MAX_TOKENS = 128


@dataclass
class TextChunk:
    text:            str
    chunk_type:      str            # "summary" | "section" | "sentence"
    chunk_index:     int
    total_chunks:    int            = 0   # se rellena después de crear todos los chunks
    timestamp_start: Optional[float] = None
    timestamp_end:   Optional[float] = None
    source_type:     str            = "text"   # "transcript" | "pdf_text" | "pdf_ocr" | "description"


def _tok(text: str) -> int:
    """Estimación rápida de tokens sin cargar un tokenizer completo."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_sentences(text: str) -> list[str]:
    """División por oraciones con soporte para abreviaciones comunes en español."""
    # Separar por punto/exclamación/interrogación seguido de espacio y mayúscula
    pattern = r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑÜ"\'])'
    parts = re.split(pattern, text.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text: str) -> list[str]:
    """División por párrafos (doble salto de línea) o por salto simple si no hay dobles."""
    paras = re.split(r'\n\s*\n', text)
    if len(paras) <= 1:
        # Sin párrafos marcados: dividir por líneas simples
        paras = text.split('\n')
    return [p.strip() for p in paras if p.strip()]


def chunk_text(
    text: str,
    source_type: str = "text",
) -> list[TextChunk]:
    """
    Genera los tres niveles de chunks a partir de texto plano.

    Args:
        text:        Texto a chunkear (transcripción, PDF extraído, etc.)
        source_type: "transcript" | "pdf_text" | "pdf_ocr" | "description"

    Returns:
        Lista de TextChunk con los tres niveles jerárquicos.
    """
    if not text or not text.strip():
        return []

    chunks: list[TextChunk] = []
    idx = 0

    # ── 1. SUMMARY: los primeros SUMMARY_MAX_TOKENS del texto completo ────────
    summary_chars = SUMMARY_MAX_TOKENS * CHARS_PER_TOKEN
    summary_text  = text[:summary_chars].strip()
    if summary_text:
        chunks.append(TextChunk(
            text=summary_text,
            chunk_type="summary",
            chunk_index=idx,
            source_type=source_type,
        ))
        idx += 1

    # ── 2. SECTION: ventana deslizante con overlap ─────────────────────────────
    section_chars  = SECTION_MAX_TOKENS * CHARS_PER_TOKEN
    overlap_chars  = SECTION_OVERLAP_TOKENS * CHARS_PER_TOKEN
    step           = section_chars - overlap_chars
    pos = 0
    while pos < len(text):
        segment = text[pos: pos + section_chars].strip()
        if segment:
            chunks.append(TextChunk(
                text=segment,
                chunk_type="section",
                chunk_index=idx,
                source_type=source_type,
            ))
            idx += 1
        pos += step

    # ── 3. SENTENCE: oraciones individuales ───────────────────────────────────
    sentences = _split_sentences(text)
    for sent in sentences:
        if _tok(sent) <= SENTENCE_MAX_TOKENS and len(sent) > 20:
            chunks.append(TextChunk(
                text=sent,
                chunk_type="sentence",
                chunk_index=idx,
                source_type=source_type,
            ))
            idx += 1

    # Rellenar total_chunks ahora que sabemos cuántos son
    total = len(chunks)
    for c in chunks:
        c.total_chunks = total

    logger.debug(
        "chunk_text: %d chars → %d chunks (summary=%d, section=%d, sentence=%d)",
        len(text), total,
        sum(1 for c in chunks if c.chunk_type == "summary"),
        sum(1 for c in chunks if c.chunk_type == "section"),
        sum(1 for c in chunks if c.chunk_type == "sentence"),
    )
    return chunks


def chunk_transcript(
    segments: list[dict],
) -> list[TextChunk]:
    """
    Genera chunks a partir de los segmentos con timestamps de Whisper.

    Args:
        segments: Lista de {"text": str, "start": float, "end": float}
                  (los que retorna stt.transcribe_for_ingest)

    Returns:
        Lista de TextChunk con timestamps para deep links con ?t=seconds.
    """
    if not segments:
        return []

    chunks:   list[TextChunk] = []
    idx = 0

    # ── Summary: concatenar todos los segmentos ────────────────────────────────
    full_text = " ".join(s["text"].strip() for s in segments)
    summary_chars = SUMMARY_MAX_TOKENS * CHARS_PER_TOKEN
    chunks.append(TextChunk(
        text=full_text[:summary_chars].strip(),
        chunk_type="summary",
        chunk_index=idx,
        timestamp_start=segments[0]["start"],
        timestamp_end=segments[-1]["end"],
        source_type="transcript",
    ))
    idx += 1

    # ── Sections: ventana deslizante sobre los segmentos (no sobre caracteres) ──
    # Cada "section" agrupa N segmentos hasta alcanzar SECTION_MAX_TOKENS chars
    window:      list[dict] = []
    window_chars = 0
    section_chars = SECTION_MAX_TOKENS * CHARS_PER_TOKEN

    for i, seg in enumerate(segments):
        window.append(seg)
        window_chars += len(seg["text"])

        if window_chars >= section_chars or i == len(segments) - 1:
            section_text  = " ".join(s["text"].strip() for s in window)
            ts_start      = window[0]["start"]
            ts_end        = window[-1]["end"]
            chunks.append(TextChunk(
                text=section_text.strip(),
                chunk_type="section",
                chunk_index=idx,
                timestamp_start=ts_start,
                timestamp_end=ts_end,
                source_type="transcript",
            ))
            idx += 1
            # Overlap: conservar los últimos 2 segmentos en la siguiente ventana
            overlap_segs = window[-2:] if len(window) >= 2 else window[-1:]
            window       = overlap_segs
            window_chars = sum(len(s["text"]) for s in window)

    # ── Sentences: cada segmento de Whisper ya es aproximadamente una oración ──
    for seg in segments:
        text = seg["text"].strip()
        if text and _tok(text) <= SENTENCE_MAX_TOKENS and len(text) > 15:
            chunks.append(TextChunk(
                text=text,
                chunk_type="sentence",
                chunk_index=idx,
                timestamp_start=seg["start"],
                timestamp_end=seg["end"],
                source_type="transcript",
            ))
            idx += 1

    total = len(chunks)
    for c in chunks:
        c.total_chunks = total

    logger.debug(
        "chunk_transcript: %d segmentos → %d chunks", len(segments), total
    )
    return chunks
