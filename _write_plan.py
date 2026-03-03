import pathlib

TARGET = pathlib.Path("/home/jleon/2026/PUCP/GTR/CDN/docs/ai-search-engine-plan.md")

CONTENT = r'''# Plan de Implementación: Motor de Búsqueda IA para CDN Offline

> **Contexto**: Proyecto GTR-PUCP — CDN educativa offline para escuelas rurales del Perú.
> **Hardware objetivo**: NVIDIA Jetson Orin NX (16 GB unified memory, 1024 CUDA cores, 32 TOPS INT8)
> **Fecha de revisión**: Febrero 2026
> **Stack base**: Node.js/Express/PostgreSQL/Redis (existente) + FastAPI/Python (nuevo, en Jetson)

---

## Índice

1. [Visión del Sistema y Principios](#1-visión-del-sistema-y-principios)
2. [Soporte Multiplataforma](#2-soporte-multiplataforma)
3. [Arquitectura General de la Pipeline IA](#3-arquitectura-general-de-la-pipeline-ia)
4. [Entrada por Voz — STT-Only (Whisper)](#4-entrada-por-voz--stt-only-whisper)
5. [Niveles de Inteligencia (Triaje Adaptativo)](#5-niveles-de-inteligencia-triaje-adaptativo)
6. [Estrategia de Inferencia en Edge (Jetson Orin NX)](#6-estrategia-de-inferencia-en-edge-jetson-orin-nx)
7. [Gestión de Memoria y Prevención de OOM](#7-gestión-de-memoria-y-prevención-de-oom)
8. [Arquitectura de Datos Vectoriales](#8-arquitectura-de-datos-vectoriales)
9. [Pipeline de Ingesta Multi-modal](#9-pipeline-de-ingesta-multi-modal)
10. [Motor de Recuperación Híbrida (HyDE + BM25 + Vector)](#10-motor-de-recuperación-híbrida-hyde--bm25--vector)
11. [Mecanismo Anti-Alucinación (Grounding Estricto)](#11-mecanismo-anti-alucinación-grounding-estricto)
12. [Contrato de API: Rich Snippets y Streaming SSE](#12-contrato-de-api-rich-snippets-y-streaming-sse)
13. [Visor de Contenido y Flujo de Autenticación](#13-visor-de-contenido-y-flujo-de-autenticación)
14. [Integración con el CDN Existente (Node.js → FastAPI)](#14-integración-con-el-cdn-existente-nodejs--fastapi)
15. [Consideraciones Críticas de Hardware](#15-consideraciones-críticas-de-hardware)
16. [Gestión Térmica Adaptativa](#16-gestión-térmica-adaptativa)
17. [Limitaciones Conocidas y Mitigaciones](#17-limitaciones-conocidas-y-mitigaciones)
18. [Observabilidad y Métricas](#18-observabilidad-y-métricas)
19. [Plan de Fases de Implementación](#19-plan-de-fases-de-implementación)
20. [Estructura de Directorios y Dependencias](#20-estructura-de-directorios-y-dependencias)

---

## 1. Visión del Sistema y Principios

### 1.1 Qué hace este sistema

Añade una capa de inteligencia artificial **completamente offline** al CDN educativo. El usuario hace una pregunta (por texto o por voz) y recibe:

1. Un **texto de visión general** generado por la IA, explicando el tema consultado.
2. Una **lista de tarjetas enriquecidas** (Rich Snippets) con los contenidos de la CDN relacionados — cada tarjeta incluye thumbnail, título, fecha, snippet y enlace directo al visor de la plataforma.

**La IA no genera videos, audios ni documentos.** Su único output es texto estructurado + metadatos de los contenidos encontrados. La generación de multimedia no es parte del buscador y no está planificada para esta fase.

### 1.2 Principios de Diseño

| Principio | Implementación |
|-----------|----------------|
| **Offline-First absoluto** | Cero llamadas a Internet en inferencia, embeddings, STT o retrieval |
| **Salida solo texto** | La IA devuelve JSON con texto + metadatos. Nunca genera archivos multimedia |
| **Visor propio de plataforma** | Los resultados enlazan a rutas del visor interno (`/viewer/*`), no a descargas directas |
| **Autenticación en CDN, no en IA** | El AI Engine no valida permisos; devuelve rutas. El CDN backend las protege |
| **Multiplataforma** | La API es agnóstica: sirve igual a la web, app móvil y app de escritorio |
| **Sin degradación del CDN** | FastAPI :8000 es proceso separado; fallo del AI Engine no afecta streaming/upload |
| **Latencia tolerable** | < 1 s para STT de consulta de voz; < 3 s para primer token de respuesta |
| **Trazabilidad** | Cada afirmación del overview está anclada a chunks reales de la CDN |
| **Gestión proactiva de memoria** | Ingesta y inferencia nunca corren simultáneamente sin control de semáforo |

### 1.3 Tabla de Mejoras sobre Versiones Anteriores

| Aspecto | Versión anterior | Esta versión |
|---------|-----------------|--------------|
| Entrada | Solo texto | Texto + voz (STT-Only, sin TTS) |
| Output | Texto + links | Rich Snippets: thumbnail, snippet real, fecha, deep link al visor |
| Navegación de resultados | URL directa a archivo | Ruta al visor de la plataforma (`/viewer/video/{id}?t=142`) |
| Autenticación | No especificada | Auth en CDN backend; AI devuelve `requires_auth` flag; frontend maneja 401 |
| Enrutamiento | Binario (L1/L2) | Triaje de 4 niveles con RCS continuo |
| Retrieval | RAG básico | HyDE + BM25 + Vector + Cross-Encoder re-ranker |
| Inferencia | Llama 3 genérico | Speculative decoding: draft 1B + target 8B (2.8× speed-up) |
| Memoria | 16.0 GB exactos (riesgo OOM) | 14.5 GB working set + 1.5 GB buffer; semáforo ingesta/inferencia |
| Quechua | Detección sin aviso | Soporte parcial documentado; fallback a español con advertencia visible |
| Thumbnails | Solo videos | Videos (FFmpeg frame s=10), PDFs (primera página JPG), audio (ícono categoría) |
| SSE Proxy | Sin configuración de buffering | `X-Accel-Buffering: no` + gzip desactivado en ruta SSE |
| Térmico | Gestor opcional | Gestor **crítico obligatorio** + requerimiento de disipador activo en hardware |
| Cuantización AWQ | Dataset genérico | Dataset de calibración educativo peruano |
| Plataformas | Web únicamente | Web + App Móvil (React Native/PWA) + Desktop (Electron/PWA) |

---

## 2. Soporte Multiplataforma

### 2.1 Clientes del Sistema

El backend (Express :3000 + FastAPI :8000) es completamente agnóstico de plataforma. Devuelve JSON y SSE, que cualquier cliente puede consumir.

```
┌─────────────────────────────────────────────────────────┐
│                  CLIENTES (todos sin Internet)           │
│                                                          │
│  [Web Browser]        React SPA en :5173                 │
│  [App Móvil]          React Native / PWA                 │
│  [App Escritorio]     Electron / PWA instalable          │
│                                                          │
│  Todos se conectan al mismo:                             │
│  API:    http://cdn-local:3000/api/                      │
│  Assets: http://cdn-local:3000/storage/                  │
│  Visor:  http://cdn-local:5173/viewer/                   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Entrada de Voz en Móvil

Los dispositivos móviles tienen micrófono integrado. El flujo de búsqueda por voz usa la **Web Audio API** (en browser/PWA) o la **API nativa de audio** (en React Native) para capturar el audio y enviarlo al endpoint STT del AI Engine. El resultado es idéntico a una búsqueda por texto.

### 2.3 Visor de Contenido Multiplataforma

Cada plataforma implementa su propio visor usando las mismas rutas de API:

| Contenido | Ruta del visor | Implementación |
|-----------|----------------|----------------|
| Video | `/viewer/video/{id}?t={segundos}` | Video.js o `<video>` nativo, seek automático al timestamp |
| PDF / Documento | `/viewer/document/{id}?page={n}` | PDF.js embebido; no entrega el PDF directo al browser |
| Audio | `/viewer/audio/{id}?t={segundos}` | `<audio>` nativo con seek |

Desde el visor, si el usuario tiene permiso `can_download`, se habilita el botón de descarga.
El visor es la única puerta de entrada al contenido desde la búsqueda IA — nunca se entregan rutas de descarga directa en los resultados.

---

## 3. Arquitectura General de la Pipeline IA

```
╔══════════════════════════════════════════════════════════════════════════════╗
║           CLIENTES (Web / Móvil / Escritorio)                                ║
║                                                                              ║
║  [Texto en barra de búsqueda]    [Botón micrófono → audio blob]              ║
╚═════════════════════════╦═══════════════════════╦════════════════════════════╝
                          ║ POST /api/ai/search    ║ POST /api/ai/voice-search
                          ╚═══════════════════════╩════════════════════════════╗
                                                                               ║
╔═════════════════════════════════════════════════════════════════════════════╗ ║
║       CDN BACKEND — Node.js/Express :3000  [EXISTENTE + rutas nuevas]      ║ ║
║  JWT auth middleware → proxy → AI Engine                                    ║ ║
╚════════════════════════════════════════════════╦════════════════════════════╝ ║
                                                 ║ forward interno              ║
                                                 ▼                             ║
╔════════════════════════════════════════════════════════════════════════════╗  ║
║         AI ENGINE — FastAPI :8000 — NVIDIA Jetson Orin NX [NUEVO]         ║  ║
║                                                                            ║  ║
║  ┌─────────────────────────────────────────────────────────────────────┐  ║  ║
║  │ STT Gate (solo en /voice-search)                                    │  ║  ║
║  │  audio blob → Whisper Tiny CPU → query text                         │  ║  ║
║  └──────────────────────────────┬──────────────────────────────────────┘  ║  ║
║                                 │ query text (común a texto y voz)         ║  ║
║  ┌──────────────────────────────▼──────────────────────────────────────┐  ║  ║
║  │ Adaptive Intent Router                                              │  ║  ║
║  │  embed fast (e5-small) → RCS Score → Triaje 4 niveles               │  ║  ║
║  └──────────┬───────────────────┬──────────────┬──────────────┬────────┘  ║  ║
║             │L1                 │L2            │L3            │L4         ║  ║
║  ┌──────────▼───────────────────▼──────────────▼───────┐     │           ║  ║
║  │            Hybrid Retriever                         │     │           ║  ║
║  │  ChromaDB + BM25 + PG FTS                           │     │           ║  ║
║  │  → HyDE → RRF Fusion → Cross-Encoder Top-5         │     │           ║  ║
║  └───────────────────────┬─────────────────────────────┘     │Clarif.    ║  ║
║                          │ chunks + metadata                  │           ║  ║
║  ┌───────────────────────▼───────────────────────────────────▼───────┐  ║  ║
║  │ Speculative Decoder (TensorRT-LLM INT4 AWQ)                       │  ║  ║
║  │  Draft 1B propone γ=5 tokens → Target 8B verifica → 2.8× speedup  │  ║  ║
║  └──────────────────────────────────────┬──────────────────────────────┘  ║  ║
║                                         │ texto generado                   ║  ║
║  ┌──────────────────────────────────────▼──────────────────────────────┐  ║  ║
║  │ Grounding Verifier                                                  │  ║  ║
║  │  Coverage Score por oración → bloquea si < 0.45 en L1              │  ║  ║
║  └──────────────────────────────────────┬──────────────────────────────┘  ║  ║
║                                         │ SSE chunks                       ║  ║
╚═════════════════════════════════════════╪══════════════════════════════════╝  ║
                                          ║ SSE / JSON                          ║
              ╔═══════════════════════════╝                                     ║
              ║                                                                  ║
╔═════════════▼════════════════════════════════════════════════════════════════╗ ║
║  RESPUESTA FINAL (agnóstica de plataforma)                                   ║ ║
║                                                                              ║ ║
║  query_transcribed: "Explícame qué es OSPF..."  ← solo en voice-search      ║ ║
║  ai_overview { text, grounding, language_detected }                          ║ ║
║  cdn_results [ { thumbnail_url, title, snippet, upload_date,                 ║ ║
║                  viewer_url, deep_link, requires_auth, relevance_score } ]   ║ ║
║  ui_hints { suggested_queries }                                              ║ ║
╚══════════════════════════════════════════════════════════════════════════════╝ ╝
```

---

## 4. Entrada por Voz — STT-Only (Whisper)

### 4.1 Decisión de Diseño: STT Únicamente

El sistema acepta voz como **modo de entrada** a la búsqueda. La IA **no genera voz ni audio** como salida. El pipeline es:

```
Micrófono → audio WAV/WebM → STT (Whisper Tiny) → texto → pipeline de búsqueda normal
```

La razón es doble: generar texto tarda ~8 s en la Jetson. Añadir TTS consumiría
~800 MB adicionales de un modelo de síntesis de voz y otros ~3-5 s de latencia, sin que el
presupuesto de memoria lo permita. La salida es y será siempre texto estructurado.

### 4.2 Endpoint de Búsqueda por Voz

```http
POST http://cdn-local:3000/api/ai/voice-search
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data

audio: <blob WAV o WebM, mono 16kHz, máx 15 segundos>
context[user_role]: student
context[current_category]: redes
```

Respuesta: idéntica a `/api/ai/search`, con el campo adicional:

```json
"query_transcribed": "Explícame qué es el protocolo OSPF y en qué capa del modelo TCP/IP trabaja"
```

### 4.3 Implementación STT en FastAPI

```python
# ai_engine/routers/voice_search.py
from fastapi import APIRouter, UploadFile, File, Form
import whisper, tempfile, json

router = APIRouter()

# Whisper Tiny: 39 MB, corre SOLO en CPU (no ocupa VRAM de los LLMs)
# Latencia Real en Jetson Orin NX CPU: ~0.8 s para consulta de 10 s
stt_model = whisper.load_model("tiny", device="cpu")

@router.post("/voice-search")
async def voice_search(
    audio: UploadFile = File(...),
    context: str = Form(default="{}")
):
    audio_bytes = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        result = stt_model.transcribe(
            tmp.name,
            language=None,   # auto-detect: detecta español y quechua
            fp16=False,      # CPU no soporta fp16
            task="transcribe",
            condition_on_previous_text=False
        )

    query_text    = result["text"].strip()
    detected_lang = result.get("language", "es")

    search_payload = {
        "query":  query_text,
        "context": json.loads(context),
        "meta":   {"input_mode": "voice", "detected_language": detected_lang}
    }
    return await search_handler(search_payload)
```

### 4.4 Consideraciones de Audio por Plataforma

| Plataforma | API para captura | Formato enviado | Nota |
|---|---|---|---|
| Web / PWA | `MediaRecorder` API | WebM/Opus | Requiere `https` o `localhost` para acceso al micrófono |
| React Native | `expo-av` | WAV 16kHz mono | Sin restricción de protocolo |
| Electron | Node.js `mic` | WAV 16kHz mono | Acceso directo al dispositivo de audio |

**Restricción de longitud**: máximo 15 segundos por consulta. Suficiente para preguntas educativas.

### 4.5 Whisper para Consultas vs. Whisper para Ingesta

| Uso | Modelo | Dispositivo | Memoria | Concurrencia |
|---|---|---|---|---|
| **STT de consultas** (tiempo real) | Whisper Tiny (39 MB) | CPU | ~0.15 GB | Siempre disponible; no compite con GPU |
| **Ingesta de videos** (batch background) | Whisper Small (244 MB) | CPU | ~0.9 GB | Solo cuando inferencia está inactiva (semáforo) |

---

## 5. Niveles de Inteligencia (Triaje Adaptativo)

### 5.1 Cálculo del Score de Confianza de Recuperación (RCS)

```python
async def route_query(query: str) -> RoutingDecision:
    query_emb  = await embed_fast(query)          # intfloat/multilingual-e5-small, < 50ms
    candidates = await chroma.query(query_emb, n_results=5)
    rcs        = mean(candidates.distances[:3])   # 0.0 – 1.0, similitud coseno del top-3
    fts_count  = await pg_fts_count(query)        # señal de refuerzo desde PostgreSQL FTS

    if rcs >= 0.78 and fts_count >= 2:   return Level.L1_CDN_STRICT
    elif rcs >= 0.55 or fts_count >= 1:  return Level.L2_CDN_AUGMENTED
    elif is_educational_domain(query):   return Level.L3_GENERAL_KNOWLEDGE
    else:                                return Level.L4_CLARIFICATION
```

### 5.2 Comportamiento por Nivel

| Nivel | Condición | Comportamiento |
|---|---|---|
| **L1 CDN Strict** | RCS ≥ 0.78 + FTS ≥ 2 | Overview 100% anclado a CDN. Badge "Verificado con fuentes locales". Si grounding < 0.45 → respuesta bloqueada |
| **L2 CDN Augmented** | RCS ≥ 0.55 o FTS ≥ 1 | RAG + conocimiento base. Afirmaciones etiquetadas `[CDN]` vs `[Base]` |
| **L3 Knowledge Only** | Dominio educativo, sin match CDN | Solo modelo. Aviso: "Respuesta de conocimiento general. No se encontraron recursos en la red local." |
| **L4 Clarification** | RCS < 0.40 sin dominio educativo | 2-3 preguntas aclaratorias. Sin generación especulativa |

---

## 6. Estrategia de Inferencia en Edge (Jetson Orin NX)

### 6.1 Cuantización INT4 AWQ — Dataset de Calibración Peruano

AWQ (Activation-aware Weight Quantization) preserva los canales de activación de mayor magnitud.
El dataset de calibración es crítico: **debe reflejar el dominio real de uso**.

```bash
# El dataset debe contener texto educativo en español peruano:
# transcripciones de clases, libros del MINEDU, ejercicios de matemáticas,
# ciencias naturales, historia del Perú. Mínimo 512 muestras de ~256 tokens.

python quantize.py \
    --model_dir   ./hf_models/Llama-3.1-8B-Instruct \
    --output_dir  ./trt_checkpoints/llama31-8b-int4-awq \
    --qformat     int4_awq \
    --calib_size  512 \
    --calib_dataset ./calibration/peru_educational_es.jsonl  # CRITICO: dominio real

# NOTA: La calibración AWQ ocurre UNA SOLA VEZ, en reposo o en máquina separada.
# NO ocurre en tiempo de ejecución. El resultado son checkpoints estáticos.
```

```bash
trtllm-build \
    --checkpoint_dir ./trt_checkpoints/llama31-8b-int4-awq \
    --output_dir     ./trt_engines/llama31-8b-int4 \
    --gemm_plugin auto --gpt_attention_plugin auto \
    --max_batch_size 1 \            # conserva memoria
    --max_input_len  2560 \
    --max_seq_len    3584 \
    --use_paged_context_fmha enable \
    --speculative_decoding_mode draft_tokens_external
```

### 6.2 Speculative Decoding

```
Sin speculative decoding (autoregresivo puro):
  Token₁ → [8B fwd] → Token₂ → [8B fwd] → ...   →  ~12 tok/s

Con speculative decoding (γ = 5 tokens de borrador):
  [1B propone: tok₁…tok₅] → [8B verifica los 5 en 1 solo fwd] → acepta k ≥ 3
                                                               →  ~28–35 tok/s  (2.5–3× más rápido)
```

### 6.3 System Prompts por Nivel

```python
SYSTEM_PROMPT_L1 = """Eres un asistente educativo offline en escuelas rurales del Perú.
Usa ÚNICAMENTE los fragmentos [FUENTE N]. NO inventes datos. Si un dato no aparece
en ninguna fuente, omítelo. Responde en español para secundaria.
Termina con: [FUENTES USADAS: N, M]"""

SYSTEM_PROMPT_L2 = """Eres un asistente educativo offline. Usa primero los fragmentos
CDN [FUENTE N] marcándolos [CDN]. Complementa con tu conocimiento base marcado [Base]."""

SYSTEM_PROMPT_L3 = """Eres un asistente educativo offline. No hay recursos locales
sobre este tema. Responde con tu conocimiento general en español para estudiantes peruanos."""

MAX_CONTEXT_TOKENS    = 1792   # reducido para dejar margen de seguridad en memoria
MAX_GENERATION_TOKENS = 512
```

---

## 7. Gestión de Memoria y Prevención de OOM

### 7.1 El Problema: Memoria Unificada en Jetson

En la Jetson Orin NX, CPU y GPU comparten los mismos 16 GB físicamente. No son compartimentos separados. Si el motor de inferencia LLM y Whisper Small (ingesta batch) corren simultáneamente, el sistema puede sufrir un **Out-Of-Memory (OOM) con reinicio del proceso**, dejando el CDN sin IA hasta intervención manual.

La versión anterior del plan calculaba exactamente 16.0 GB — sin margen. Esto es inaceptable en producción en un entorno sin personal técnico local.

### 7.2 Presupuesto de Memoria Revisado

```
Jetson Orin NX — 16 GB unified memory
╔══════════════════════════════════════════════════════════════════╗
║  RESIDENTES PERMANENTES                                          ║
║  OS + servicios del sistema                       : ~2.0 GB     ║
║  Node.js/Express + PostgreSQL + Redis             : ~1.2 GB     ║
║  FastAPI + Python runtime                         : ~0.5 GB     ║
║  ChromaDB (100K chunks × 512d en memoria)         : ~0.8 GB     ║
║  Embedding model multilingual-e5-small FP16       : ~0.5 GB     ║
║  Whisper Tiny CPU (STT de consultas en tiempo real): ~0.15 GB   ║
║  Draft model Llama-3.2-1B INT4 AWQ                : ~2.1 GB     ║
║  Target model Llama-3.1-8B INT4 AWQ               : ~6.2 GB     ║
║  KV-Cache paged (máx reservado)                   : ~1.05 GB    ║
║  ──────────────────────────────────────────────────────────      ║
║  SUBTOTAL RESIDENTES                              : ~14.5 GB    ║
╠══════════════════════════════════════════════════════════════════╣
║  BUFFER DE SEGURIDAD (nunca tocar)                : ~1.5 GB     ║
╠══════════════════════════════════════════════════════════════════╣
║  POOL DE INGESTA (uso temporal, controlado por semáforo)         ║
║  Whisper Small CPU (ingesta batch de videos)      : ~0.9 GB     ║
║  PyMuPDF + Tesseract OCR                          : ~0.3 GB     ║
║  ──────────────────────────────────────────────────────────      ║
║  POOL TOTAL (toma del buffer cuando inferencia inactiva): ~1.2 GB║
╚══════════════════════════════════════════════════════════════════╝

MÁXIMO simultáneo (residentes + pool):  15.7 GB  ✓  (0.3 GB de margen mínimo)
```

### 7.3 Semáforo de Exclusión Ingesta / Inferencia

```python
# ai_engine/resource_manager.py
import asyncio

_inference_lock = asyncio.Lock()
_ingestion_lock = asyncio.Lock()

class ResourceManager:
    """
    Garantiza que Whisper Small (ingesta batch) y el LLM (inferencia)
    no compitan por memoria al mismo tiempo.
    """

    async def acquire_inference(self):
        """Espera a que no haya ingesta activa antes de inferir."""
        if _ingestion_lock.locked():
            await _ingestion_lock.acquire()
            _ingestion_lock.release()
        await _inference_lock.acquire()

    def release_inference(self):
        _inference_lock.release()

    async def acquire_ingestion(self):
        """Espera a que no haya inferencia activa antes de ingestar."""
        if _inference_lock.locked():
            await _inference_lock.acquire()
            _inference_lock.release()
        await _ingestion_lock.acquire()

    def release_ingestion(self):
        _ingestion_lock.release()

resource_manager = ResourceManager()
```

```python
# Uso en el handler de búsqueda:
async def search_handler(payload):
    await resource_manager.acquire_inference()
    try:
        return await run_search_pipeline(payload)
    finally:
        resource_manager.release_inference()

# Uso en el worker de ingesta:
async def ingest_worker(content_id: str):
    await resource_manager.acquire_ingestion()
    try:
        await run_ingestion_pipeline(content_id)
    finally:
        resource_manager.release_ingestion()
```

---

## 8. Arquitectura de Datos Vectoriales

### 8.1 ChromaDB: Elección Justificada

| Criterio | ChromaDB | Milvus |
|---|---|---|
| Setup en Jetson ARM64 | Single binary, SQLite embedded | Docker compose + etcd + MinIO |
| RAM en reposo | ~150 MB | ~800 MB |
| Escala adecuada | < 200K chunks | > 500K chunks |
| **Veredicto** | **Elegido** — adecuado para CDN rural | Considerar si escala supera 200K docs |

### 8.2 Esquema de Colección

```python
chroma_client.create_collection(
    name="cdn_chunks",
    metadata={"hnsw:space": "cosine", "hnsw:construction_ef": 200, "hnsw:M": 32},
    embedding_function=LocalEmbeddingFunction()
)

# Metadata por chunk — incluye viewer_url (ruta al visor, no a archivo crudo)
chunk_metadata = {
    "content_id":       "uuid-postgresql",
    "content_type":     "video | pdf | audio | document",
    "title":            "Redes de Computadoras - Módulo 5",
    "category":         "tecnologia",
    "chunk_index":      4,
    "total_chunks":     23,
    "source_type":      "transcript | pdf_text | pdf_ocr | description",
    "timestamp_start":  142.5,     # segundos (video/audio); null para PDF
    "timestamp_end":    189.0,
    "viewer_url":       "/viewer/video/uuid?t=142",   # ruta al visor, NO al archivo
    "thumbnail_url":    "/storage/thumbnails/uuid.jpg",
    "upload_date":      "2026-01-15T09:00:00Z",
    "language":         "es | qu",
    "chunk_type":       "summary | section | sentence"
}
```

### 8.3 Chunking Jerárquico

```
SUMMARY  (256 tokens)            → representación completa del documento; para ranking inicial
  └── SECTION (512 tok, overlap 64) → párrafos/capítulos; para contexto RAG
        └── SENTENCE (128 tok)      → oraciones; para grounding y snippets de tarjetas
```

---

## 9. Pipeline de Ingesta Multi-modal

### 9.1 Hook Automático desde el CDN

```typescript
// server/src/controllers/uploadController.ts — añadir al final de processingComplete()
async function notifyAIEngineForIndexing(contentId: string): Promise<void> {
  const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
  try {
    await fetch(`${AI_ENGINE_URL}/api/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId }),
    });
  } catch {
    // Non-fatal: el CDN sigue operativo. El content_id queda en ai_ingestion_queue
    console.warn(`[AI] Engine no disponible, ingesta diferida: ${contentId}`);
  }
}
```

### 9.2 Generación de Thumbnails durante Ingesta

Los thumbnails son imágenes estáticas generadas una vez al ingestar, guardadas en `/storage/thumbnails/`:

```python
# ai_engine/services/ingestion/thumbnail_generator.py

async def generate_thumbnail(content_id, content_type, file_path, category) -> str:
    output = f"/storage/thumbnails/{content_id}.jpg"

    if content_type == "video":
        # FFmpeg: frame representativo al segundo 10
        subprocess.run([
            "ffmpeg", "-i", file_path, "-ss", "00:00:10",
            "-vframes", "1", "-vf", "scale=320:180", "-q:v", "3",
            output, "-y"
        ], check=True)

    elif content_type in ("pdf", "document"):
        # PyMuPDF: primera página como JPG 320×180
        import fitz
        doc = fitz.open(file_path)
        page = doc[0]
        mat = fitz.Matrix(320/page.rect.width, 0, 0, 180/page.rect.height, 0, 0)
        page.get_pixmap(matrix=mat).save(output)

    elif content_type == "audio":
        # Sin frame visual: copia ícono genérico de categoría
        shutil.copy(f"/static/icons/audio_{category}.jpg", output)

    return f"/storage/thumbnails/{content_id}.jpg"
```

**Nota**: `ffmpegService.ts` del CDN existente ya genera thumbnails para video. El AI Engine reutiliza ese thumbnail si existe; lo genera si falta.

### 9.3 Pipeline por Tipo de Contenido (con semáforo activo)

```
╔═══════════════════════════════════════════════════════════════╗
║   INGESTA PIPELINE (worker background, semáforo requerido)    ║
╠═════════════════╦═════════════════════════════════════════════╣
║  VIDEO / AUDIO  ║ 1. Thumbnail FFmpeg (si no existe)          ║
║                 ║ 2. Extrae audio mono 16kHz → FFmpeg         ║
║                 ║ 3. Transcripción → Whisper Small CPU        ║
║                 ║    (~1 min por cada 10 min de video)        ║
║                 ║ 4. Segmentación por VAD (silencios)         ║
║                 ║ 5. Chunking jerárquico con timestamp        ║
║                 ║ 6. Embed batch → ChromaDB                   ║
╠═════════════════╬═════════════════════════════════════════════╣
║  PDF / DOC      ║ 1. Thumbnail PyMuPDF primera página         ║
║                 ║ 2. Extrae texto → PyMuPDF                   ║
║                 ║ 3. Si < 100 chars/pág → OCR Tesseract 5    ║
║                 ║    (modelo español instalado)               ║
║                 ║ 4. Chunking jerárquico por párrafos         ║
║                 ║ 5. Embed batch → ChromaDB                   ║
╚═════════════════╩═════════════════════════════════════════════╝
```

---

## 10. Motor de Recuperación Híbrida (HyDE + BM25 + Vector)

### 10.1 HyDE: Expansión de Query

```python
async def hyde_expand(query: str) -> str:
    prompt = f"Escribe un párrafo educativo de 5 oraciones sobre: {query}"
    return await draft_model.generate(prompt, max_tokens=150)

# Interpolación: 60% embedding de la query original + 40% del doc hipotético
query_emb = 0.6 * embed(query) + 0.4 * embed(hypothetical_doc)
```

### 10.2 Búsqueda Paralela + RRF

```python
async def hybrid_search(query, query_emb, top_k=20):
    vector_results = await chroma.query(query_emb, n_results=top_k,
                                        where={"chunk_type": {"$in": ["section","summary"]}})
    bm25_scores = bm25_index.get_scores(spanish_tokenizer.tokenize(query))
    bm25_top_k  = np.argsort(bm25_scores)[-top_k:][::-1]
    return rrf_merge(vector_results, bm25_top_k, k=60)   # Reciprocal Rank Fusion
```

### 10.3 Cross-Encoder Re-ranker

```python
# ms-marco-MiniLM-L-6-v2: 22 MB, rápido en CPU
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scored   = reranker.predict([(query, c.text) for c in top_20_candidates])
top_5    = sorted(zip(scored, top_20_candidates), reverse=True)[:5]
```

### 10.4 Ensamblaje de Contexto

```python
def build_context(chunks: list) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        time_info = (f"Tiempo: {chunk.metadata['timestamp_start']:.0f}s – "
                     f"{chunk.metadata['timestamp_end']:.0f}s"
                     if chunk.metadata.get('timestamp_start') else "")
        parts.append(
            f"[FUENTE {i+1}]\n"
            f"Título: {chunk.metadata['title']}\n"
            f"Tipo: {chunk.metadata['content_type']}\n"
            f"{time_info}\n"
            f"Fragmento: {chunk.text}\n---"
        )
    return "\n".join(parts)
```

---

## 11. Mecanismo Anti-Alucinación (Grounding Estricto)

### 11.1 Coverage Score Post-Generación

```python
async def verify_grounding(response: str, chunks: list) -> GroundingReport:
    sentences = split_sentences(response)
    scores    = []
    for sent in sentences:
        sent_emb = embed(sent)
        max_sim  = max(cosine_similarity(sent_emb, embed(c.text)) for c in chunks)
        scores.append(GroundingScore(sentence=sent, score=max_sim))

    coverage = mean(s.score for s in scores)
    return GroundingReport(
        coverage_score=coverage,
        unverified=[s for s in scores if s.score < 0.45],
        is_grounded=(coverage >= 0.60)
    )
```

### 11.2 Acciones por Score

| Coverage | L1 | L2 / L3 |
|---|---|---|
| ≥ 0.80 | Normal + badge "Verificado CDN" | Normal |
| 0.60 – 0.79 | Normal + aviso suave | Normal |
| 0.45 – 0.59 | Oraciones no verificadas eliminadas | Aviso visible |
| < 0.45 | **Respuesta bloqueada** → mensaje al usuario | Aviso fuerte |

### 11.3 Prompt Anti-Alucinación L1

```
<|system|>
{system_prompt}
REGLA: Solo usa datos de los fragmentos [FUENTE N]. Termina con [FUENTES USADAS: N,M].
<|context|>
{assembled_context}
<|user|>
{query}
<|assistant|>
```

El campo `[FUENTES USADAS: ...]` se parsea automáticamente para detectar citas fabricadas (números de fuente que no existen en los chunks entregados).

---

## 12. Contrato de API: Rich Snippets y Streaming SSE

### 12.1 Búsqueda por Texto

```http
POST http://cdn-local:3000/api/ai/search
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "query": "Explícame qué es el protocolo OSPF y en qué capa del modelo TCP/IP trabaja",
  "context": { "user_role": "student", "current_category": "redes" },
  "options": { "streaming": true, "max_sources": 5, "language": "auto" }
}
```

### 12.2 Respuesta JSON Completa (sin streaming)

```json
{
  "request_id": "f7e2a1b4-9c3d-...",
  "query_transcribed": null,

  "routing": {
    "level": "L2_CDN_AUGMENTED",
    "confidence": 0.71,
    "retrieval_time_ms": 148,
    "generation_time_ms": 3850
  },

  "ai_overview": {
    "text": "OSPF (Open Shortest Path First) es un protocolo de enrutamiento dinámico de estado de enlace. [CDN] Opera en la Capa 3 del modelo OSI (Capa de Red) y en la Capa de Internet del modelo TCP/IP. [CDN] Utiliza el algoritmo de Dijkstra para calcular la ruta más corta intercambiando paquetes LSA. [Base] En entornos empresariales es el protocolo interior más usado por su escalabilidad.",
    "grounding": {
      "coverage_score": 0.79,
      "is_verified": true,
      "unverified_count": 1,
      "source_mode": "L2_CDN_AUGMENTED"
    },
    "language_detected": "es"
  },

  "cdn_results": [
    {
      "rank": 1,
      "content_id": "uuid-abc123",
      "type": "video",
      "title": "Clase Grabada: Protocolos de Enrutamiento TCP/IP",
      "category": "redes",
      "snippet": "(min 12:45) ...OSPF se encapsula directamente sobre IP con protocolo 89, a diferencia de RIP que usa UDP puerto 520...",
      "upload_date": "2024-01-15T09:00:00Z",
      "duration_seconds": 2847,
      "thumbnail_url": "/storage/thumbnails/uuid-abc123.jpg",
      "viewer_url": "/viewer/video/uuid-abc123",
      "deep_link": "/viewer/video/uuid-abc123?t=765",
      "requires_auth": false,
      "relevance_score": 0.91
    },
    {
      "rank": 2,
      "content_id": "uuid-def456",
      "type": "pdf",
      "title": "Manual Técnico: Configuración de OSPF en Routers",
      "category": "redes",
      "snippet": "...el comando 'router ospf 1' inicia el proceso. Definir las áreas correctamente evita bucles de enrutamiento...",
      "upload_date": "2023-10-27T14:30:00Z",
      "page_count": 48,
      "thumbnail_url": "/storage/thumbnails/uuid-def456.jpg",
      "viewer_url": "/viewer/document/uuid-def456",
      "deep_link": "/viewer/document/uuid-def456?page=12",
      "requires_auth": true,
      "relevance_score": 0.86
    }
  ],

  "ui_hints": {
    "show_sources_panel": true,
    "highlight_timestamps": true,
    "show_auth_warning": true,
    "suggested_queries": [
      "¿Qué diferencia hay entre OSPF y BGP?",
      "¿Cómo funciona el algoritmo de Dijkstra en redes?"
    ]
  }
}
```

### 12.3 Protocolo SSE (modo preferido — streaming)

```
event: routing
data: {"level":"L2_CDN_AUGMENTED","confidence":0.71}

event: source
data: {"rank":1,"type":"video","title":"Clase Grabada: Protocolos TCP/IP","snippet":"(min 12:45) ...OSPF con protocolo 89...","thumbnail_url":"/storage/thumbnails/uuid-abc123.jpg","viewer_url":"/viewer/video/uuid-abc123","deep_link":"/viewer/video/uuid-abc123?t=765","requires_auth":false,"relevance_score":0.91}

event: source
data: {"rank":2,"type":"pdf","title":"Manual Técnico OSPF","snippet":"...router ospf 1 inicia el proceso...","thumbnail_url":"/storage/thumbnails/uuid-def456.jpg","viewer_url":"/viewer/document/uuid-def456","deep_link":"/viewer/document/uuid-def456?page=12","requires_auth":true,"relevance_score":0.86}

event: token
data: {"text":"OSPF "}

event: token
data: {"text":"(Open Shortest Path First) "}

... (~30ms entre tokens en Jetson)

event: grounding
data: {"coverage_score":0.79,"is_verified":true}

event: done
data: {"total_time_ms":4120,"tokens_generated":112}
```

Las tarjetas de contenido con thumbnails llegan en ~150ms — antes de que el LLM genere una sola palabra. El usuario puede navegar al video mientras lee el overview.

### 12.4 Campos del Rich Snippet por Tipo de Contenido

| Campo | Video | PDF/Doc | Audio |
|---|---|---|---|
| `thumbnail_url` | Frame FFmpeg s=10 | Primera página JPG | Ícono de categoría |
| `snippet` | Fragmento transcripción Whisper con timestamp | Texto extraído con número de página | Fragmento transcripción Whisper |
| `deep_link` | `viewer_url?t={s}` | `viewer_url?page={n}` | `viewer_url?t={s}` |
| `duration_seconds` | ✓ | — | ✓ |
| `page_count` | — | ✓ | — |

### 12.5 Error Estandarizado

```json
{
  "error": {
    "code": "GROUNDING_INSUFFICIENT",
    "level": "L1",
    "message": "No hay suficiente información en la red local sobre este tema.",
    "coverage_score": 0.31,
    "fallback_action": "SHOW_GENERAL_SEARCH",
    "suggested_queries": ["redes de computadoras", "modelo OSI capas"]
  }
}
```

---

## 13. Visor de Contenido y Flujo de Autenticación

### 13.1 Principio Fundamental

> **La IA es un motor de descubrimiento, no un repositorio de archivos.**

Los resultados incluyen `viewer_url` y `deep_link` — rutas a páginas del frontend de la plataforma donde el contenido se visualiza en un ambiente controlado. El archivo nunca se entrega crudamente al browser desde la búsqueda.

```
INCORRECTO:  /storage/videos/uuid-abc123/720p.mp4     ← descarga directa
INCORRECTO:  /api/content/uuid-def456/download         ← descarga directa

CORRECTO:    /viewer/video/uuid-abc123?t=765           ← visor de la plataforma
CORRECTO:    /viewer/document/uuid-def456?page=12      ← visor de la plataforma
```

### 13.2 Rutas de Visor por Tipo

| Tipo | Ruta | Componente frontend |
|---|---|---|
| Video | `/viewer/video/{id}?t={s}` | Video.js; seek automático al segundo `t` al cargar |
| PDF | `/viewer/document/{id}?page={n}` | PDF.js embebido; abre en la página `n` |
| Audio | `/viewer/audio/{id}?t={s}` | Player `<audio>` con seek |

Desde el visor: si `can_download === true` para ese usuario y contenido → se muestra botón "Descargar". La descarga es acción explícita del usuario **desde dentro del visor**, nunca una URL expuesta en resultados de búsqueda.

### 13.3 Flujo de Autenticación

```
1. UI renderiza tarjeta de resultado.
   Si requires_auth === true → ícono de candado visible en la tarjeta.

2. Usuario hace clic en una tarjeta → navega a /viewer/video/uuid-abc123?t=765

3. El servidor CDN (Express :3000) intercepta la request al visor.

4a. Token JWT válido + permiso en DB:
    → Carga el visor. El contenido streama normalmente.

4b. Sin JWT (no autenticado):
    → Express redirige 302 a /login?redirect=/viewer/video/uuid-abc123?t=765
    → Tras login exitoso, redirige al deep link original con seek incluido.

4c. JWT válido pero sin permiso (403):
    → Frontend muestra: "No tienes acceso a este contenido. Contacta a tu docente."
```

```typescript
// server/src/middleware/viewerAuth.ts  [NUEVO]
export const viewerAuthMiddleware: RequestHandler = async (req, res, next) => {
  const token = req.cookies?.jwt || req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    const back = encodeURIComponent(req.originalUrl);
    return res.redirect(302, `/login?redirect=${back}`);
  }
  const user = await verifyJWT(token);
  if (!user) {
    return res.redirect(302, `/login?redirect=${encodeURIComponent(req.originalUrl)}`);
  }
  const hasAccess = await checkContentPermission(user.id, req.params.id);
  if (!hasAccess) return res.status(403).json({ error: 'ACCESS_DENIED' });
  req.user = user;
  next();
};
```

### 13.4 Público vs. Restringido

El campo `requires_auth` en los resultados es solo informativo para la UI (mostrar/ocultar el candado). La **única fuente de verdad de permisos** es el middleware del CDN backend que consulta PostgreSQL en cada request. La UI nunca toma decisiones de seguridad.

---

## 14. Integración con el CDN Existente (Node.js → FastAPI)

### 14.1 Nueva Ruta en Express

```typescript
// server/src/routes/ai.ts  [NUEVO]
import express from 'express';
import { authMiddleware } from '../middleware/auth.js';
import { aiSearchController } from '../controllers/aiSearchController.js';

const router = express.Router();
router.post('/search',       authMiddleware, aiSearchController.search);
router.post('/voice-search', authMiddleware, aiSearchController.voiceSearch);
router.get('/health',        aiSearchController.health);
export default router;
```

```typescript
// server/src/controllers/aiSearchController.ts  [NUEVO]
export const aiSearchController = {

  async search(req, res) {
    const AI_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
    const { query, context, options } = req.body;

    if (options?.streaming) {
      // CRITICO: desactivar buffering y compresión para SSE.
      // Sin esto, los tokens se acumulan en el buffer de Nginx/Express
      // y el usuario no ve nada hasta que llega el response completo.
      res.setHeader('Content-Type',      'text/event-stream');
      res.setHeader('Cache-Control',     'no-cache');
      res.setHeader('Connection',        'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no');        // Nginx: desactiva proxy buffering
      res.setHeader('Content-Encoding',  'identity');  // desactiva gzip explícitamente

      const upstream = await fetch(`${AI_URL}/api/search/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, context, user_id: req.user.id }),
      });

      const reader = upstream.body!.getReader();
      const pump = async () => {
        const { done, value } = await reader.read();
        if (done) { res.end(); return; }
        res.write(value);
        pump();
      };
      pump();

    } else {
      const result = await fetch(`${AI_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, context, user_id: req.user.id }),
      });
      res.json(await result.json());
    }
  },

  async voiceSearch(req, res) {
    const AI_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
    const formData = new FormData();
    // req.file viene de multer (audio en memoria, máx 2 MB para 15 s a 16kHz mono)
    formData.append('audio', new Blob([req.file.buffer]), 'query.wav');
    formData.append('context', JSON.stringify(req.body.context || {}));

    const result = await fetch(`${AI_URL}/api/voice-search`, {
      method: 'POST',
      body: formData,
    });
    res.json(await result.json());  // voice-search siempre es JSON, no SSE
  },

  async health(req, res) {
    const AI_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
    try {
      const r = await fetch(`${AI_URL}/api/health`, { signal: AbortSignal.timeout(2000) });
      res.json(await r.json());
    } catch {
      res.status(503).json({ status: 'ai_engine_unavailable' });
    }
  }
};
```

### 14.2 Cambio en index.ts (mínimo)

```typescript
// server/src/index.ts — agregar las líneas marcadas
import aiRoutes from './routes/ai.js';                          // AGREGAR
import multer  from 'multer';                                    // AGREGAR
const voiceUpload = multer({                                     // AGREGAR
  storage: multer.memoryStorage(),                               // AGREGAR
  limits:  { fileSize: 2_000_000 }  // 2 MB máx (15 s audio)   // AGREGAR
});                                                              // AGREGAR

app.use('/api/auth',       authRoutes);
app.use('/api/categories', categoryRoutes);
app.use('/api/content',    contentRoutes);
app.use('/api/upload',     uploadRoutes);
app.use('/api/ai',         aiRoutes);                           // AGREGAR
```

---

## 15. Consideraciones Críticas de Hardware

### 15.1 Disipación Activa: Obligatoria en Escuelas Rurales

> ⚠️ **Advertencia de despliegue**: Las escuelas rurales del Perú pueden alcanzar 25°C–35°C de temperatura ambiente sin aire acondicionado. La Jetson Orin NX bajo carga de inferencia LLM genera calor significativo y sostenido. **Un disipador pasivo no es suficiente**.

**Hardware obligatorio**:
- Jetson Orin NX con **Active Cooling Kit** (disipador + ventilador PWM controlado por el SoC)
- Sin esto el sistema alcanza throttling térmico a los pocos minutos de uso, elevando la latencia a 18+ s por respuesta y degradando la experiencia para todos los usuarios

**Condiciones de instalación**:
- Gabinete con ventilación (no sellado herméticamente)
- Temperatura ambiente máxima recomendada: ≤ 35°C
- Si el ambiente supera 35°C: ventilador adicional externo o rack con ventilación forzada

### 15.2 Verificación del Ventilador

```bash
# Verificar que el SoC reconoce el ventilador PWM
cat /sys/class/thermal/cooling_device*/type   # debe aparecer "pwm-fan"

# El nvpmodel + thermal manager controlan la velocidad automáticamente
# Solo asegurarse de que el fan esté conectado al header J14 del Carrier Board
```

---

## 16. Gestión Térmica Adaptativa

### 16.1 Perfiles de Potencia NVPModel

```python
# ai_engine/thermal_manager.py
THERMAL_THRESHOLDS = {
    "nominal":  {"max_temp": 55,  "nvp_mode": 4, "draft_gamma": 5},
    "warm":     {"max_temp": 68,  "nvp_mode": 3, "draft_gamma": 4},
    "hot":      {"max_temp": 78,  "nvp_mode": 2, "draft_gamma": 3},
    "critical": {"max_temp": 999, "nvp_mode": 1, "draft_gamma": 2},
}

async def thermal_governor():
    while True:
        temp = int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000.0
        for profile, cfg in THERMAL_THRESHOLDS.items():
            if temp < cfg["max_temp"]:
                subprocess.run(["nvpmodel", "-m", str(cfg["nvp_mode"])])
                update_inference_config(draft_gamma=cfg["draft_gamma"])
                if profile == "critical":
                    await notify_ui_thermal_warning(temp)  # aviso visible en UI
                break
        await asyncio.sleep(10)
```

### 16.2 Rendimiento por Perfil Térmico

| Perfil | Temp. SoC | Potencia | Tokens/seg | Latencia ~256 tok |
|---|---|---|---|---|
| Nominal | < 55°C | ~15 W | ~35 tok/s | ~8 s |
| Warm | < 68°C | ~12 W | ~28 tok/s | ~10 s |
| Hot | < 78°C | ~9 W | ~20 tok/s | ~13 s |
| Critical | ≥ 78°C | ~7 W | ~14 tok/s | ~18 s + ⚠️ en UI |

### 16.3 KV-Cache Persistente (reduce ~40% de tokens a procesar)

```python
kv_cache = DiskLRU(cache_dir="/tmp/kv_prefix_cache", max_size_gb=1.0, ttl_hours=24)

async def get_or_generate(prompt_hash: str, full_prompt: str):
    cached = kv_cache.get(prompt_hash)
    if cached:
        return await engine.generate_from_kv_state(cached, max_new_tokens=512)
    response = await engine.generate(full_prompt, max_new_tokens=512)
    kv_cache.set(prompt_hash, response.kv_state)
    return response
```

---

## 17. Limitaciones Conocidas y Mitigaciones

### 17.1 Soporte de Quechua — Limitación Real Documentada

| Componente | Español | Quechua |
|---|---|---|
| Whisper STT (transcripción de consulta) | Excelente | Bueno |
| multilingual-e5-small (embedding) | Excelente | **Pobre** — cobertura marginal en pretraining |
| Llama-3.1-8B (generación) | Excelente | **Muy limitado** — escasos tokens quechua en pretraining |
| Cross-Encoder re-ranker | Bueno | **No funcional** — entrenado en pares inglés/inglés |

**Mitigación**: traducción automática quechua → español con el draft model 1B, con advertencia explícita al usuario:

```python
async def route_with_language_check(query: str) -> RoutingDecision:
    detected_lang = detect_language(query)   # langdetect

    if detected_lang == "qu":
        query_es = await draft_model.generate(
            f"Traduce al español: {query}", max_tokens=100
        )
        decision = await route_query(query_es)
        decision.meta["original_language"] = "qu"
        decision.meta["translation_warning"] = (
            "Consulta detectada en quechua y traducida automáticamente al español. "
            "La precisión puede ser menor."
        )
        return decision

    return await route_query(query)
```

El sistema es **transparente sobre esta limitación**. No pretende soporte completo de quechua.

### 17.2 Concurrencia Limitada

La Jetson puede atender **1 request de inferencia a la vez**. Para escuelas con 20+ estudiantes simultáneos:

- Requests hacen cola FIFO con `asyncio.Queue`
- El tiempo estimado de espera se informa vía SSE:
  `event: queue_position data: {"position": 3, "estimated_wait_s": 28}`
- Las tarjetas de contenido (Rich Snippets) se entregan inmediatamente (~150ms); el usuario puede navegar mientras espera el texto de la IA

Para escuelas grandes: dos Jetsons + Nginx round-robin local resuelve la concurrencia.

### 17.3 Latencia de Indexación vs. Disponibilidad

Un video de 60 minutos tarda ~6 minutos en transcribirse e indexarse. Durante ese tiempo el contenido está disponible en el CDN para streaming pero aún no aparece en búsquedas IA. Estado `indexing` visible en la UI como "Indexando con IA...".

---

## 18. Observabilidad y Métricas

### 18.1 Métricas Prometheus

```python
from prometheus_client import Histogram, Counter, Gauge

RETRIEVAL_LATENCY   = Histogram('ai_retrieval_seconds',   buckets=[0.05,0.1,0.2,0.5,1.0,2.0])
GENERATION_LATENCY  = Histogram('ai_generation_seconds',  buckets=[2,5,10,15,30])
STT_LATENCY         = Histogram('ai_stt_seconds',         buckets=[0.3,0.6,1.0,2.0,5.0])
COVERAGE_SCORE      = Histogram('ai_grounding_coverage',  buckets=[0.2,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
ROUTING_LEVEL       = Counter('ai_routing_decisions_total', labelnames=['level'])
JETSON_TEMP         = Gauge('jetson_soc_temp_celsius')
JETSON_GPU_UTIL     = Gauge('jetson_gpu_util_pct')
KV_CACHE_HITS       = Counter('ai_kv_cache_hits_total')
INGESTION_QUEUE_LEN = Gauge('ai_ingestion_queue_length')
INFERENCE_QUEUE_LEN = Gauge('ai_inference_queue_length')
```

### 18.2 Endpoint /api/ai/health

```json
{
  "status": "healthy",
  "jetson": {
    "soc_temp_celsius": 52.3,
    "gpu_util_pct": 34,
    "active_profile": "nominal",
    "free_memory_gb": 2.1,
    "fan_status": "active"
  },
  "models": {
    "draft_model": "loaded",
    "target_model": "loaded",
    "embedder": "loaded",
    "stt_whisper_tiny": "loaded"
  },
  "index": {
    "total_chunks": 18432,
    "total_documents": 412,
    "last_ingestion": "2026-02-23T14:30:00Z",
    "pending_ingestion_jobs": 2
  },
  "queues": {
    "inference_waiting": 0,
    "ingestion_waiting": 2
  },
  "performance": {
    "avg_retrieval_ms": 148,
    "avg_generation_ms": 3940,
    "avg_stt_ms": 820,
    "avg_coverage_score": 0.83,
    "kv_cache_hit_rate": 0.24
  }
}
```

---

## 19. Plan de Fases de Implementación

### Semana 1-2: Fundación de Datos e Ingesta
- [ ] Instalar ChromaDB + `multilingual-e5-small` en Jetson Orin NX
- [ ] Pipeline de ingesta PDF: PyMuPDF + Tesseract + generación de thumbnail (primera página)
- [ ] Pipeline de ingesta video: FFmpeg + Whisper Small + thumbnail (frame s=10) + semáforo
- [ ] Indexar todos los documentos actuales de `/storage/`
- [ ] Hook en `uploadController.ts` + tabla `ai_ingestion_queue` en PostgreSQL
- [ ] Verificar Active Heat Sink instalado y ventilador reconocido por sysfs

### Semana 3-4: Motor de Retrieval Híbrido
- [ ] BM25 con tokenizador spaCy `es_core_news_sm`
- [ ] HyDE con draft model 1B
- [ ] Cross-encoder re-ranker `ms-marco-MiniLM-L-6-v2`
- [ ] Benchmark retrieval (objetivo < 200ms; incluye HyDE)
- [ ] Tests unitarios: chunking jerárquico, RRF fusion, re-ranking

### Semana 5-6: TensorRT-LLM y Motor de Inferencia
- [ ] Construir dataset de calibración AWQ educativo peruano (mínimo 512 muestras)
- [ ] Cuantizar y compilar Llama-3.2-1B (draft) con AWQ en Jetson
- [ ] Cuantizar y compilar Llama-3.1-8B (target) con AWQ en Jetson
- [ ] Validar speculative decoding γ=5 y medir speed-up real obtenido
- [ ] Implementar y testear thermal_manager + perfiles NVPModel

### Semana 7-8: STT, API, Visor e Integración
- [ ] Endpoint `/api/ai/voice-search` con Whisper Tiny CPU
- [ ] Implementar `ResourceManager` (semáforo ingesta/inferencia)
- [ ] FastAPI: search (SSE + JSON), voice-search, ingest, health
- [ ] Express: routes/ai.ts + aiSearchController.ts con headers SSE correctos
- [ ] Rutas `/viewer/*` en frontend React con PDF.js + Video.js + seek desde deep_link
- [ ] viewerAuth middleware: JWT → 302 login → redirect back
- [ ] multer para upload de audio en Express
- [ ] Tests de integración end-to-end: texto, voz, PDF viewer, video player

### Semana 9-10: Grounding, QA y Prueba de Carga
- [ ] Coverage Score verificator + detección de citas fabricadas
- [ ] Dataset de evaluación: 60 pares pregunta/respuesta-esperada
  - 40 en español técnico (redes, matemáticas, ciencias)
  - 10 de conocimiento general educativo peruano
  - 10 en quechua (medir precisión tras traducción automática)
- [ ] Calibrar umbrales RCS con datos reales de la CDN
- [ ] Test de carga: 5 usuarios concurrentes → validar cola FIFO + tiempo estimado en UI
- [ ] Test térmico: 30 min de uso continuo en ambiente simulado de 30°C
- [ ] Documentación de operación: re-indexado manual, monitoreo, mantenimiento del índice

---

## 20. Estructura de Directorios y Dependencias

### 20.1 Estructura del AI Engine

```
cdn/
├── server/                   EXISTENTE — cambios mínimos
│   └── src/
│       ├── routes/
│       │   └── ai.ts                          NUEVO
│       ├── controllers/
│       │   └── aiSearchController.ts          NUEVO
│       └── middleware/
│           └── viewerAuth.ts                  NUEVO
│
└── ai_engine/                NUEVO — corre en Jetson Orin NX
    ├── main.py
    ├── requirements.txt
    ├── Dockerfile.jetson      ARM64 + CUDA 11.4
    ├── calibration/
    │   └── peru_educational_es.jsonl   dataset AWQ calibración
    ├── config/
    │   ├── settings.py
    │   └── prompts.py         L1 / L2 / L3 / L4 templates
    ├── routers/
    │   ├── search.py          /api/search + /api/search/stream
    │   ├── voice_search.py    /api/voice-search
    │   ├── ingest.py          /api/ingest
    │   └── health.py          /api/health
    ├── services/
    │   ├── resource_manager.py      semáforo ingesta/inferencia (anti-OOM)
    │   ├── intent_router.py         triaje 4 niveles + detección quechua
    │   ├── hybrid_retriever.py      BM25 + Vector + Cross-Encoder
    │   ├── hyde_expander.py         HyDE query expansion
    │   ├── llm_engine.py            TensorRT-LLM + speculative decoding
    │   ├── grounding_verifier.py    Coverage Score + citas fabricadas
    │   ├── thermal_manager.py       NVPModel dinámico  (OBLIGATORIO)
    │   └── ingestion/
    │       ├── pdf_processor.py     PyMuPDF + Tesseract OCR + thumbnail
    │       ├── video_processor.py   FFmpeg + Whisper Small + thumbnail
    │       ├── thumbnail_generator.py
    │       └── chunker.py           chunking jerárquico
    ├── models/
    │   └── schemas.py         Pydantic models — contrato API
    └── tests/
        ├── test_retrieval.py
        ├── test_grounding.py
        ├── test_stt.py
        └── eval_dataset.jsonl  60 pares pregunta/respuesta-esperada
```

### 20.2 Dependencias Python

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
python-multipart==0.0.9        para recibir audio en multipart/form-data

# Retrieval
chromadb==0.5.0
sentence-transformers==3.0.0   multilingual-e5-small embedding
rank_bm25==0.2.2               BM25 index en memoria
spacy==3.7.4
es-core-news-sm                tokenizador español

# Re-ranker y LLM utilities
transformers==4.41.0
torch==2.3.0+cu118             ARM64 build para Jetson

# LLM Inference
tensorrt-llm==0.10.0           wheel ARM64 específico Jetson

# STT
openai-whisper==20231117       Tiny para STT de consultas; Small para ingesta batch

# Ingesta de documentos
pymupdf==1.24.0                PyMuPDF: texto de PDFs + thumbnail primera página
pytesseract==0.3.10            OCR PDFs escaneados

# Detección de idioma
langdetect==1.0.9              español vs quechua

# Infraestructura
prometheus-client==0.20.0
aiofiles==23.2.0
httpx==0.27.0
diskcache==5.6.3               KV-Cache persistente en disco
```

---

> **Nota — Variante Jetson Orin NX de 8 GB**:
> - Eliminar el draft model 1B → sin speculative decoding
> - Reducir KV-Cache a 0.6 GB y `MAX_CONTEXT_TOKENS` a 1024
> - El resto del sistema funciona igual; la latencia aumenta ~2.5× sin speculative decoding
> - El **Active Heat Sink sigue siendo obligatorio** en ambas variantes
'''

TARGET.write_text(CONTENT, encoding='utf-8')
print(f"OK — {len(CONTENT.splitlines())} líneas escritas en {TARGET}")
