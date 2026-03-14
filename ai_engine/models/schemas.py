"""
models/schemas.py — Tipos Pydantic compartidos por todos los routers y servicios.
GTR-PUCP CDN Educativa Offline
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContentType(str, Enum):
    VIDEO    = "video"
    PDF      = "pdf"
    AUDIO    = "audio"
    DOCUMENT = "document"
    IMAGE    = "image"


class RoutingLevel(str, Enum):
    L1_CDN_STRICT      = "L1_CDN_STRICT"
    L2_CDN_AUGMENTED   = "L2_CDN_AUGMENTED"
    L3_GENERAL         = "L3_GENERAL_KNOWLEDGE"
    L4_CLARIFICATION   = "L4_CLARIFICATION"


class ThermalProfile(str, Enum):
    NOMINAL  = "nominal"
    WARM     = "warm"
    HOT      = "hot"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------

class SearchContext(BaseModel):
    user_role:        Optional[str] = None
    current_category: Optional[str] = None
    user_id:          Optional[str] = None
    input_mode:       str = "text"
    detected_language: Optional[str] = None


class SearchOptions(BaseModel):
    streaming:    bool = True
    max_sources:  int  = 5
    language:     str  = "auto"


class SearchRequest(BaseModel):
    query:   str             = Field(..., min_length=1, max_length=1024)
    context: SearchContext   = Field(default_factory=SearchContext)
    options: SearchOptions   = Field(default_factory=SearchOptions)


# ---------------------------------------------------------------------------
# Rich Snippets (tarjetas de resultado)
# ---------------------------------------------------------------------------

class RichSnippet(BaseModel):
    rank:             int
    content_id:       str
    content_type:     ContentType
    title:            str
    category:         Optional[str]        = None
    snippet:          str
    upload_date:      str
    thumbnail_url:    str
    viewer_url:       str
    deep_link:        str
    requires_auth:    bool                 = False
    relevance_score:  float
    duration_seconds: Optional[int]        = None   # video / audio
    page_count:       Optional[int]        = None   # pdf / document


# ---------------------------------------------------------------------------
# Grounding / Anti-alucinación
# ---------------------------------------------------------------------------

class GroundingScore(BaseModel):
    sentence: str
    score:    float


class GroundingReport(BaseModel):
    coverage_score:   float
    is_grounded:      bool
    unverified:       list[GroundingScore] = []
    source_mode:      RoutingLevel         = RoutingLevel.L2_CDN_AUGMENTED


# ---------------------------------------------------------------------------
# Respuesta de búsqueda
# ---------------------------------------------------------------------------

class RoutingDecision(BaseModel):
    level:              RoutingLevel
    confidence:         float
    retrieval_time_ms:  int = 0
    generation_time_ms: int = 0


class AIOverviewResponse(BaseModel):
    text:              str
    grounding:         GroundingReport
    language_detected: str = "es"


class UIHints(BaseModel):
    show_sources_panel:   bool       = True
    highlight_timestamps: bool       = True
    show_auth_warning:    bool       = False
    suggested_queries:    list[str]  = []


class SearchResponse(BaseModel):
    request_id:        Optional[str]       = None
    query_transcribed: Optional[str]       = None   # solo en voice-search
    routing:           RoutingDecision
    ai_overview:       AIOverviewResponse
    cdn_results:       list[RichSnippet]
    ui_hints:          UIHints             = Field(default_factory=UIHints)


# ---------------------------------------------------------------------------
# Ingesta
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    content_id: str = Field(..., description="UUID del registro en PostgreSQL")


class IngestStatus(BaseModel):
    content_id: str
    status:     str   # "queued" | "processing" | "done" | "error"
    message:    str   = ""


# ---------------------------------------------------------------------------
# Chunk vectorial (interno — no se expone directamente en la API)
# ---------------------------------------------------------------------------

class VectorChunk(BaseModel):
    text:            str
    content_id:      str
    content_type:    ContentType
    title:           str
    category:        Optional[str]   = None
    chunk_index:     int             = 0
    total_chunks:    int             = 1
    source_type:     str             = "text"   # "transcript"|"pdf_text"|"pdf_ocr"|"description"
    timestamp_start: Optional[float] = None     # segundos (video/audio)
    timestamp_end:   Optional[float] = None
    viewer_url:      str             = ""
    thumbnail_url:   str             = ""
    upload_date:     str             = ""
    language:        str             = "es"
    chunk_type:      str             = "section"  # "summary"|"section"|"sentence"
