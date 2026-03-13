# Plan de Implementación: Motor de Búsqueda IA para CDN Offline

> **Contexto**: Proyecto GTR-PUCP — CDN educativa offline para escuelas rurales del Perú.  
> **Hardware objetivo**: NVIDIA Jetson Orin NX (16 GB, 1024 CUDA cores, 32 TOPS INT8)  
> **Fecha de revisión**: Febrero 2026  
> **Autor**: Arquitectura diseñada para integración con el stack Node.js/Express/PostgreSQL/Redis existente

---

## Índice

1. [Visión del Sistema](#1-visión-del-sistema)
2. [Arquitectura General de la Pipeline IA](#2-arquitectura-general-de-la-pipeline-ia)
3. [Niveles de Inteligencia (Triaje Adaptativo)](#3-niveles-de-inteligencia-triaje-adaptativo)
4. [Estrategia de Inferencia en Edge (Jetson Orin NX)](#4-estrategia-de-inferencia-en-edge-jetson-orin-nx)
5. [Arquitectura de Datos Vectoriales](#5-arquitectura-de-datos-vectoriales)
6. [Pipeline de Ingesta Multi-modal](#6-pipeline-de-ingesta-multi-modal)
7. [Motor de Recuperación Híbrida (HyDE + BM25 + Vector)](#7-motor-de-recuperación-híbrida-hyde--bm25--vector)
8. [Mecanismo Anti-Alucinación (Grounding Estricto)](#8-mecanismo-anti-alucinación-grounding-estricto)
9. [Contrato de API y Streaming SSE](#9-contrato-de-api-y-streaming-sse)
10. [Integración con el CDN Existente (Node.js → FastAPI)](#10-integración-con-el-cdn-existente-nodejs--fastapi)
11. [Gestión Térmica y Recursos de la Jetson](#11-gestión-térmica-y-recursos-de-la-jetson)
12. [Observabilidad y Métricas](#12-observabilidad-y-métricas)
13. [Plan de Fases de Implementación](#13-plan-de-fases-de-implementación)

---

## 1. Visión del Sistema

### 1.1 Objetivo

Añadir una capa de inteligencia artificial **completamente offline** al CDN existente que permita a estudiantes y docentes hacer preguntas en lenguaje natural sobre el contenido almacenado en la red local, recibiendo tanto una respuesta sintetizada como los archivos fuente relevantes con navegación directa.

### 1.2 Principios de Diseño

| Principio | Implementación |
|-----------|----------------|
| **Offline-First absoluto** | Ninguna inferencia, embedding ni recuperación toca Internet |
| **Progresivo** | La búsqueda tradicional del CDN sigue funcionando; la IA es una capa encima |
| **Latencia tolerable** | < 3 segundos para primer token, < 15 s para respuesta completa en Jetson |
| **Sin degradación de CDN** | El servicio IA corre en proceso separado (FastAPI :8000), aislado del Express :3000 |
| **Trazabilidad** | Cada afirmación de la IA se ancla a fragmentos específicos de la CDN |
| **Multimodal** | Indexa texto de PDFs, transcripción de audio/video, OCR de imágenes |

### 1.3 Diferencias Clave con el Plan Original

| Aspecto | Plan Original | Este Plan |
|---------|---------------|-----------|
| Enrutamiento | Binario (L1/L2) | Triaje de 4 niveles con score de confianza |
| Retrieval | RAG básico | HyDE + BM25 + Vector + Re-ranker cross-encoder |
| Modelo | Llama 3 genérico | Speculative decoding: borrador 1B + objetivo 8B |
| Respuesta | JSON bloqueante | Streaming SSE con citas inline progresivas |
| Ingesta | Manual | Hook automático en el pipeline de upload existente |
| Contenido | Solo texto | Transcripción Whisper de video, OCR de PDFs escaneados |
| Alucinaciones | Prompt engineering | Verificación formal: coverage score + contradiction detection |
| Térmico | Sin mención | Gestor adaptativo de carga según temperatura Jetson |
| Idioma | Solo español | Detección automática español/quechua |

---

## 2. Arquitectura General de la Pipeline IA

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          CLIENTE (React Browser)                             ║
║  [Barra de búsqueda] ──────── query text ──────────────────────────────────  ║
╚══════════════════════════════════════════════╦═══════════════════════════════╝
                                               ║ HTTP/SSE
                                               ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║              CDN BACKEND (Node.js/Express :3000)  ← EXISTENTE               ║
║  /api/search/ai  ──── proxy + auth middleware ──────────────────────────────  ║
╚══════════════════════════════════════════════╦═══════════════════════════════╝
                                               ║ HTTP forward (internal LAN)
                                               ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║         AI ENGINE (Python/FastAPI :8000) — NVIDIA Jetson Orin NX NUEVO      ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │                    ADAPTIVE INTENT ROUTER                           │     ║
║  │  query → [Embedding rápido E5-small] → Triaje de 4 niveles          │     ║
║  └───────────────┬──────────────────────┬────────────────┬─────────────┘     ║
║                  │                      │                │                   ║
║                  ▼                      ▼                ▼                   ║
║  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           ║
║  │   L1: CDN RAG    │  │  L2: Hybrid RAG  │  │  L3: Pure LLM    │           ║
║  │  (Alta confianza)│  │ (Confianza media)│  │  (Conocimiento   │           ║
║  │                  │  │                  │  │   base general)  │           ║
║  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘           ║
║           │                     │                      │                    ║
║           └─────────────────────┴──────────────────────┘                    ║
║                                         │                                   ║
║                                         ▼                                   ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │                 HYBRID RETRIEVER                                    │     ║
║  │  ChromaDB (vectors) + BM25 (keywords) + PostgreSQL FTS              │     ║
║  │  → Cross-Encoder Re-ranker → Top-K chunks                           │     ║
║  └───────────────────────────────┬─────────────────────────────────────┘     ║
║                                  │                                           ║
║                                  ▼                                           ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │              SPECULATIVE DECODER (TensorRT-LLM)                     │     ║
║  │  Draft model: Llama-3.2-1B-Instruct (INT4 → 2.1 GB VRAM)           │     ║
║  │  Target model: Llama-3.1-8B-Instruct (INT4 → 6.2 GB VRAM)          │     ║
║  │  → 2.8× speed-up promedio vs autoregressive puro                    │     ║
║  └───────────────────────────────┬─────────────────────────────────────┘     ║
║                                  │                                           ║
║                                  ▼                                           ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │              GROUNDING VERIFIER                                     │     ║
║  │  Coverage Score + Contradiction Detector → Filtra citas fantasma    │     ║
║  └───────────────────────────────┬─────────────────────────────────────┘     ║
║                                  │ SSE chunks                               ║
╚══════════════════════════════════╪═════════════════════════════════════════╝
                                   │
                                   ▼ JSON + SSE stream
                              Cliente React
```

---

## 3. Niveles de Inteligencia (Triaje Adaptativo)

A diferencia del modelo binario original (L1/L2), se propone un **triaje de 4 niveles** basado en un score de confianza continuo calculado antes de la inferencia.

### 3.1 Cálculo del Score de Confianza de Recuperación (RCS)

```python
# Pseudocódigo del Intent Router
async def route_query(query: str) -> RoutingDecision:
    # 1. Embedding rápido con modelo ligero (< 50ms en Jetson)
    query_emb = await embed_fast(query)          # intfloat/multilingual-e5-small

    # 2. Búsqueda aproximada en ChromaDB (top-5, sin re-ranking aún)
    candidates = await chroma.query(query_emb, n_results=5)

    # 3. Score de confianza = promedio de similitudes coseno del top-3
    rcs = mean(candidates.distances[:3])         # 0.0 – 1.0

    # 4. Conteo de resultados PostgreSQL FTS como señal adicional
    fts_count = await pg_fts_count(query)

    # 5. Clasificación por umbrales calibrados
    if rcs >= 0.78 and fts_count >= 2:
        return Level.L1_CDN_STRICT            # Solo fuentes CDN, sin creación libre
    elif rcs >= 0.55 or fts_count >= 1:
        return Level.L2_CDN_AUGMENTED         # RAG + relleno con conocimiento base
    elif is_educational_domain(query):
        return Level.L3_GENERAL_KNOWLEDGE     # Solo base del modelo, sin CDN
    else:
        return Level.L4_CLARIFICATION         # Pedir reformulación al usuario
```

### 3.2 Comportamiento por Nivel

| Nivel | Condición | Comportamiento del Sistema |
|-------|-----------|---------------------------|
| **L1 CDN Strict** | RCS ≥ 0.78 + FTS ≥ 2 | Respuesta anclada 100% a la CDN. Prompt con restricción hard: "Solo usa la información de los documentos siguientes. Si no encuentras la respuesta, di explícitamente que no está disponible en la red local." |
| **L2 CDN Augmented** | RCS ≥ 0.55 o FTS ≥ 1 | RAG con documentos CDN + completado con conocimiento base. Cada afirmación etiquetada como `[CDN]` o `[Base]` |
| **L3 Knowledge Only** | Dominio educativo detectado, sin match CDN | Respuesta de modelo puro. Aviso al usuario: "Esta respuesta usa conocimiento general del modelo. No se encontraron recursos en la red local." |
| **L4 Clarification** | Query ambigua + RCS < 0.40 | El motor devuelve 2-3 preguntas aclaratorias en lugar de generar una respuesta especulativa |

---

## 4. Estrategia de Inferencia en Edge (Jetson Orin NX)

### 4.1 Distribución de Memoria Planificada

```
Jetson Orin NX — 16 GB unified memory
├── Sistema operativo + servicios (Ubuntu 22.04 + Docker)   : ~2.5 GB
├── FastAPI + Python runtime + ChromaDB en memoria         : ~1.8 GB
├── Modelo de embedding (multilingual-e5-small, FP16)      : ~0.5 GB
├── Draft model Llama-3.2-1B-Instruct (INT4 GPTQ)          : ~2.1 GB
├── Target model Llama-3.1-8B-Instruct (INT4 GPTQ)         : ~6.2 GB
├── KV-Cache dinámico                                       : ~2.0 GB
└── Buffer / overhead                                       : ~0.9 GB
                                                   TOTAL : 16.0 GB ✓
```

### 4.2 Cadena de Optimización TensorRT-LLM

```bash
# Paso 1: Convertir pesos Llama a formato TensorRT-LLM
python convert_checkpoint.py \
    --model_dir ./hf_models/Llama-3.1-8B-Instruct \
    --output_dir ./trt_checkpoints/llama31-8b \
    --dtype float16

# Paso 2: Cuantización INT4 AWQ (Activation-aware Weight Quantization)
# AWQ minimiza el error de cuantización preservando los canales de mayor magnitud
python quantize.py \
    --model_dir ./hf_models/Llama-3.1-8B-Instruct \
    --output_dir ./trt_checkpoints/llama31-8b-int4 \
    --qformat int4_awq \
    --calib_size 512 \
    --calib_dataset ./calibration/educational_es.jsonl  # ← dataset de dominio educativo en español

# Paso 3: Compilar engine TensorRT con parámetros Jetson
trtllm-build \
    --checkpoint_dir ./trt_checkpoints/llama31-8b-int4 \
    --output_dir ./trt_engines/llama31-8b-int4 \
    --gemm_plugin auto \
    --gpt_attention_plugin auto \
    --max_batch_size 2 \
    --max_input_len 3072 \
    --max_seq_len 4096 \
    --max_num_tokens 4096 \
    --use_paged_context_fmha enable \  # ← Reduce memoria KV-Cache
    --speculative_decoding_mode draft_tokens_external  # ← Habilita speculative decoding
```

### 4.3 Speculative Decoding: Por qué es clave en Jetson

En inferencia autoregresiva normal, cada token requiere un forward pass completo del modelo grande (8B). El **speculative decoding** usa el modelo pequeño (1B) para proponer N tokens en paralelo y el modelo grande los verifica todos en un solo forward pass.

```
Sin speculative decoding:
  Token 1 → [8B forward] → Token 2 → [8B forward] → Token 3 ...
  Latencia: N × t_grande

Con speculative decoding (γ=5 tokens de borrador):
  [1B: propone tokens 1-5] → [8B: verifica 5 tokens en 1 forward] → acepta k≥3
  Latencia: (N/k) × t_grande + (N/k) × t_pequeño
  Speed-up estimado: 2.5× – 3.2× en Jetson Orin NX
```

### 4.4 Configuración de Contexto y Prompting

```python
SYSTEM_PROMPT_L1 = """Eres un asistente educativo experto que opera en una red local
sin Internet. Analiza ÚNICAMENTE los fragmentos de la CDN que se proporcionan a
continuación. NO inventes información. Si una afirmación no está soportada por los
fragmentos, omítela. Responde siempre en español claro y conciso, apropiado para
estudiantes de secundaria de Perú."""

SYSTEM_PROMPT_L2 = """Eres un asistente educativo. Combina la información de los
fragmentos de la CDN local (marcados [CDN]) con tu conocimiento base (marcado [Base]).
Distingue visualmente ambas fuentes. Responde en español."""

# Límites de contexto
MAX_CONTEXT_TOKENS = 2048   # para los chunks recuperados
MAX_GENERATION_TOKENS = 512  # respuesta overview
```

---

## 5. Arquitectura de Datos Vectoriales

### 5.1 ChromaDB: Elección Justificada vs. Milvus

| Criterio | ChromaDB | Milvus |
|----------|----------|--------|
| Setup en Jetson | Single binary, 0 dependencias | Requiere Kubernetes/Docker compose complejo |
| RAM idle | ~150 MB | ~800 MB |
| Queries/seg (1M vecs) | ~200 QPS | ~2,000 QPS |
| Persistencia | SQLite embedded | Servidor dedicado |
| **Veredicto** | ✅ **Elegido** — perfecto para < 100K docs | Para escala > 500K docs, migrar |

### 5.2 Esquema de Colecciones ChromaDB

```python
# Colección principal: fragmentos de documentos CDN
chroma_client.create_collection(
    name="cdn_chunks",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,
        "hnsw:M": 32                    # balance calidad/memoria
    },
    embedding_function=LocalEmbeddingFunction()  # sin llamadas externas
)

# Estructura de metadata por chunk
chunk_metadata = {
    "content_id": "uuid-del-contenido-en-postgresql",
    "content_type": "video" | "pdf" | "audio" | "document",
    "title": "Números Reales - Clase 3",
    "category": "matematicas",
    "chunk_index": 4,            # posición en el documento
    "total_chunks": 23,
    "source_type": "transcript" | "pdf_text" | "pdf_ocr" | "description",
    "timestamp_start": 142.5,    # segundos (solo para video/audio)
    "timestamp_end": 189.0,
    "url_path": "/api/content/stream/uuid",
    "thumbnail_url": "/storage/thumbnails/uuid.jpg",
    "language": "es" | "qu",    # español o quechua
    "created_at": "2026-02-15T10:30:00Z"
}
```

### 5.3 Estrategia de Chunking Jerárquico

No todos los fragmentos deben tener el mismo tamaño. Se propone un esquema de **tres niveles de granularidad**:

```
NIVEL DOCUMENTO (para retrieval inicial — representación densa del contenido completo)
  └── chunk_type: "summary"
      size: 256 tokens
      uso: vectorizar el resumen generado del contenido completo

NIVEL SECCIÓN (para contexto — párrafos o capítulos)
  └── chunk_type: "section"
      size: 512 tokens, overlap: 64 tokens
      uso: recuperar secciones temáticas coherentes

NIVEL ORACIÓN (para grounding — anclar citas precisas)
  └── chunk_type: "sentence"
      size: 128 tokens
      uso: verificar afirmaciones, mostrar citas exactas al usuario
```

**Ventaja**: El retrieval usa resúmenes de documento para el ranking inicial (rápido, menor ruido) y luego baja a nivel oración para grounding fino (preciso, verificable).

---

## 6. Pipeline de Ingesta Multi-modal

### 6.1 Hook Automático en el CDN Existente

La ingesta se dispara automáticamente cuando el `uploadController.ts` existente cambia el estado de un contenido a `active`. Se agrega una llamada al AI Engine sin modificar la lógica core:

```typescript
// server/src/controllers/uploadController.ts — AGREGAR al final de processingComplete()
async function notifyAIEngineForIndexing(contentId: string): Promise<void> {
  const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
  try {
    await fetch(`${AI_ENGINE_URL}/api/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId }),
    });
    console.log(`[AI] Ingesta solicitada para content_id: ${contentId}`);
  } catch (err) {
    // Non-fatal: la búsqueda textual sigue funcionando aunque la IA no indexe
    console.warn(`[AI] Engine no disponible, ingesta diferida: ${err}`);
  }
}
```

### 6.2 Pipeline de Procesamiento por Tipo de Contenido

```
╔═══════════════════════════════════════════════════════╗
║              INGESTA PIPELINE (FastAPI worker)         ║
╠═══════════════╦═══════════════════════════════════════╣
║   VIDEO/AUDIO ║                                       ║
║               ║  1. Extrae audio → FFmpeg              ║
║               ║  2. Transcripción → Whisper tiny.en   ║
║               ║     (modelo 39MB, corre en CPU Orin)  ║
║               ║  3. Segmenta por pausas (VAD)          ║
║               ║  4. Chunk por segmento (max 30s)       ║
║               ║  5. Embed cada chunk → ChromaDB        ║
╠═══════════════╬═══════════════════════════════════════╣
║      PDF      ║                                       ║
║               ║  1. Extrae texto → PyMuPDF             ║
║               ║  2. Si texto < 100 chars/pág → OCR    ║
║               ║     (Tesseract 5 con modelo español)  ║
║               ║  3. Chunk por párrafos + overlap       ║
║               ║  4. Embed → ChromaDB                   ║
╠═══════════════╬═══════════════════════════════════════╣
║   THUMBNAILS  ║                                       ║
║               ║  1. BLIP-2 caption (opcional, pesado) ║
║               ║  2. Alt-text → metadata del chunk     ║
╚═══════════════╩═══════════════════════════════════════╝
```

### 6.3 Estimación de Tiempo de Ingesta

| Tipo | Duración/Tamaño | Tiempo en Jetson |
|------|----------------|------------------|
| Video 10 min | ~150 MB | ~45 s (Whisper tiny) |
| PDF 50 páginas texto | ~2 MB | ~8 s |
| PDF 50 páginas escaneado | ~15 MB | ~120 s (OCR) |
| Audio 30 min | ~45 MB | ~90 s |

La ingesta es asíncrona y no bloquea el CDN.

---

## 7. Motor de Recuperación Híbrida (HyDE + BM25 + Vector)

### 7.1 Flujo de Recuperación en 4 Pasos

**Paso 1 — HyDE (Hypothetical Document Embeddings)**

Antes de buscar en el índice vectorial, se usa el modelo pequeño (1B) para generar un "documento hipotético" que respondería a la pregunta. El embedding de ese documento es más similar a los documentos reales que el embedding de la pregunta sola.

```python
async def hyde_expand(query: str) -> str:
    """Genera un pasaje educativo hipotético que respondería a la query."""
    prompt = f"Escribe un párrafo educativo breve (5 oraciones) sobre: {query}"
    hypothetical_doc = await draft_model.generate(prompt, max_tokens=150)
    return hypothetical_doc

# El embedding del documento hipotético se combina con el de la query
query_emb = 0.6 * embed(query) + 0.4 * embed(hypothetical_doc)  # interpolación
```

**Paso 2 — Búsqueda Paralela: Vector + BM25**

```python
async def hybrid_search(query: str, query_emb: np.ndarray, top_k: int = 20):
    # Vector search en ChromaDB
    vector_results = await chroma.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where={"chunk_type": {"$in": ["section", "summary"]}}
    )

    # BM25 keyword search (índice en memoria con rank_bm25)
    tokenized_query = spanish_tokenizer.tokenize(query)  # con stopwords español
    bm25_scores = bm25_index.get_scores(tokenized_query)
    bm25_top_k = np.argsort(bm25_scores)[-top_k:][::-1]

    # Fusión por Reciprocal Rank Fusion (RRF)
    return rrf_merge(vector_results, bm25_results, k=60)
```

**Paso 3 — Re-ranking con Cross-Encoder**

El re-ranker evalúa cada (query, chunk) como par, en lugar de embeddings independientes — mucho más preciso pero más lento. Se aplica solo a los top-20 candidatos de RRF.

```python
# Modelo: ms-marco-MiniLM-L-6-v2 (22MB, rápido en CPU)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scored = reranker.predict([(query, chunk.text) for chunk in candidates])
top_5_chunks = sorted(zip(scored, candidates), reverse=True)[:5]
```

**Paso 4 — Ensamblaje de Contexto con Metadata**

```python
def build_context(chunks: list[Chunk]) -> str:
    """Ensambla el contexto con metadatos estructurados para el LLM."""
    ctx_parts = []
    for i, chunk in enumerate(chunks):
        ctx_parts.append(f"""
[FUENTE {i+1}]
Título: {chunk.metadata['title']}
Tipo: {chunk.metadata['content_type']}
Categoría: {chunk.metadata['category']}
{f"Tiempo: {chunk.metadata['timestamp_start']:.0f}s – {chunk.metadata['timestamp_end']:.0f}s" 
  if chunk.metadata.get('timestamp_start') else ""}
Fragmento: {chunk.text}
---""")
    return "\n".join(ctx_parts)
```

---

## 8. Mecanismo Anti-Alucinación (Grounding Estricto)

### 8.1 Verificación Post-Generación: Coverage Score

Después de generar la respuesta, se verifica cuántas oraciones de la respuesta están soportadas por los chunks recuperados:

```python
async def verify_grounding(response: str, chunks: list[Chunk]) -> GroundingReport:
    sentences = split_sentences(response)
    sentence_scores = []

    for sentence in sentences:
        # Embedding de la oración de respuesta
        sent_emb = embed(sentence)
        # Similitud máxima con algún chunk fuente
        max_sim = max(cosine_similarity(sent_emb, embed(c.text)) for c in chunks)
        sentence_scores.append(GroundingScore(sentence=sentence, score=max_sim))

    coverage = mean(s.score for s in sentence_scores)

    return GroundingReport(
        coverage_score=coverage,
        # Oraciones con score < 0.45 se marcan como no verificadas
        unverified_sentences=[s for s in sentence_scores if s.score < 0.45],
        is_grounded=(coverage >= 0.60)
    )
```

### 8.2 Acciones por Score de Grounding

| Coverage Score | Acción |
|----------------|--------|
| ≥ 0.80 | Respuesta devuelta normalmente. Badge "Verificado con fuentes CDN" |
| 0.60 – 0.79 | Respuesta con aviso: "Algunas afirmaciones pueden ser de conocimiento general" |
| 0.45 – 0.59 | Oraciones no verificadas eliminadas del output. Advertencia visible |
| < 0.45 en L1 | Respuesta bloqueada. Se devuelve: "No hay suficiente información en la red local sobre este tema." |

### 8.3 Prompt Anti-Alucinación para L1

```python
L1_PROMPT_TEMPLATE = """
<|system|>
{system_prompt}

REGLA CRÍTICA: Puedes ÚNICAMENTE usar información de los fragmentos marcados como
[FUENTE N]. Si un dato no aparece en ninguna fuente, NO lo incluyas en tu respuesta.
Termina tu respuesta con la sección [FUENTES USADAS] listando los números de fuente
que utilizaste (ej: [FUENTES USADAS: 1, 3]).
<|end|>

<|context|>
{assembled_context}
<|end|>

<|user|>
{query}
<|end|>

<|assistant|>
"""
```

El campo `[FUENTES USADAS: ...]` permite verificar automáticamente qué chunks citó el modelo y comparar con los chunks que realmente existen, detectando citas fabricadas.

---

## 9. Contrato de API y Streaming SSE

### 9.1 Endpoint Principal: POST /api/ai/search

```http
POST http://cdn-server:3000/api/ai/search
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: text/event-stream

{
  "query": "¿Cómo se resuelven ecuaciones de segundo grado?",
  "context": {
    "user_role": "student",
    "current_category": "matematicas",
    "session_history": ["factorización", "polinomios"]   // últimas queries para contexto
  },
  "options": {
    "streaming": true,        // SSE o JSON bloqueante
    "max_sources": 5,
    "language": "auto"        // auto-detecta español/quechua
  }
}
```

### 9.2 Respuesta JSON Final (sin streaming)

```json
{
  "request_id": "f7e2a1b4-...",
  "routing": {
    "level": "L1_CDN_STRICT",
    "confidence": 0.84,
    "retrieval_time_ms": 142,
    "generation_time_ms": 3210
  },
  "overview": {
    "text": "Las ecuaciones de segundo grado se resuelven aplicando la fórmula cuadrática: x = (−b ± √(b²−4ac)) / 2a. En el Módulo 4 de la clase 'Álgebra Básica' se detalla cada paso con ejemplos. El discriminante (b²−4ac) determina el número de soluciones reales.",
    "grounding": {
      "coverage_score": 0.91,
      "is_verified": true,
      "unverified_count": 0
    },
    "language_detected": "es"
  },
  "sources": [
    {
      "rank": 1,
      "content_id": "uuid-123",
      "title": "Álgebra Básica - Módulo 4: Ecuaciones Cuadráticas",
      "type": "video",
      "category": "matematicas",
      "url": "/api/content/stream/uuid-123",
      "thumbnail_url": "/storage/thumbnails/uuid-123.jpg",
      "relevance_score": 0.92,
      "snippet": "...aplicamos la fórmula general x = (-b ± √Δ) / 2a donde el discriminante Δ = b²-4ac nos indica...",
      "timestamp_start": 142,
      "timestamp_end": 189,
      "deep_link": "/api/content/stream/uuid-123?t=142"
    },
    {
      "rank": 2,
      "content_id": "uuid-456",
      "title": "Guía de Estudio: Ecuaciones de 2do Grado",
      "type": "pdf",
      "category": "matematicas",
      "url": "/api/content/uuid-456/download",
      "thumbnail_url": "/storage/thumbnails/uuid-456.jpg",
      "relevance_score": 0.87,
      "snippet": "La factorización es el método alternativo más eficiente cuando el discriminante es un cuadrado perfecto...",
      "timestamp_start": null,
      "timestamp_end": null,
      "deep_link": "/api/content/uuid-456/view?page=12"
    }
  ],
  "ui_hints": {
    "show_sources_panel": true,
    "highlight_timestamps": true,
    "suggested_queries": [
      "¿Qué es el discriminante?",
      "Ejemplos de ecuaciones sin solución real"
    ]
  }
}
```

### 9.3 Protocolo SSE (Streaming)

```
event: routing
data: {"level":"L1_CDN_STRICT","confidence":0.84}

event: source
data: {"rank":1,"content_id":"uuid-123","title":"Álgebra Básica - Módulo 4","type":"video","relevance_score":0.92,"snippet":"...fórmula general x = (-b ± √Δ)...","deep_link":"/api/content/stream/uuid-123?t=142"}

event: source
data: {"rank":2,"content_id":"uuid-456","title":"Guía de Estudio: Ecuaciones","type":"pdf","relevance_score":0.87,"snippet":"La factorización es el método alternativo...","deep_link":"/api/content/uuid-456/view?page=12"}

event: token
data: {"text":"Las "}

event: token
data: {"text":"ecuaciones "}

event: token
data: {"text":"de segundo grado "}

... (tokens progresivos del LLM, ~50ms entre tokens en Jetson)

event: grounding
data: {"coverage_score":0.91,"is_verified":true}

event: done
data: {"total_time_ms":3890,"tokens_generated":97}
```

**Ventaja de SSE**: El frontend puede renderizar las fuentes CDN inmediatamente (en ~150ms tras la búsqueda vectorial) mientras el texto de IA llega progresivamente. El usuario ve contenido útil sin esperar la generación completa.

### 9.4 Formato de Error Estandarizado

```json
{
  "error": {
    "code": "GROUNDING_INSUFFICIENT",
    "level": "L1",
    "message": "No hay suficiente información en la red local sobre este tema.",
    "coverage_score": 0.31,
    "fallback_action": "SHOW_GENERAL_SEARCH",
    "suggested_queries": ["buscar en categoría matemáticas", "ver contenido disponible"]
  }
}
```

---

## 10. Integración con el CDN Existente (Node.js → FastAPI)

### 10.1 Nueva Ruta en Express (proxy con auth)

```typescript
// server/src/routes/ai.ts  [NUEVO]
import express from 'express';
import { authMiddleware } from '../middleware/auth.js';
import { aiSearchController } from '../controllers/aiSearchController.js';

const router = express.Router();

// Requiere autenticación — mismo JWT del sistema existente
router.post('/search', authMiddleware, aiSearchController.search);
router.get('/search/stream', authMiddleware, aiSearchController.searchStream);
router.get('/health', aiSearchController.health);

export default router;
```

```typescript
// server/src/controllers/aiSearchController.ts  [NUEVO]
export const aiSearchController = {
  async search(req, res) {
    const { query, context, options } = req.body;
    const AI_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';

    if (options?.streaming) {
      // Configurar headers SSE
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      // Proxy del stream de FastAPI → cliente
      const upstream = await fetch(`${AI_URL}/api/search/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, context, user_id: req.user.id }),
      });

      upstream.body!.pipeTo(
        new WritableStream({
          write(chunk) { res.write(chunk); },
          close() { res.end(); }
        })
      );
    } else {
      // JSON bloqueante
      const result = await fetch(`${AI_URL}/api/search`, { ... });
      res.json(await result.json());
    }
  }
};
```

### 10.2 Registro en index.ts existente (cambio mínimo)

```typescript
// server/src/index.ts — AGREGAR (las 2 líneas marcadas)
import aiRoutes from './routes/ai.js';                    // ← AGREGAR

// ...existing routes...
app.use('/api/auth', authRoutes);
app.use('/api/categories', categoryRoutes);
app.use('/api/content', contentRoutes);
app.use('/api/upload', uploadRoutes);
app.use('/api/ai', aiRoutes);                             // ← AGREGAR
```

---

## 11. Gestión Térmica y Recursos de la Jetson

### 11.1 Perfiles de Potencia Adaptativos

La Jetson Orin NX puede ejecutarse en varios perfiles de potencia (NVPModel). El gestor térmico del AI Engine ajusta el perfil dinámicamente:

```python
# ai_engine/thermal_manager.py
import subprocess
import asyncio

THERMAL_THRESHOLDS = {
    "nominal":   {"max_temp": 55, "nvp_mode": 4, "batch_size": 2, "draft_tokens": 5},
    "warm":      {"max_temp": 68, "nvp_mode": 3, "batch_size": 1, "draft_tokens": 4},
    "hot":       {"max_temp": 78, "nvp_mode": 2, "batch_size": 1, "draft_tokens": 3},
    "critical":  {"max_temp": 999, "nvp_mode": 1, "batch_size": 1, "draft_tokens": 2},
}

async def get_soc_temperature() -> float:
    """Lee temperatura del SoC desde sysfs."""
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read()) / 1000.0

async def thermal_governor():
    """Loop de control térmico cada 10 segundos."""
    while True:
        temp = await get_soc_temperature()
        for profile_name, cfg in THERMAL_THRESHOLDS.items():
            if temp < cfg["max_temp"]:
                await apply_nvp_mode(cfg["nvp_mode"])
                update_inference_config(
                    batch_size=cfg["batch_size"],
                    draft_gamma=cfg["draft_tokens"]
                )
                break
        await asyncio.sleep(10)
```

### 11.2 Tabla de Rendimiento por Perfil

| Perfil | Temp. SoC | Potencia | Tokens/seg | Latencia respuesta |
|--------|-----------|----------|------------|--------------------|
| Nominal | < 55°C | ~15W | ~35 tok/s | ~8 s (256 tok) |
| Warm | < 68°C | ~12W | ~28 tok/s | ~10 s |
| Hot | < 78°C | ~9W | ~20 tok/s | ~13 s |
| Critical | ≥ 78°C | ~7W | ~14 tok/s | ~18 s + aviso UI |

### 11.3 KV-Cache Persistente entre Consultas

Para preguntas frecuentes (ej. "¿Qué es fotosíntesis?"), el sistema prefix-cache el prompt del sistema + contexto frecuente, reduciendo los tokens a procesar en un ~40%:

```python
# Cache de prefijos usando DiskLRU (sobrevive reinicios)
kv_cache = DiskLRU(
    cache_dir="/tmp/kv_prefix_cache",
    max_size_gb=1.5,
    ttl_hours=24
)

async def get_or_generate(prompt_hash: str, full_prompt: str) -> Response:
    cached = kv_cache.get(prompt_hash)
    if cached:
        # Solo genera los tokens nuevos desde el estado KV cacheado
        return await engine.generate_from_kv_state(cached, max_new_tokens=512)
    response = await engine.generate(full_prompt, max_new_tokens=512)
    kv_cache.set(prompt_hash, response.kv_state)
    return response
```

---

## 12. Observabilidad y Métricas

### 12.1 Métricas Clave a Monitorear

```python
# Prometheus metrics para el AI Engine
from prometheus_client import Histogram, Counter, Gauge

# Latencias
RETRIEVAL_LATENCY = Histogram('ai_retrieval_seconds', 'Tiempo de retrieval híbrido',
                               buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0])
GENERATION_LATENCY = Histogram('ai_generation_seconds', 'Tiempo de generación LLM',
                                buckets=[2, 5, 10, 15, 30])

# Calidad
COVERAGE_SCORE = Histogram('ai_grounding_coverage', 'Coverage score del grounding',
                             buckets=[0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
ROUTING_LEVEL = Counter('ai_routing_decisions_total', 'Decisiones de enrutamiento',
                         labelnames=['level'])   # L1, L2, L3, L4

# Recursos Jetson
JETSON_TEMP = Gauge('jetson_soc_temperature_celsius', 'Temperatura SoC Jetson')
JETSON_GPU_UTIL = Gauge('jetson_gpu_utilization_percent', 'Utilización GPU Jetson')
KV_CACHE_HITS = Counter('ai_kv_cache_hits_total', 'Cache KV hits')
```

### 12.2 Dashboard de Salud (Endpoint /api/ai/health)

```json
{
  "status": "healthy",
  "jetson": {
    "soc_temp_celsius": 52.3,
    "gpu_utilization_pct": 34,
    "active_profile": "nominal",
    "free_memory_gb": 3.2
  },
  "models": {
    "draft_model": "loaded",
    "target_model": "loaded",
    "embedder": "loaded"
  },
  "index": {
    "total_chunks": 12847,
    "total_documents": 284,
    "last_ingestion": "2026-02-22T14:30:00Z",
    "pending_ingestion": 0
  },
  "performance": {
    "avg_retrieval_ms": 138,
    "avg_generation_ms": 3240,
    "avg_coverage_score": 0.84,
    "cache_hit_rate": 0.23
  }
}
```

---

## 13. Plan de Fases de Implementación

> **Estado al 3 de marzo 2026** — El AI Engine está operativo en modo desarrollo (PC/laptop).
> Los servicios implementados funcionan en CPU con Phi-3.5-mini-instruct.
> Pendiente: compilación TRT-LLM para Jetson + speculative decoding.

### Semana 1-2: Fundación de Datos
- [x] FastAPI app operativa con SSE streaming (puerto 8000)
- [x] ChromaDB + embeddings `multilingual-e5-small` integrados en `hybrid_retriever.py`
- [x] BM25 con spaCy `es_core_news_md` funcionando
- [x] Pipeline de ingesta PDF/video implementado (`ai_engine/services/ingestion/`)
- [x] Whisper para STT implementado en `stt.py`
- [ ] Ingesta masiva de documentos CDN pendiente (sin contenido real aún)
- [ ] Tests unitarios del chunking jerárquico

### Semana 3-4: Motor de Retrieval
- [x] BM25 index con tokenizador español
- [x] Cross-encoder re-ranker integrado en `hybrid_retriever.py`
- [ ] HyDE query expansion (pendiente)
- [ ] Benchmark de latencia de retrieval (objetivo < 200ms)

### Semana 5-6: Inferencia y Engine
- [x] `llm_engine.py` con HF fallback funcionando (Phi-3.5-mini-instruct en CPU)
- [x] `settings.py` multi-plataforma (laptop / orin_nx_16gb / agx_orin)
- [x] `thermal_manager.py` implementado
- [ ] Compilar engine TRT-LLM para Jetson (requiere hardware)
- [ ] Speculative decoding con γ=5
- [ ] Benchmark tokens/segundo en Jetson

### Semana 7-8: Integración y API
- [x] FastAPI con todos los endpoints (search, ingest, health, voice-search)
- [x] SSE streaming implementado y funcionando en el frontend
- [x] Hook de ingesta automática en `uploadController.ts`
- [x] Routes en Express con proxy al AI Engine
- [ ] Tests de integración end-to-end

### Semana 9: Grounding y QA
- [ ] Coverage Score verificator
- [ ] Dataset de evaluación: 50 preguntas con ground truth
- [ ] Ajuste de umbrales de routing (RCS_L1, RCS_L2)
- [ ] Test de carga: 10 consultas concurrentes en Jetson
- [ ] Documentación de operación

---

## Estructura de Directorios del AI Engine

```
cdn/
└── ai_engine/                    [NUEVO directorio]
    ├── main.py                   FastAPI app entry point
    ├── requirements.txt
    ├── Dockerfile.jetson          ARM64 + CUDA 11.4
    ├── config/
    │   ├── settings.py            Configuración centralizada
    │   └── prompts.py             Templates de prompts por nivel
    ├── routers/
    │   ├── search.py              /api/search + /api/search/stream
    │   ├── ingest.py              /api/ingest
    │   └── health.py              /api/health
    ├── services/
    │   ├── intent_router.py       Triaje de 4 niveles
    │   ├── hybrid_retriever.py    BM25 + Vector + Re-ranker
    │   ├── hyde_expander.py       HyDE query expansion
    │   ├── llm_engine.py          TensorRT-LLM wrapper + speculative decoding
    │   ├── grounding_verifier.py  Coverage Score + citation checker
    │   ├── ingestion/
    │   │   ├── pdf_processor.py   PyMuPDF + Tesseract OCR
    │   │   ├── video_processor.py FFmpeg + Whisper
    │   │   └── chunker.py         Chunking jerárquico
    │   └── thermal_manager.py     Gestor térmico Jetson
    ├── models/
    │   └── schemas.py             Pydantic models (API contract)
    └── tests/
        ├── test_retrieval.py
        ├── test_grounding.py
        └── eval_dataset.jsonl     50 preguntas con ground truth
```

---

## Resumen de Dependencias Python

```txt
# requirements.txt — ai_engine
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
chromadb==0.5.0
sentence-transformers==3.0.0          # multilingual-e5-small embeddings
rank_bm25==0.2.2                       # BM25 index
spacy==3.7.4                           # Tokenización español
es-core-news-sm @ https://...          # Modelo spaCy español
transformers==4.41.0                    # Cross-encoder re-ranker
torch==2.3.0+cu118                     # ARM64 build para Jetson
tensorrt-llm==0.10.0                   # TensorRT-LLM (ARM64 wheel específico Jetson)
openai-whisper==20231117               # Transcripción offline
pymupdf==1.24.0                        # Extracción texto PDF
pytesseract==0.3.10                    # OCR para PDFs escaneados
prometheus-client==0.20.0             # Métricas
aiofiles==23.2.0                       # I/O asíncrono
httpx==0.27.0                          # Cliente HTTP async
diskcache==5.6.3                       # KV-Cache persistente en disco
```

---

> **Nota de hardware**: Todo lo descrito asume una **Jetson Orin NX de 16 GB**. Para la variante de 8 GB, se recomienda:
> - Usar solo el target model (8B INT4, sin draft model 1B simultáneo)
> - Reducir el KV-Cache a 0.8 GB
> - Limitar `max_context_tokens` a 1536
> Se pierde el speed-up de speculative decoding pero el resto del sistema funciona igual.
