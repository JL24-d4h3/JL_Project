# Comparación Técnica: Familia Jetson para Motor de Búsqueda IA
## CDN Educativa Offline GTR-PUCP — Selección de Plataforma

> **Audiencia**: Equipo técnico del proyecto.
> **Fecha**: Febrero 2026
> **Propósito**: Evaluar todas las plataformas Jetson relevantes para dos escenarios:
> **A)** Banco de pruebas / desarrollo activo  **B)** Prototipo final / despliegue en escuela

---

## Índice

1. [Especificaciones de Hardware — Todas las Plataformas](#1-especificaciones-de-hardware--todas-las-plataformas)
2. [Matriz de Compatibilidad de Software](#2-matriz-de-compatibilidad-de-software)
3. [Presupuesto de Memoria por Plataforma](#3-presupuesto-de-memoria-por-plataforma)
4. [Estrategia de Inferencia LLM por Plataforma](#4-estrategia-de-inferencia-llm-por-plataforma)
5. [Pipeline de Retrieval por Plataforma](#5-pipeline-de-retrieval-por-plataforma)
6. [Latencia Estimada Comparativa](#6-latencia-estimada-comparativa)
7. [Ingesta de Contenido por Plataforma](#7-ingesta-de-contenido-por-plataforma)
8. [Gestión Térmica por Plataforma](#8-gestión-térmica-por-plataforma)
9. [Concurrencia y Escalabilidad](#9-concurrencia-y-escalabilidad)
10. [Tabla Resumen de Cambios al Plan Original](#10-tabla-resumen-de-cambios-al-plan-original)
11. [Diferencias de Código por Plataforma](#11-diferencias-de-código-por-plataforma)
12. [Qué se Puede Validar en Cada Plataforma](#12-qué-se-puede-validar-en-cada-plataforma)
13. [Análisis Coste / Beneficio](#13-análisis-coste--beneficio)
14. [Decisión Recomendada](#14-decisión-recomendada)

---

## 1. Especificaciones de Hardware — Todas las Plataformas

### 1.1 Tabla Comparativa Completa

| Especificación | Jetson Nano 4GB ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | **Orin NX 16GB ★** | AGX Orin 32GB | AGX Orin 64GB |
|---|---|---|---|---|---|---|---|
| **Arquitectura GPU** | Maxwell | Ampere | Ampere | Ampere | **Ampere** | Ampere | Ampere |
| **CUDA cores** | 128 | 512 | 1024 | 1024 | **1024** | 2048 | 2048 |
| **Tensor Cores** | ✗ | ✓ 16 | ✓ 32 | ✓ 32 | **✓ 32** | ✓ 64 | ✓ 64 |
| **Compute Capability** | 5.3 | 8.7 | 8.7 | 8.7 | **8.7** | 8.7 | 8.7 |
| **RAM unificada** | 4 GB LPDDR4 | 4 GB LPDDR5 | 8 GB LPDDR5 | 8 GB LPDDR5 | **16 GB LPDDR5** | 32 GB LPDDR5 | 64 GB LPDDR5 |
| **Bandwidth memoria** | 25.6 GB/s | 34 GB/s | 68 GB/s | 102 GB/s | **102 GB/s** | 204 GB/s | 204 GB/s |
| **TOPS INT8** | ~0.5 | 20 | 40 | 70 | **100** | 200 | 275 |
| **CPU** | 4× A57 @ 1.43 GHz | 6× A78AE @ 1.5 GHz | 6× A78AE @ 1.5 GHz | 8× A78AE @ 2.0 GHz | **8× A78AE @ 2.0 GHz** | 12× A78AE @ 2.2 GHz | 12× A78AE @ 2.2 GHz |
| **TDP máximo** | 10 W | 10 W | 15 W | 20 W | **25 W** | 40 W | 60 W |
| **JetPack** | 4.6.x (max) | 6.x | 6.x | 6.x | **6.x** | 6.x | 6.x |
| **CUDA Toolkit** | 10.2 | 12.x | 12.x | 12.x | **12.x** | 12.x | 12.x |
| **Almacenamiento** | microSD | microSD/NVMe | microSD/NVMe | NVMe M.2 | **NVMe M.2** | NVMe M.2 | NVMe M.2 |
| **Precio aprox. (2026)** | ~$100–150 | ~$149 | ~$199 | ~$399 | **~$499** | ~$999 | ~$1,299 |
| **Estado** | ⚰️ EOL | Activo | Activo | Activo | **Activo** | Activo | Activo |
| **Rol en proyecto** | ❌ Descartar | ⚠️ Solo mínimo | ✅ Pruebas | ✅ Pruebas/Proto | **🎯 Plan original** | 🚀 Hub/Regional | 🚀 Centro educativo grande |

> ★ = plataforma objetivo del plan original
> ⚰️ = discontinuada; no comprar nueva

También existe la familia **Xavier** (Volta, compute 7.2): Xavier NX 8/16GB y AGX Xavier 32GB. Se excluyen del análisis principal por tres razones: JetPack max 5.x, TensorRT-LLM con optimizaciones muy limitadas en Volta, y fin de producción activa. Se mencionan solo en la tabla de compatibilidad.

### 1.2 El Salto Arquitectónico Clave: Maxwell → Ampere

```
Jetson Nano (Maxwell 5.3)  ←── BRECHA INFRANQUEABLE ──→  Familia Orin (Ampere 8.7)

  Sin Tensor Cores               Tensor Cores 3ª gen
  INT4: no soportado             INT4: hasta 64 TOPS efectivos (Orin NX 16GB)
  TensorRT-LLM: incompatible     TensorRT-LLM: completamente soportado
  JetPack 4.x (CUDA 10.2)       JetPack 6.x (CUDA 12.x)
```

Cualquier plataforma de la familia Orin comparte la misma arquitectura de software.
El código escrito para Orin Nano 8GB **corre sin cambios** en Orin NX 16GB o AGX Orin —
solo cambian los parámetros (tamaño de modelo, contexto, top-k) vía variable de entorno.

---

## 2. Matriz de Compatibilidad de Software

| Componente del Plan | Nano ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB ★ | AGX Orin 32/64GB |
|---|---|---|---|---|---|---|
| **TensorRT-LLM** | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **AWQ INT4** | ✗ | ✓ (modelos ≤1.5B) | ✓ (modelos ≤4B) | ✓ (modelos ≤4B ajustado) | ✓ (8B cómodo) | ✓ (13B+ posible) |
| **Speculative decoding** | ✗ | ✗ (sin RAM para 2 modelos) | ✓ (1B + 4B) | ✓ (1B + 4B) | ✓ (1B + 8B) | ✓ (1B + 8-13B) |
| **llama.cpp** | ✓ (solo CPU, lento) | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ChromaDB** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **e5-small en GPU** | ✗ (Maxwell) | ✓ (512 cores, lento) | ✓ | ✓ | ✓ | ✓ |
| **HyDE** | ✗ | ✗ (sin RAM para draft) | ✓ | ✓ | ✓ | ✓ |
| **Cross-Encoder GPU** | ✗ | ⚠️ Lento ~1s | ✓ ~80ms | ✓ ~50ms | ✓ ~50ms | ✓ ~25ms |
| **Whisper Tiny STT** | ✓ (~4s) | ✓ (~1.5s) | ✓ (~1.2s) | ✓ (~0.9s) | ✓ (~0.8s) | ✓ (~0.5s) |
| **Whisper Small ingesta** | ⚠️ Cron | ⚠️ Cron | ✓ Semáforo | ✓ Semáforo | ✓ Semáforo | ✓ Sin restricción |
| **JetPack / CUDA** | 4.6/10.2 | 6.x/12.x | 6.x/12.x | 6.x/12.x | 6.x/12.x | 6.x/12.x |
| **Docker + CUDA** | ⚠️ Difícil | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Stack Node/PG/Redis** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Xavier NX (referencia)** | — | — | — | — | — | — |
| *Xavier NX 16GB (7.2)* | *TRT-LLM marginal* | *TRT-LLM marginal* | *JetPack 5.x max* | — | — | — |

### Por qué TensorRT-LLM no funciona en Nano (legacy)

```
Compute Capability requerido por TensorRT-LLM: >= 7.0 (Volta, 2017+)
Jetson Nano Maxwell compute capability:               5.3 (2016)
→ Incompatible. Es una restricción de silicio, no de software.
```

Toda la familia Orin (Nano, NX, AGX) tiene compute 8.7 — todas son compatibles con TensorRT-LLM sin excepción.

---

## 3. Presupuesto de Memoria por Plataforma

### 3.1 Orin Nano 4GB — Solo Pipeline, Sin LLM Útil

```
Orin Nano 4GB — presupuesto
────────────────────────────────────────
OS + servicios                 : ~0.8 GB
Node.js/PG/Redis               : ~0.7 GB
FastAPI + Python               : ~0.3 GB
ChromaDB (5K chunks)           : ~0.1 GB
e5-small FP16 GPU              : ~0.35 GB
Whisper Tiny CPU               : ~0.15 GB
LLM: solo Llama-3.2-1B INT4    : ~0.7 GB  ← calidad mínima
────────────────────────────────────────
SUBTOTAL                       : ~3.1 GB
Margen                         : ~0.9 GB
────────────────────────────────────────
Sin speculative decoding (no hay RAM para 2 modelos).
MAX_CONTEXT=768, MAX_GEN=192.
Útil para probar TRT-LLM arranca y el stack de retrieval.
*No apto para validar calidad de respuestas*.
```

### 3.2 Orin Nano 8GB — Óptimo para Pruebas

```
Orin Nano 8GB — presupuesto (1 usuario)
────────────────────────────────────────
OS + servicios                 : ~1.2 GB
Node.js/PG/Redis               : ~0.9 GB
FastAPI + Python               : ~0.4 GB
ChromaDB (30K chunks × 512d)   : ~0.3 GB
e5-small FP16 GPU              : ~0.5 GB
Whisper Tiny CPU               : ~0.15 GB
Draft: Llama-3.2-1B INT4       : ~1.0 GB  (también para HyDE)
Target: Phi-3.5-mini-3.8B INT4 : ~2.1 GB
KV-Cache (512 tokens máx)      : ~0.4 GB
────────────────────────────────────────
SUBTOTAL RESIDENTES            : ~7.0 GB
BUFFER                         : ~1.0 GB  ✓
────────────────────────────────────────
Pool ingesta (semáforo ⚠️)     : ~1.2 GB
Máximo simultáneo              : 8.2 GB  ⚠️ muy ajustado
→ Semáforo obligatorio; considerar cron nocturno para ingesta en Nano 8GB
```

> **¿Por qué no el modelo 8B en 8GB?** Los pesos INT4 de Llama-3.1-8B ocupan ~4.2 GB.
> Con el resto del stack (~3.5 GB) el total supera los 8 GB disponibles.
> El par 1B (draft) + Phi-3.5-mini-3.8B (target) es el máximo viable con margen seguro.

### 3.3 Orin NX 8GB — Idéntica RAM, Mayor Bandwidth

```
Orin NX 8GB — presupuesto
Mismo stack que §3.2.
Diferencia clave: 102 GB/s vs 68 GB/s de bandwidth.
→ Los tokens/s son ~1.5× más rápidos con el mismo modelo que en Orin Nano 8GB.
→ La ingesta en realtime es más estable (embed batch termina más rápido).
Presupuesto de memoria: idéntico al §3.2.
```

### 3.4 Orin NX 16GB — Plan Original

```
Jetson Orin NX 16GB — presupuesto (plan original sin cambios)
────────────────────────────────────────────────────────────
OS + servicios del sistema              : ~2.0 GB
Node.js/Express + PostgreSQL + Redis    : ~1.2 GB
FastAPI + Python runtime                : ~0.5 GB
ChromaDB (100K chunks × 512d)          : ~0.8 GB
multilingual-e5-small FP16 (GPU)       : ~0.5 GB
Whisper Tiny CPU                        : ~0.15 GB
Draft model Llama-3.2-1B INT4 AWQ      : ~2.1 GB
Target model Llama-3.1-8B INT4 AWQ     : ~6.2 GB
KV-Cache paged (máx)                   : ~1.05 GB
────────────────────────────────────────────────────────────
SUBTOTAL RESIDENTES                     : ~14.5 GB
BUFFER DE SEGURIDAD                     : ~1.5 GB  ✓
Pool ingesta (semáforo)                : ~1.2 GB
Máximo simultáneo                       : 15.7 GB  ✓
```

### 3.5 AGX Orin 32GB — Headroom para Modelos Mayores

```
AGX Orin 32GB — opciones de target model
────────────────────────────────────────────────────────────
Stack base (OS + servicios + FastAPI + ChromaDB + embedder + STT) : ~5.5 GB
Draft model Llama-3.2-1B INT4                                      : ~2.1 GB
Target OPCIÓN A — Llama-3.1-8B INT4                                : ~6.2 GB → total ~13.8 GB ✓
Target OPCIÓN B — Llama-3.1-13B INT4                               : ~9.0 GB → total ~16.6 GB ✓✓
Target OPCIÓN C — Qwen2.5-14B INT4                                 : ~9.5 GB → total ~17.1 GB ✓✓
KV-Cache ampliado (4096 tokens)                                    : ~2.0 GB
────────────────────────────────────────────────────────────
Con 32GB se puede correr draft 1B + target 13B con speculative decoding
y mantener ingesta realtime sin restricción (10+ GB libres durante inferencia).
```

---

## 4. Estrategia de Inferencia LLM por Plataforma

### 4.1 Tabla Comparativa de Configuraciones

| Plataforma | Backend | Draft → Target | Speculative | tok/s est. | Latencia 256 tok |
|---|---|---|---|---|---|
| **Nano ⚰️** | llama.cpp CPU | — → TinyLlama-1.1B Q4 | ✗ | ~2–3 | ~90–130 s |
| **Orin Nano 4GB** | TRT-LLM | — → Llama-3.2-1B INT4 | ✗ | ~8–12 | ~22–32 s |
| **Orin Nano 8GB** | TRT-LLM | 1B → Phi-3.5-mini-3.8B INT4 | ✓ γ=4 | ~18–24 | ~11–14 s |
| **Orin NX 8GB** | TRT-LLM | 1B → Phi-3.5-mini-3.8B INT4 | ✓ γ=4 | ~25–32 | ~8–10 s |
| **Orin NX 16GB ★** | TRT-LLM | 1B → Llama-3.1-8B INT4 | ✓ γ=5 | ~28–35 | ~7–9 s |
| **AGX Orin 32GB** | TRT-LLM | 1B → Llama-3.1-13B INT4 | ✓ γ=5 | ~50–65 | ~4–5 s |
| **AGX Orin 64GB** | TRT-LLM | 3B → Qwen2.5-14B INT4 | ✓ γ=6 | ~65–80 | ~3–4 s |

### 4.2 Por qué Orin Nano 8GB y Orin NX 8GB difieren pese a misma RAM

La inferencia INT4 es un workload **memory-bandwidth bound**: para cada token hay que leer los pesos del modelo desde memoria. El cómputo (TOPS) no es el cuello de botella — el ancho de banda sí.

```
Orin Nano  8GB:  68 GB/s  → lee 3.8B INT4 (~2 GB) en ~29 ms → base ~34 tok/s
Orin NX    8GB: 102 GB/s  → lee 3.8B INT4 (~2 GB) en ~20 ms → base ~50 tok/s
Orin NX   16GB: 102 GB/s  → lee 8B INT4   (~4 GB) en ~39 ms → base ~26 tok/s
AGX Orin  32GB: 204 GB/s  → lee 8B INT4   (~4 GB) en ~20 ms → base ~50 tok/s

Speculative decoding (γ=5, aceptación k≈3.2): speedup ≈ 2.5–3×
```

### 4.3 Calidad Educativa por Modelo

| Modelo | Parámetros | Calidad |
|---|---|---|
| TinyLlama-1.1B | 1.1B | ❌ Baja — respuestas incompletas, errores frecuentes |
| Llama-3.2-1B | 1B | ⚠️ Marginal — solo para probar que el pipeline arranca |
| Phi-3.5-mini-instruct | 3.8B | ✅ Buena — apta para pruebas, razonamiento sólido |
| Llama-3.2-3B | 3B | ✅ Buena — alternativa al Phi-3.5-mini |
| Llama-3.1-8B ★ | 8B | ✅✅ Muy buena — objetivo del plan, secundaria peruana |
| Llama-3.1-13B | 13B | ✅✅✅ Excelente — AGX Orin, nivel más elaborado |
| Qwen2.5-14B | 14B | ✅✅✅ Excelente — cubre bien español técnico |

### 4.4 Compilación TRT-LLM por Variante de Modelo

```bash
# Orin Nano/NX 8GB — par 1B (draft) + 3.8B (target)
trtllm-build \
    --checkpoint_dir ./trt_checkpoints/phi35-mini-int4-awq \
    --output_dir     ./trt_engines/phi35-mini-int4 \
    --speculative_decoding_mode draft_tokens_external \
    --max_batch_size 1 --max_input_len 1280 --max_seq_len 1536

# Orin NX 16GB — par 1B (draft) + 8B (target) — plan original
trtllm-build \
    --checkpoint_dir ./trt_checkpoints/llama31-8b-int4-awq \
    --output_dir     ./trt_engines/llama31-8b-int4 \
    --speculative_decoding_mode draft_tokens_external \
    --max_batch_size 1 --max_input_len 2560 --max_seq_len 3584

# AGX Orin 32GB — par 1B (draft) + 13B (target)
trtllm-build \
    --checkpoint_dir ./trt_checkpoints/llama31-13b-int4-awq \
    --output_dir     ./trt_engines/llama31-13b-int4 \
    --speculative_decoding_mode draft_tokens_external \
    --max_batch_size 2 --max_input_len 4096 --max_seq_len 5120
```

---

## 5. Pipeline de Retrieval por Plataforma

| Componente | Nano ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB ★ | AGX Orin 32GB |
|---|---|---|---|---|---|---|
| **ChromaDB chunks máx** | 10K × 384d | 5K × 384d | 30K × 512d | 50K × 512d | 100K × 512d | 200K × 512d |
| **Embedding device** | CPU FP32 | GPU FP16 (512 cores) | GPU FP16 | GPU FP16 | GPU FP16 | GPU FP16 |
| **Latencia embed query** | ~80 ms | ~40 ms | ~20 ms | ~15 ms | ~15 ms | ~8 ms |
| **HyDE** | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| **Cross-Encoder** | ✗ | ⚠️ ~1,000 ms | ✓ ~80ms | ✓ ~50ms | ✓ ~50ms | ✓ ~25ms |
| **BM25** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Top-K retrieval** | 10→3 | 10→3 | 15→5 | 20→5 | 20→5 | 30→8 |
| **Recall@K estimado** | ~0.71 | ~0.71 | ~0.84 | ~0.87 | ~0.87 | ~0.91 |

---

## 6. Latencia Estimada Comparativa

*Condiciones: 1 usuario, perfil térmico nominal, búsqueda por texto, ~256 tokens de respuesta.*

| Etapa | Nano ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB ★ | AGX Orin 32GB |
|---|---|---|---|---|---|---|
| **STT (10s audio)** | ~4 s | ~1.5 s | ~1.2 s | ~0.9 s | ~0.8 s | ~0.5 s |
| **Embed query** | ~80 ms | ~40 ms | ~20 ms | ~15 ms | ~15 ms | ~8 ms |
| **ChromaDB search** | ~50 ms | ~40 ms | ~35 ms | ~30 ms | ~30 ms | ~20 ms |
| **BM25 scoring** | ~30 ms | ~25 ms | ~20 ms | ~20 ms | ~20 ms | ~15 ms |
| **HyDE expansion** | ✗ | ✗ | ~120 ms | ~100 ms | ~80 ms | ~50 ms |
| **Cross-Encoder** | ✗ | ~1,000 ms | ~80 ms | ~50 ms | ~50 ms | ~25 ms |
| **Total retrieval** | ~160 ms | ~1,100 ms | ~275 ms | ~215 ms | ~195 ms | ~118 ms |
| **1er token LLM** | ~15 s | ~3 s | ~1.5 s | ~1.0 s | ~0.8 s | ~0.5 s |
| **Generación 256 tok** | ~90–130 s | ~22–30 s | ~11–14 s | ~8–10 s | **~7–9 s** | ~4–5 s |
| **Grounding verify** | ~400 ms | ~150 ms | ~100 ms | ~100 ms | ~100 ms | ~60 ms |
| **────────────────** | **───────** | **───────** | **───────** | **───────** | **───────** | **───────** |
| **Total (solo texto)** | ~92–132 s | ~24–33 s | **~12–15 s** | **~9–11 s** | **~8–10 s** | **~5–6 s** |
| **Total (con STT)** | ~96–136 s | ~26–35 s | ~13–16 s | ~10–12 s | ~9–11 s | ~6–7 s |
| **1as tarjetas UI** | ~240 ms | ~1,300 ms | ~310 ms | ~250 ms | ~230 ms | ~145 ms |

> **Observación sobre Orin Nano 4GB**: el Cross-Encoder tarda ~1s en los 512 CUDA cores más lentos.
> Dominará el retrieval. Si se deshabilita, las tarjetas llegan en ~110ms pero el ranking baja.

> **Observación clave**: las tarjetas Rich Snippets (thumbnails, snippets, deep links) son
> resultados de retrieval y llegan **antes** de que el LLM genere una sola palabra.
> La latencia de 90–130s del Nano legacy afecta únicamente al texto del AI Overview.

---

## 7. Ingesta de Contenido por Plataforma

### 7.1 Estrategia de Ingesta por Plataforma

| Plataforma | Modo de ingesta | Motivo |
|---|---|---|
| Nano ⚰️ | Cron nocturno, detener LLM | Solo 4GB, sin margen |
| Orin Nano 4GB | Cron nocturno | Sin margen para Whisper Small + LLM simultáneo |
| Orin Nano 8GB | Semáforo ⚠️ ajustado | ~0.8GB margen; semáforo obligatorio; en producción preferir cron |
| Orin NX 8GB | Semáforo realtime | Mismo margen que Nano 8GB pero ingesta más rápida por bandwidth |
| Orin NX 16GB ★ | Semáforo realtime | Diseño original del plan |
| AGX Orin 32GB | Realtime sin restricción | 10+ GB libres; Whisper Small convive sin problema |

### 7.2 Tiempos de Ingesta Comparativos

| Tarea | Nano ⚰️ | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB | AGX Orin 32GB |
|---|---|---|---|---|---|
| Thumbnail FFmpeg | ~8 s | ~3 s | ~2.5 s | ~2 s | ~1 s |
| Whisper Small (10 min video) | ~240 s | ~75 s | ~65 s | ~60 s | ~35 s |
| Extracción PDF (50 pág) | ~10 s | ~4 s | ~3.5 s | ~3 s | ~2 s |
| OCR Tesseract (50 pág) | ~300 s | ~100 s | ~95 s | ~90 s | ~55 s |
| Embed 1000 chunks (e5-small) | ~120 s CPU | ~15 s GPU | ~10 s GPU | ~10 s GPU | ~5 s GPU |
| **Video 60 min — completo** | **~25 min** | **~8 min** | **~7 min** | **~6 min** | **~3.5 min** |

---

## 8. Gestión Térmica por Plataforma

### 8.1 Perfiles NVPModel Disponibles

| Plataforma | Modos NVPModel | Rango potencia | Draft gamma ajustable | Disipador activo |
|---|---|---|---|---|
| Nano ⚰️ | 0 (10W) / 1 (5W) | 5–10 W | ✗ | Recomendado |
| Orin Nano 4/8GB | 0 (15W) / 1 (10W) / 2 (7W) | 7–15 W | ✓ si spec. decoding activo | **Obligatorio** |
| Orin NX 8GB | 0 (20W) / 1 (15W) / 2 (10W) / 3 (5W) | 5–20 W | ✓ γ: 4→3→2 | **Obligatorio** |
| Orin NX 16GB ★ | 0 (25W) / 1 / 2 / 3 / 4 (7W) | 7–25 W | ✓ γ: 5→4→3→2 | **Obligatorio** |
| AGX Orin 32GB | 0 (40W) / 1 / 2 / 3 / 4 / 5 (10W) | 10–40 W | ✓ γ: 6→5→4→3→2 | **Obligatorio** |

### 8.2 Gestor Térmico Unificado (Familia Orin)

El mismo gestor sirve a todas las variantes Orin — solo cambia el perfil cargado:

```python
# thermal_manager.py — compatible con toda la familia Orin
PROFILES = {
    "orin_nano_8gb": {
        "nominal":  {"max_temp": 52,  "nvp_mode": 0, "draft_gamma": 4},
        "warm":     {"max_temp": 65,  "nvp_mode": 1, "draft_gamma": 3},
        "critical": {"max_temp": 999, "nvp_mode": 2, "draft_gamma": 2},
    },
    "orin_nx_8gb": {
        "nominal":  {"max_temp": 55, "nvp_mode": 3, "draft_gamma": 4},
        "warm":     {"max_temp": 68, "nvp_mode": 2, "draft_gamma": 3},
        "hot":      {"max_temp": 78, "nvp_mode": 1, "draft_gamma": 2},
        "critical": {"max_temp": 999,"nvp_mode": 0, "draft_gamma": 2},
    },
    "orin_nx_16gb": {                                          # plan original
        "nominal":  {"max_temp": 55, "nvp_mode": 4, "draft_gamma": 5},
        "warm":     {"max_temp": 68, "nvp_mode": 3, "draft_gamma": 4},
        "hot":      {"max_temp": 78, "nvp_mode": 2, "draft_gamma": 3},
        "critical": {"max_temp": 999,"nvp_mode": 1, "draft_gamma": 2},
    },
    "agx_orin_32gb": {
        "nominal":  {"max_temp": 55,  "nvp_mode": 5, "draft_gamma": 6},
        "warm":     {"max_temp": 68,  "nvp_mode": 4, "draft_gamma": 5},
        "hot":      {"max_temp": 78,  "nvp_mode": 3, "draft_gamma": 4},
        "very_hot": {"max_temp": 85,  "nvp_mode": 2, "draft_gamma": 3},
        "critical": {"max_temp": 999, "nvp_mode": 1, "draft_gamma": 2},
    },
}
```

Nano legacy (legacy, solo referencia):
```python
NANO_LEGACY_PROFILES = {
    "normal":   {"max_temp": 60,  "nvp_mode": 0},  # 10W — sin draft_gamma
    "throttle": {"max_temp": 999, "nvp_mode": 1},  # 5W
}
```

---

## 9. Concurrencia y Escalabilidad

| Plataforma | Usuarios con UI fluida | Espera usuario N+1 | Para escuelas grandes |
|---|---|---|---|
| Nano ⚰️ | 1 | ~130 s | No escalar |
| Orin Nano 4GB | 1 | ~30 s | No escalar |
| **Orin Nano 8GB** | 1–2 | ~13 s | Segundo dispositivo viable dado su precio |
| **Orin NX 8GB** | 2–3 | ~10 s | 2 unidades + Nginx round-robin |
| **Orin NX 16GB ★** | 3–5 | ~9 s | 2 unidades + Nginx para escuelas grandes |
| **AGX Orin 32GB** | 8–12 | ~5 s | Una unidad para escuela de 200+ alumnos |
| **AGX Orin 64GB** | 15–20 | ~3 s | Hub distrital con múltiples escuelas |

> "Usuarios con UI fluida": tarjetas llegan < 400ms y AI Overview llega antes de ~30s
> (umbral de tolerancia documentado en entornos educativos). Cola FIFO aplica en todos.

---

## 10. Tabla Resumen de Cambios al Plan Original

El plan original está escrito para la **Orin NX 16GB**. Esta tabla indica qué cambia en cada variante.

| Componente | Nano ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB ★ | AGX Orin 32GB |
|---|---|---|---|---|---|---|
| TensorRT-LLM | ❌ → llama.cpp | ✓ | ✓ | ✓ | ✓ | ✓ |
| Target model | TinyLlama-1.1B | Llama-3.2-1B | Phi-3.5-mini-3.8B | Phi-3.5-mini-3.8B | **Llama-3.1-8B** | Llama-3.1-13B |
| Speculative decoding | ❌ | ❌ | ✓ γ=4 | ✓ γ=4 | **✓ γ=5** | ✓ γ=5 |
| `MAX_CONTEXT_TOKENS` | 512 | 768 | 1024 | 1024 | **1792** | 3584 |
| `MAX_GENERATION_TOKENS` | 128 | 192 | 256 | 256 | **512** | 1024 |
| `TOP_K_RETRIEVAL` | 10→3 | 10→3 | 15→5 | 20→5 | **20→5** | 30→8 |
| HyDE | ❌ | ❌ | ✓ | ✓ | **✓** | ✓ |
| Cross-Encoder | ❌ | ⚠️ Lento | ✓ | ✓ | **✓** | ✓ |
| Embedding device | `cpu` | `cuda` | `cuda` | `cuda` | **`cuda`** | `cuda` |
| ChromaDB máx chunks | 10K | 5K | 30K | 50K | **100K** | 200K |
| Semáforo ingesta | Cron | Cron | Semáforo ⚠️ | Semáforo ✓ | **Semáforo ✓** | Sin restricción |
| Thermal profiles | 2 | 3 | 3 | 4 | **5** | 6 |
| Node.js / API / Frontend | ≡ Sin cambios | ≡ Sin cambios | ≡ Sin cambios | ≡ Sin cambios | ≡ Sin cambios | ≡ Sin cambios |

---

## 11. Diferencias de Código por Plataforma

### 11.1 `config/settings.py` — Configuración Unificada Multi-plataforma

```python
# config/settings.py
import os

PLATFORM = os.getenv("AI_PLATFORM", "orin_nx_16gb")
# Valores: "nano_legacy" | "orin_nano_4gb" | "orin_nano_8gb" |
#          "orin_nx_8gb" | "orin_nx_16gb" | "agx_orin_32gb" | "agx_orin_64gb"

_CONFIGS = {
    "nano_legacy": {
        "LLM_BACKEND": "llama_cpp", "LLM_MODEL": "tinyllama-1.1b-q4_k_m.gguf",
        "LLM_N_GPU_LAYERS": 0, "LLM_N_THREADS": 4,
        "DRAFT_MODEL": None, "SPECULATIVE": False,
        "MAX_CONTEXT": 512, "MAX_GEN": 128,
        "EMBED_DEVICE": "cpu", "HYDE": False, "CROSS_ENCODER": False,
        "TOP_K": 10, "TOP_K_FINAL": 3, "CHROMA_MAX": 10_000,
        "INGESTION_MODE": "cron", "THERMAL_PROFILE": "nano_legacy",
    },
    "orin_nano_4gb": {
        "LLM_BACKEND": "tensorrt_llm",
        "TARGET_MODEL_DIR": "./trt_engines/llama32-1b-int4",
        "DRAFT_MODEL": None, "SPECULATIVE": False,
        "MAX_CONTEXT": 768, "MAX_GEN": 192,
        "EMBED_DEVICE": "cuda", "HYDE": False, "CROSS_ENCODER": False,
        "TOP_K": 10, "TOP_K_FINAL": 3, "CHROMA_MAX": 5_000,
        "INGESTION_MODE": "cron", "THERMAL_PROFILE": "orin_nano",
    },
    "orin_nano_8gb": {
        "LLM_BACKEND": "tensorrt_llm",
        "DRAFT_MODEL_DIR": "./trt_engines/llama32-1b-int4",
        "TARGET_MODEL_DIR": "./trt_engines/phi35-mini-int4",
        "SPECULATIVE": True, "SPECULATIVE_GAMMA": 4,
        "MAX_CONTEXT": 1024, "MAX_GEN": 256,
        "EMBED_DEVICE": "cuda", "HYDE": True, "CROSS_ENCODER": True,
        "TOP_K": 15, "TOP_K_FINAL": 5, "CHROMA_MAX": 30_000,
        "INGESTION_MODE": "semaphore_cautious",
        "THERMAL_PROFILE": "orin_nano_8gb",
    },
    "orin_nx_8gb": {
        "LLM_BACKEND": "tensorrt_llm",
        "DRAFT_MODEL_DIR": "./trt_engines/llama32-1b-int4",
        "TARGET_MODEL_DIR": "./trt_engines/phi35-mini-int4",
        "SPECULATIVE": True, "SPECULATIVE_GAMMA": 4,
        "MAX_CONTEXT": 1024, "MAX_GEN": 256,
        "EMBED_DEVICE": "cuda", "HYDE": True, "CROSS_ENCODER": True,
        "TOP_K": 20, "TOP_K_FINAL": 5, "CHROMA_MAX": 50_000,
        "INGESTION_MODE": "realtime",
        "THERMAL_PROFILE": "orin_nx_8gb",
    },
    "orin_nx_16gb": {                         # ─── PLAN ORIGINAL ───
        "LLM_BACKEND": "tensorrt_llm",
        "DRAFT_MODEL_DIR": "./trt_engines/llama32-1b-int4",
        "TARGET_MODEL_DIR": "./trt_engines/llama31-8b-int4",
        "SPECULATIVE": True, "SPECULATIVE_GAMMA": 5,
        "MAX_CONTEXT": 1792, "MAX_GEN": 512,
        "EMBED_DEVICE": "cuda", "HYDE": True, "CROSS_ENCODER": True,
        "TOP_K": 20, "TOP_K_FINAL": 5, "CHROMA_MAX": 100_000,
        "INGESTION_MODE": "realtime",
        "THERMAL_PROFILE": "orin_nx_16gb",
    },
    "agx_orin_32gb": {
        "LLM_BACKEND": "tensorrt_llm",
        "DRAFT_MODEL_DIR": "./trt_engines/llama32-1b-int4",
        "TARGET_MODEL_DIR": "./trt_engines/llama31-13b-int4",
        "SPECULATIVE": True, "SPECULATIVE_GAMMA": 5,
        "MAX_CONTEXT": 3584, "MAX_GEN": 1024,
        "EMBED_DEVICE": "cuda", "HYDE": True, "CROSS_ENCODER": True,
        "TOP_K": 30, "TOP_K_FINAL": 8, "CHROMA_MAX": 200_000,
        "INGESTION_MODE": "realtime",
        "THERMAL_PROFILE": "agx_orin_32gb",
    },
    "agx_orin_64gb": {
        "LLM_BACKEND": "tensorrt_llm",
        "DRAFT_MODEL_DIR": "./trt_engines/llama32-3b-int4",
        "TARGET_MODEL_DIR": "./trt_engines/qwen25-14b-int4",
        "SPECULATIVE": True, "SPECULATIVE_GAMMA": 6,
        "MAX_CONTEXT": 4096, "MAX_GEN": 1024,
        "EMBED_DEVICE": "cuda", "HYDE": True, "CROSS_ENCODER": True,
        "TOP_K": 30, "TOP_K_FINAL": 8, "CHROMA_MAX": 500_000,
        "INGESTION_MODE": "realtime",
        "THERMAL_PROFILE": "agx_orin_64gb",
    },
}

cfg                   = _CONFIGS[PLATFORM]
LLM_BACKEND           = cfg["LLM_BACKEND"]
DRAFT_MODEL_DIR       = cfg.get("DRAFT_MODEL_DIR")
TARGET_MODEL_DIR      = cfg.get("TARGET_MODEL_DIR") or cfg.get("LLM_MODEL")
SPECULATIVE_DECODING  = cfg["SPECULATIVE"]
SPECULATIVE_GAMMA     = cfg.get("SPECULATIVE_GAMMA", 0)
MAX_CONTEXT_TOKENS    = cfg["MAX_CONTEXT"]
MAX_GENERATION_TOKENS = cfg["MAX_GEN"]
EMBEDDING_DEVICE      = cfg["EMBED_DEVICE"]
HYDE_ENABLED          = cfg["HYDE"]
CROSS_ENCODER_ENABLED = cfg["CROSS_ENCODER"]
TOP_K_RETRIEVAL       = cfg["TOP_K"]
TOP_K_FINAL           = cfg["TOP_K_FINAL"]
CHROMA_MAX_CHUNKS     = cfg["CHROMA_MAX"]
INGESTION_MODE        = cfg["INGESTION_MODE"]
THERMAL_PROFILE       = cfg["THERMAL_PROFILE"]
```

### 11.2 `services/llm_engine.py` — Selector de Backend (sin cambios respecto al plan)

```python
# services/llm_engine.py
from config.settings import LLM_BACKEND

if LLM_BACKEND == "tensorrt_llm":
    from services.llm_backends.trt_engine import TRTEngine as LLMEngine
elif LLM_BACKEND == "llama_cpp":
    from services.llm_backends.llama_cpp_engine import LlamaCppEngine as LLMEngine

engine = LLMEngine()
```

### 11.3 `requirements.txt` por Familia de Hardware

```
# requirements_orin_family.txt  ← toda la familia Orin (Nano, NX, AGX)
tensorrt-llm==0.10.0           # wheel ARM64 JetPack 6.x específico
torch==2.3.0+cu118

# requirements_nano_legacy.txt  ← solo Jetson Nano (EOL, no recomendado)
llama-cpp-python==0.2.77       # CMAKE_ARGS="-DLLAMA_CUBLAS=off" (Maxwell sin aceleración)
```

---

## 12. Qué se Puede Validar en Cada Plataforma

| Capacidad | Nano ⚰️ | Orin Nano 4GB | Orin Nano 8GB | Orin NX 8GB | Orin NX 16GB ★ | AGX Orin 32GB |
|---|---|---|---|---|---|---|
| Stack microservicios funciona | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contrato SSE end-to-end | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| JWT + visor contenido + deep links | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ingesta PDF + video + thumbnails | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Retrieval BM25 + Vector (core) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Triaje 4 niveles L1–L4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Grounding verifier | ✅ (lento) | ✅ | ✅ | ✅ | ✅ | ✅ |
| STT voz → búsqueda | ✅ (4s) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TensorRT-LLM arranca** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Speculative decoding** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **HyDE + Cross-Encoder** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Semáforo realtime ingesta** | ❌ | ❌ | ⚠️ | ✅ | ✅ | ✅ |
| **Calidad ≈ modelo 8B de producción** | ❌ | ❌ | ⚠️ (3.8B) | ⚠️ (3.8B) | ✅ | ✅✅ |
| **Latencia ≈ producción final** | ❌ | ❌ | ⚠️ (~12s) | ⚠️ (~10s) | ✅ | ✅ |
| **Perfiles térmicos completos** | ❌ | ❌ | ⚠️ (3/5) | ⚠️ (4/5) | ✅ | ✅ |
| **Concurrencia 10+ usuarios** | ❌ | ❌ | ❌ | ⚠️ (3) | ⚠️ (5) | ✅ |

---

## 13. Análisis Coste / Beneficio

### 13.1 Para Banco de Pruebas / Desarrollo

| Plataforma | Precio | Qué sí valida | Qué no valida | Veredicto |
|---|---|---|---|---|
| Nano ⚰️ | ~$100–150 | Stack de integración, API, retrieval | TRT-LLM, speculative, HyDE, calidad LLM | Solo si ya se tiene — no comprar |
| Orin Nano 4GB | ~$149 | Todo lo anterior + TRT-LLM arranca | Speculative decoding, calidad LLM útil, HyDE | Poca diferencia con Nano 8GB por $50 menos |
| **Orin Nano 8GB** | **~$199** | **Todo el pipeline: TRT-LLM, spec. decoding, HyDE, Cross-Encoder** | **Calidad modelo 8B, latencia exacta final** | **✅ Óptimo para pruebas** |
| Orin NX 8GB | ~$399 | Todo lo del Nano 8GB + mayor velocidad | Calidad modelo 8B | Viable pero $200 extra para pruebas |

### 13.2 Para Prototipo Final / Despliegue en Escuela

| Plataforma | Precio | Escuela objetivo | Fortalezas | Limitaciones |
|---|---|---|---|---|
| Orin Nano 8GB | ~$199 | Pequeña, ≤ 3 alumnos simultáneos | Precio mínimo, funcional | Modelo 3.8B, latencia ~12s, ingesta ajustada |
| Orin NX 8GB | ~$399 | Pequeña-mediana, ≤ 5 alumnos | Más rápido, modelo idéntico 3.8B | Aún usa modelo 3.8B, no 8B |
| **Orin NX 16GB ★** | **~$499** | **Mediana, ≤ 20 alumnos** | **Plan completo: modelo 8B, spec. decoding, HyDE** | **Precio $499** |
| AGX Orin 32GB | ~$999 | Grande o hub distrital | Modelo 13B, 10+ usuarios, ingesta libre | Precio, mayor ventilación necesaria |

### 13.3 Relación Calidad-Precio

```
Precio    Plataforma          Tokens/s   Modelo target   Usuarios fluidos
─────────────────────────────────────────────────────────────────────────
 $199     Orin Nano 8GB       18–24      Phi-3.5-mini    1–2
 $399     Orin NX 8GB         25–32      Phi-3.5-mini    2–3  ← +velocidad, mismo modelo
 $499     Orin NX 16GB ★      28–35      Llama-3.1-8B    3–5  ← +calidad de modelo
 $999     AGX Orin 32GB       50–65      Llama-3.1-13B   8–12 ← +concurrencia y calidad
$1,299    AGX Orin 64GB       65–80      Qwen2.5-14B     15–20
```

El salto de $199 → $499 (+$300) es el más valioso: pasa de modelo 3.8B a 8B (diferencia real en calidad de respuestas educativas). Para un prototipo que se presentará a docentes y evaluadores, este salto importa.

El salto de $499 → $999 (+$500) es de concurrencia: de 5 a 10+ usuarios simultáneos. Solo relevante si la escuela piloto tiene grupos grandes usando el sistema al mismo tiempo.

---

## 14. Decisión Recomendada

### Estrategia de Dos Fases

```
FASE 1 — PRUEBAS Y DESARROLLO (Semanas 1–4 del plan)
──────────────────────────────────────────────────────
Hardware:   Jetson Orin Nano 8GB (~$199)
Config:     AI_PLATFORM=orin_nano_8gb
Modelos:    Llama-3.2-1B (draft) + Phi-3.5-mini-3.8B (target)

Qué se valida con certeza:
  ✓ TensorRT-LLM + speculative decoding en hardware Orin real
  ✓ HyDE + Cross-Encoder + BM25 + Vector retrieval end-to-end
  ✓ SSE streaming Node.js → FastAPI → frontend
  ✓ JWT auth + visor + deep links (?t=142, ?page=12)
  ✓ Ingesta PDF + video + thumbnails en la Jetson
  ✓ Grounding verifier + triaje L1–L4
  ✓ Gestión térmica con 3 perfiles NVPModel
  ✓ Todos los tests unitarios del plan

Lo que se acepta como diferente respecto a producción:
  ≈ Latencia ~12s vs ~8s (aceptable en desarrollo)
  ≈ Calidad respuestas modelo 3.8B vs 8B (funcional, menos preciso)


FASE 2 — PROTOTIPO FINAL (Semanas 5–10 del plan)
──────────────────────────────────────────────────────
Hardware:   Jetson Orin NX 16GB (~$499)  ← plan original
Config:     AI_PLATFORM=orin_nx_16gb
Modelos:    Llama-3.2-1B (draft) + Llama-3.1-8B (target)

Migración desde Orin Nano 8GB:
  1. Cambiar AI_PLATFORM=orin_nano_8gb → AI_PLATFORM=orin_nx_16gb
  2. Compilar engines 8B INT4 AWQ (el 1B ya está compilado en la Fase 1)
  3. Re-indexar ChromaDB a 100K si se tenía la base reducida a 30K
  4. Verificar Active Heat Sink instalado y fan reconocido
  → Node.js, FastAPI routers, frontend, auth middleware: sin cambios
```

### Si el Prototipo Debe Demostrar Escalabilidad Regional

Considerar directamente el **AGX Orin 32GB** como hardware final, saltando el Orin NX 16GB:
- Precio +$500 respecto al Orin NX 16GB
- Modelo 13B en lugar de 8B (calidad notablemente mejor en respuestas elaboradas)
- Atiende 10+ alumnos simultáneos desde el primer día
- Código 100% compatible — solo cambiar `AI_PLATFORM=agx_orin_32gb`
