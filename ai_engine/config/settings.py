"""
config/settings.py — Configuración Unificada Multi-plataforma
GTR-PUCP CDN Educativa Offline

Cambiar de plataforma = cambiar AI_PLATFORM en el .env activo:
  AI_PLATFORM=laptop          → Desarrollo en laptop/PC (sin GPU CUDA)
  AI_PLATFORM=orin_nano_8gb   → Fase 1 (Jetson Orin Nano 8GB)
  AI_PLATFORM=orin_nx_16gb    → Fase 2 (Jetson Orin NX 16GB)   ← plan original
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env — primero el de la raíz del proyecto, luego el de ai_engine/
# (el de raíz tiene AI_PLATFORM=laptop para desarrollo)
_root_env = Path(__file__).parent.parent.parent / ".env"
if _root_env.exists():
    load_dotenv(_root_env)
_ai_env = Path(__file__).parent.parent / ".env"
if _ai_env.exists():
    load_dotenv(_ai_env, override=False)  # no sobreescribir lo que ya cargó root

PLATFORM = os.getenv("AI_PLATFORM", "orin_nx_16gb")

# ---------------------------------------------------------------------------
# Parámetros por plataforma
# ---------------------------------------------------------------------------
_CONFIGS: dict = {
    # ─── Desarrollo en laptop / PC (sin GPU CUDA) ─────────────────────────
    "laptop": {
        "LLM_BACKEND":       "hf",
        "DRAFT_MODEL_DIR":   os.getenv("DRAFT_MODEL_DIR", ""),
        "TARGET_MODEL_DIR":  os.getenv("TARGET_MODEL_DIR",
                                       "/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct"),
        "SPECULATIVE":        False,
        "SPECULATIVE_GAMMA":  0,
        "MAX_CONTEXT":        2048,
        "MAX_GEN":            1024,
        "EMBED_DEVICE":      "cpu",   # no CUDA en laptop
        "HYDE":               False,  # HyDE lento sin GPU
        "CROSS_ENCODER":      False,  # reranker lento en CPU
        "TOP_K":              30,
        "TOP_K_FINAL":        15,     # hasta 15 resultados en búsqueda
        "CHROMA_MAX":         50_000,
        "INGESTION_MODE":    "realtime",
        "THERMAL_PROFILE":   "laptop",
    },
    "orin_nano_8gb": {
        # LLM
        "LLM_BACKEND":       "tensorrt_llm",
        "DRAFT_MODEL_DIR":   os.getenv("DRAFT_MODEL_DIR", "/mnt/ssd/trt_engines/llama32-1b-int4"),
        "TARGET_MODEL_DIR":  os.getenv("TARGET_MODEL_DIR", "/mnt/ssd/trt_engines/phi35-mini-int4"),
        "SPECULATIVE":        True,
        "SPECULATIVE_GAMMA":  4,
        "MAX_CONTEXT":        1024,
        "MAX_GEN":            256,
        # Retrieval
        "EMBED_DEVICE":      "cuda",
        "HYDE":               True,
        "CROSS_ENCODER":      True,
        "TOP_K":              15,
        "TOP_K_FINAL":        5,
        "CHROMA_MAX":         30_000,
        # Ingesta
        "INGESTION_MODE":    "semaphore_cautious",
        # Térmico
        "THERMAL_PROFILE":   "orin_nano_8gb",
    },
    "orin_nx_8gb": {
        "LLM_BACKEND":       "tensorrt_llm",
        "DRAFT_MODEL_DIR":   os.getenv("DRAFT_MODEL_DIR", "/mnt/ssd/trt_engines/llama32-1b-int4"),
        "TARGET_MODEL_DIR":  os.getenv("TARGET_MODEL_DIR", "/mnt/ssd/trt_engines/phi35-mini-int4"),
        "SPECULATIVE":        True,
        "SPECULATIVE_GAMMA":  4,
        "MAX_CONTEXT":        1024,
        "MAX_GEN":            256,
        "EMBED_DEVICE":      "cuda",
        "HYDE":               True,
        "CROSS_ENCODER":      True,
        "TOP_K":              20,
        "TOP_K_FINAL":        5,
        "CHROMA_MAX":         50_000,
        "INGESTION_MODE":    "realtime",
        "THERMAL_PROFILE":   "orin_nx_8gb",
    },
    "orin_nx_16gb": {                          # ─── PLAN ORIGINAL ───
        "LLM_BACKEND":       "tensorrt_llm",
        "DRAFT_MODEL_DIR":   os.getenv("DRAFT_MODEL_DIR", "/mnt/ssd/trt_engines/llama32-1b-int4"),
        "TARGET_MODEL_DIR":  os.getenv("TARGET_MODEL_DIR", "/mnt/ssd/trt_engines/llama31-8b-int4"),
        "SPECULATIVE":        True,
        "SPECULATIVE_GAMMA":  5,
        "MAX_CONTEXT":        1792,
        "MAX_GEN":            512,
        "EMBED_DEVICE":      "cuda",
        "HYDE":               True,
        "CROSS_ENCODER":      True,
        "TOP_K":              20,
        "TOP_K_FINAL":        5,
        "CHROMA_MAX":         100_000,
        "INGESTION_MODE":    "realtime",
        "THERMAL_PROFILE":   "orin_nx_16gb",
    },
    "agx_orin_32gb": {
        "LLM_BACKEND":       "tensorrt_llm",
        "DRAFT_MODEL_DIR":   os.getenv("DRAFT_MODEL_DIR", "/mnt/ssd/trt_engines/llama32-1b-int4"),
        "TARGET_MODEL_DIR":  os.getenv("TARGET_MODEL_DIR", "/mnt/ssd/trt_engines/llama31-13b-int4"),
        "SPECULATIVE":        True,
        "SPECULATIVE_GAMMA":  5,
        "MAX_CONTEXT":        3584,
        "MAX_GEN":            1024,
        "EMBED_DEVICE":      "cuda",
        "HYDE":               True,
        "CROSS_ENCODER":      True,
        "TOP_K":              30,
        "TOP_K_FINAL":        8,
        "CHROMA_MAX":         200_000,
        "INGESTION_MODE":    "realtime",
        "THERMAL_PROFILE":   "agx_orin_32gb",
    },
}

if PLATFORM not in _CONFIGS:
    raise ValueError(
        f"AI_PLATFORM='{PLATFORM}' no reconocida. "
        f"Opciones: {list(_CONFIGS.keys())}"
    )

_cfg = _CONFIGS[PLATFORM]

# ---------------------------------------------------------------------------
# Exportar como constantes (import directo desde otros módulos)
# ---------------------------------------------------------------------------
LLM_BACKEND            = _cfg["LLM_BACKEND"]
DRAFT_MODEL_DIR        = _cfg["DRAFT_MODEL_DIR"]
TARGET_MODEL_DIR       = _cfg["TARGET_MODEL_DIR"]
SPECULATIVE_DECODING   = _cfg["SPECULATIVE"]
SPECULATIVE_GAMMA      = _cfg.get("SPECULATIVE_GAMMA", 0)
MAX_CONTEXT_TOKENS     = int(os.getenv("MAX_CONTEXT_TOKENS",  str(_cfg["MAX_CONTEXT"])))
MAX_GENERATION_TOKENS  = int(os.getenv("MAX_GENERATION_TOKENS", str(_cfg["MAX_GEN"])))
EMBEDDING_DEVICE       = _cfg["EMBED_DEVICE"]
HYDE_ENABLED           = _cfg["HYDE"]
CROSS_ENCODER_ENABLED  = _cfg["CROSS_ENCODER"]
TOP_K_RETRIEVAL        = _cfg["TOP_K"]
TOP_K_FINAL            = _cfg["TOP_K_FINAL"]
CHROMA_MAX_CHUNKS      = _cfg["CHROMA_MAX"]
INGESTION_MODE         = _cfg["INGESTION_MODE"]
THERMAL_PROFILE        = _cfg["THERMAL_PROFILE"]

# ---------------------------------------------------------------------------
# Rutas comunes (desde .env o valores por defecto)
# ---------------------------------------------------------------------------
WHISPER_MODEL_DIR      = os.getenv("WHISPER_MODEL_DIR",  "/mnt/ssd/models/whisper")
EMBED_MODEL_DIR        = os.getenv("EMBED_MODEL_DIR",    "/mnt/ssd/models/embeddings")
CHROMADB_PATH          = os.getenv("CHROMADB_PATH",      "/mnt/ssd/chromadb_data")
STORAGE_PATH           = os.getenv("STORAGE_PATH",       "/mnt/ssd/CDN/storage")
CDN_BACKEND_URL        = os.getenv("CDN_BACKEND_URL",    "http://localhost:3000")
AI_ENGINE_HOST         = os.getenv("AI_ENGINE_HOST",     "0.0.0.0")
AI_ENGINE_PORT         = int(os.getenv("AI_ENGINE_PORT", "8000"))

# ---------------------------------------------------------------------------
# Modelos fijos (no dependen de plataforma)
# ---------------------------------------------------------------------------
EMBED_MODEL_NAME       = "intfloat/multilingual-e5-small"
CROSS_ENCODER_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"
WHISPER_QUERY_MODEL    = "tiny"    # STT de consultas en tiempo real
WHISPER_INGEST_MODEL   = "small"   # STT de videos en ingesta batch

# ---------------------------------------------------------------------------
# Impresión de config activa al importar (visible en logs de arranque)
# ---------------------------------------------------------------------------
import logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)
_log.info(
    "AI Platform: %s | LLM: %s→%s | Speculative: %s γ=%d | CHROMA_MAX: %d | Ingesta: %s",
    PLATFORM,
    Path(DRAFT_MODEL_DIR).name if DRAFT_MODEL_DIR else "—",
    Path(TARGET_MODEL_DIR).name,
    SPECULATIVE_DECODING,
    SPECULATIVE_GAMMA,
    CHROMA_MAX_CHUNKS,
    INGESTION_MODE,
)
