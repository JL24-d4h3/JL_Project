"""
services/ingestion — Subpaquete de ingesta al índice vectorial.

Módulos:
  chunker.py             — Chunking jerárquico (summary / section / sentence)
  pdf_extractor.py       — Extracción de texto de PDFs y DOCX (+ OCR fallback)
  thumbnail_generator.py — Generación de miniaturas con FFmpeg / PyMuPDF
  pipeline.py            — Pipeline principal: orquesta todos los pasos de ingesta

Punto de entrada público:
  from ai_engine.services.ingestion.pipeline import ingest_content
"""
from ai_engine.services.ingestion.pipeline import ingest_content

__all__ = ["ingest_content"]
