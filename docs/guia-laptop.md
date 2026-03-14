# Guía de Laptop — Desarrollo en tu PC

> **Proyecto**: GTR-PUCP — CDN Educativa Offline  
> **Fecha**: Febrero 2026  
> **Para quién**: todo lo que haces en tu laptop, **sin necesitar la Jetson**.

La [guia-inicio.md](guia-inicio.md) cubre lo que se hace **en la Jetson** (flash, compilación TRT-LLM, arranque en producción). Esta guía cubre lo que haces **en tu laptop**: desarrollo del código, pruebas locales, descarga de modelos y preparación antes de tener el hardware.

> **Principio clave**: el 80% del trabajo de implementación ocurre aquí. La Jetson solo entra cuando hay que validar TRT-LLM y el rendimiento real. Todo lo demás — Node.js, React, FastAPI sin LLM real — se puede desarrollar y probar completamente en tu laptop.

---

## Índice

1. [Qué falta por implementar — visión global](#1-qué-falta-por-implementar--visión-global)
2. [Configurar el entorno de desarrollo](#2-configurar-el-entorno-de-desarrollo)
3. [Descarga de modelos HuggingFace (en paralelo al desarrollo)](#3-descarga-de-modelos-huggingface-en-paralelo-al-desarrollo)
4. [Mock AI Engine — desarrollar sin Jetson](#4-mock-ai-engine--desarrollar-sin-jetson)
5. [Implementar el ai_engine (FastAPI — Python)](#5-implementar-el-ai_engine-fastapi--python)
6. [Cambios en el CDN backend (Node.js)](#6-cambios-en-el-cdn-backend-nodejs)
7. [Cambios en el frontend (React)](#7-cambios-en-el-frontend-react)
8. [Schema SQL — tabla de ingesta](#8-schema-sql--tabla-de-ingesta)
9. [Construir el dataset de calibración AWQ](#9-construir-el-dataset-de-calibración-awq)
10. [Tests — qué probar en la laptop](#10-tests--qué-probar-en-la-laptop)
11. [Git — flujo de trabajo laptop ↔ Jetson](#11-git--flujo-de-trabajo-laptop--jetson)
12. [Orden de trabajo recomendado por semana](#12-orden-de-trabajo-recomendado-por-semana)

---

## 1. Qué Falta por Implementar — Visión Global

### Estado actual del repositorio

| Archivo | Estado | Pendiente |
|---|---|---|
| `ai_engine/config/settings.py` | ✅ Completo | — |
| `ai_engine/config/prompts.py` | ✅ Completo | — |
| `ai_engine/config/platforms/*.env` | ✅ Completo | — |
| `ai_engine/main.py` | ✅ Completo | — |
| `ai_engine/routers/health.py` | ✅ Completo | — |
| `ai_engine/services/thermal_manager.py` | ✅ Completo | — |
| `ai_engine/requirements.txt` | ✅ Completo | — |
| `ai_engine/calibration/seeds.jsonl` | ✅ 20 muestras | Expandir a 512 (§9) |
| `ai_engine/routers/search.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/routers/voice_search.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/routers/ingest.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/services/llm_engine.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/services/hybrid_retriever.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/services/stt.py` | 🔲 Esqueleto | **Implementar** |
| `ai_engine/services/resource_manager.py` | ❌ No existe | **Crear** |
| `ai_engine/services/intent_router.py` | ❌ No existe | **Crear** |
| `ai_engine/services/hyde_expander.py` | ❌ No existe | **Crear** |
| `ai_engine/services/grounding_verifier.py` | ❌ No existe | **Crear** |
| `ai_engine/services/ingestion/chunker.py` | ❌ No existe | **Crear** |
| `ai_engine/services/ingestion/pdf_processor.py` | ❌ No existe | **Crear** |
| `ai_engine/services/ingestion/video_processor.py` | ❌ No existe | **Crear** |
| `ai_engine/services/ingestion/thumbnail_generator.py` | ❌ No existe | **Crear** |
| `ai_engine/models/schemas.py` | ❌ No existe | **Crear** |
| `ai_engine/tests/test_retrieval.py` | ❌ No existe | **Crear** |
| `ai_engine/tests/test_grounding.py` | ❌ No existe | **Crear** |
| `ai_engine/tests/test_stt.py` | ❌ No existe | **Crear** |
| `ai_engine/tests/eval_dataset.jsonl` | ❌ No existe | **Crear** |
| `server/src/routes/ai.ts` | ❌ No existe | **Crear** |
| `server/src/controllers/aiSearchController.ts` | ❌ No existe | **Crear** |
| `server/src/middleware/viewerAuth.ts` | ❌ No existe | **Crear** |
| `server/src/controllers/uploadController.ts` | ⚠️ Modificar | Añadir hook AI |
| `server/src/index.ts` | ⚠️ Modificar | Registrar ruta `/api/ai` |
| DB schema `ai_ingestion_queue` | ❌ No existe | **Crear (§8)** |
| `search_ui/` — app React del buscador | ✅ Scaffold creado | Completar estilos / auth |
| `search_ui/src/pages/SearchPage.tsx` | ✅ Creado | Ajustar a diseño final |
| `search_ui/src/components/search/*` | ✅ Creados | SearchBar, VoiceButton, AIOverview, SnippetCard, SearchResults |
| `search_ui/src/hooks/useSSESearch.ts` | ✅ Creado | — |
| `search_ui/src/hooks/useVoiceRecorder.ts` | ✅ Creado | — |

### Lo que la laptop NO puede hacer (necesita Jetson)

- Compilar engines TensorRT-LLM (requiere CUDA en ARM64)
- Medir latencia real de inferencia LLM
- Validar gestión térmica y throttling NVPModel
- Test de carga con modelo 8B real en producción

Todo lo demás: sí se puede desarrollar y probar localmente.

---

## 2. Configurar el Entorno de Desarrollo

### 2.1 Prerequisitos

```bash
# Verificar versiones mínimas
node --version   # >= 18.0.0
python3 --version  # >= 3.10
git --version

# Instalar si falta
# Node.js: https://nodejs.org/  (usar nvm recomendado)
# Python:  sudo apt install python3.11 python3.11-dev python3.11-venv
```

### 2.2 Clonar y preparar el repo

```bash
cd /home/jleon/2026/PUCP/GTR/CDN
# Ya tienes el repo — no necesitas clonar nada
```

### 2.3 Entorno Python para el ai_engine (laptop)

En la laptop NO instalamos TensorRT-LLM (es ARM64-only). Usamos un entorno Python ligero para desarrollo y pruebas con un LLM mock o con llama.cpp/transformers como backend alternativo de desarrollo.

> **Nota importante**: usar explícitamente `python3.12`. El comando genérico `python3` en Ubuntu 24.04 con Conda resuelve a Python 3.13, y varios paquetes (spacy, chromadb) aún no tienen wheels para 3.13.

> **Nombre del venv en uso**: `ai_env` (creado en el raíz del repo). Todos los comandos Python de esta guía asumen `source ai_env/bin/activate`.

```bash
# Instalar el paquete venv de Python 3.12 si falta
sudo apt install -y python3.12-venv

cd /home/jleon/2026/PUCP/GTR/CDN
python3.12 -m venv ai_env
source ai_env/bin/activate

# python3 ahora debe decir 3.12.x
python3 --version

# Actualizar pip y setuptools primero (necesario para algunos paquetes)
pip install --upgrade pip setuptools wheel

# Instalar chromadb y spacy juntos primero (tienen restricciones mutuas)
# Se usan rangos en lugar de versiones exactas para que pip resuelva
pip install "chromadb>=0.5,<0.6" "spacy>=3.7,<3.8"

# Instalar el resto de dependencias
# Nota: faster-whisper reemplaza a openai-whisper (tiene wheels para Python 3.12)
pip install \
    fastapi==0.111.0 \
    "uvicorn[standard]==0.29.0" \
    pydantic==2.7.0 \
    python-multipart==0.0.9 \
    sentence-transformers==3.0.0 \
    rank_bm25==0.2.2 \
    "transformers==4.41.0" \
    torch \
    faster-whisper \
    pymupdf==1.24.0 \
    pytesseract==0.3.10 \
    langdetect==1.0.9 \
    prometheus-client==0.20.0 \
    aiofiles==23.2.0 \
    httpx==0.27.0 \
    diskcache==5.6.3 \
    python-dotenv==1.0.0 \
    pytest==8.2.0 \
    pytest-asyncio==0.23.7

# fastapi-cli (instalado como dependencia de fastapi) requiere typer>=0.16
# pero spacy requiere typer<0.10 — resolver eliminando fastapi-cli
pip uninstall fastapi-cli -y
pip install "typer>=0.3.0,<0.10.0"

# Modelo NLP español — usar URL directa (el comando python3 -m spacy download
# genera una URL rota cuando typer no está en la versión esperada)
pip install "https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl"

# Verificar todo
python3 -c "
import fastapi, chromadb, spacy, torch, faster_whisper
print('Python:', __import__('sys').version.split()[0])
print('fastapi', fastapi.__version__)
print('chromadb', chromadb.__version__)
print('spacy', spacy.__version__)
print('torch', torch.__version__)
print('faster-whisper', faster_whisper.__version__)
print('✓ OK')
"
```

### 2.4 Entorno Node.js para el server

```bash
cd /home/jleon/2026/PUCP/GTR/CDN/server
npm install
cp .env.example .env   # si existe; si no, ver §6.1
```

### 2.5 Entorno React — search_ui (tu frontend) y client (compañero)

```bash
# Tu app — el motor de búsqueda IA (puerto 5174)
cd /home/jleon/2026/PUCP/GTR/CDN/search_ui
npm install   # ya hecho
npm run dev   # http://localhost:5174

# El frontend de tu compañero — plataforma educativa (puerto 5173)
# No lo tocas, pero puede estar corriendo en paralelo
cd /home/jleon/2026/PUCP/GTR/CDN/client
npm install
npm run dev   # http://localhost:5173
```

> `search_ui/vite.config.ts` ya tiene el proxy configurado: todas las llamadas a `/api/*`
> se redirigen automáticamente a `http://localhost:3000` (CDN server) en desarrollo.
> En producción apuntarán al mismo dominio sin necesidad de cambiar el código.

### 2.6 Servicios locales — PostgreSQL y Redis nativos

Ambos servicios están **instalados nativamente** en esta máquina. No necesitas Docker para el desarrollo local.

| Servicio | Versión | Host | Puerto |
|---|---|---|---|
| PostgreSQL | 16 | localhost | 5432 |
| Redis | 7 | localhost | 6379 |

```bash
# ── Verificar que ambos corren ────────────────────────────────────────────
psql -U cdn_user -d cdn_dev -h localhost -c "SELECT version();"
redis-cli ping   # PONG

# ── Si necesitas recrear la base de datos de desarrollo (solo una vez) ────
sudo -u postgres psql -c "CREATE USER cdn_user WITH PASSWORD 'cdn_pass';"
sudo -u postgres psql -c "CREATE DATABASE cdn_dev OWNER cdn_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cdn_dev TO cdn_user;"

# ── Reiniciar servicios si es necesario ───────────────────────────────────
sudo systemctl restart postgresql
sudo systemctl restart redis
```

> **`docker-compose.dev.yml`**: El archivo existe en el repo como referencia para desplegar en contenedores (Jetson, servidor de producción), pero **no se usa en desarrollo local**.
>
> ⚠️ **Si alguna vez ejecutaste `docker compose up`** y luego los servicios nativos no levantan, es porque un contenedor Docker ocupa el puerto. Solución:
> ```bash
> sudo docker stop cdn-redis-1 && sudo docker rm cdn-redis-1
> sudo systemctl start redis-server
> ```

---

## 3. Descarga de Modelos HuggingFace (en Paralelo al Desarrollo)

Lanza estas descargas en background mientras trabajas en el código. Tardan horas pero no requieren atención.

### 3.1 Aceptar licencias (solo una vez, en el navegador)

1. Ir a [huggingface.co/meta-llama/Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) → clic en "Agree and access repository"
2. Ir a [huggingface.co/meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) → aceptar licencia
3. Phi-3.5-mini y los modelos de embeddings/reranker no requieren licencia

### 3.2 Descargar en background

Los modelos van a `/mnt/ssd/models/hf_models/` (SSD externo montado en la máquina).

```bash
source ai_env/bin/activate
# huggingface_hub ya está instalado en ai_env

# Login — usar este método (huggingface-cli login tiene problemas con el helper de git)
python -c "from huggingface_hub import login; login()"
# → pega tu token desde https://huggingface.co/settings/tokens
# → cuando pregunte "Add token as git credential?" responder N
#   (a menos que hayas configurado: git config --global credential.helper store)

# Directorio destino
mkdir -p /mnt/ssd/models/hf_models

# Descargar cada modelo (lanzar en terminales separadas para paralelizar)
# Ya hecho: Llama-3.2-1B-Instruct (~5 GB)
python -c "
from huggingface_hub import snapshot_download
snapshot_download('meta-llama/Llama-3.2-1B-Instruct',
                  local_dir='/mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct')
"

# En descarga: Phi-3.5-mini-instruct (~7.6 GB)
python -c "
from huggingface_hub import snapshot_download
snapshot_download('microsoft/Phi-3.5-mini-instruct',
                  local_dir='/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct')
"

# Pendiente: Llama-3.1-8B-Instruct (~16 GB) — Fase 2, cuando tengas Orin NX
python -c "
from huggingface_hub import snapshot_download
snapshot_download('meta-llama/Llama-3.1-8B-Instruct',
                  local_dir='/mnt/ssd/models/hf_models/Llama-3.1-8B-Instruct')
"
```

**Tamaños reales**:
- Llama-3.2-1B: ~5 GB ✅ ya descargado
- Phi-3.5-mini: ~7.6 GB (en descarga)
- Llama-3.1-8B: ~16 GB (Fase 2)
- **Total**: ~29 GB en `/mnt/ssd/models/hf_models/`

---

## 4. Mock AI Engine — Desarrollar sin Jetson

Para poder desarrollar y probar el Node.js y el React sin la Jetson, se usa un **mock del AI Engine** que responde con datos de ejemplo pero sin LLM real.

Crea este archivo:

```bash
cat > ai_engine/mock_main.py << 'EOF'
"""
mock_main.py — Servidor mock del AI Engine para desarrollo en laptop.
Responde con datos de ejemplo sin LLM, sin TRT-LLM, sin GPU.
Usar: uvicorn ai_engine.mock_main:app --port 8000 --reload
"""
import asyncio, time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AI Engine MOCK")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SearchRequest(BaseModel):
    query: str
    context: dict = {}


MOCK_CDN_RESULTS = [
    {
        "content_id": "uuid-001",
        "content_type": "video",
        "title": "Redes de Computadoras — Módulo 5: Protocolo TCP/IP",
        "snippet": "El protocolo TCP garantiza la entrega ordenada de datos mediante confirmaciones y retransmisión...",
        "thumbnail_url": "/storage/thumbnails/uuid-001.jpg",
        "viewer_url": "/viewer/video/uuid-001?t=142",
        "upload_date": "2026-01-15T09:00:00Z",
        "requires_auth": False,
        "relevance_score": 0.92,
    },
    {
        "content_id": "uuid-002",
        "content_type": "pdf",
        "title": "Manual de Redes — CISCO Academy Nivel 1",
        "snippet": "Una red de área local (LAN) conecta dispositivos dentro de un edificio usando Ethernet...",
        "thumbnail_url": "/storage/thumbnails/uuid-002.jpg",
        "viewer_url": "/viewer/document/uuid-002?page=3",
        "upload_date": "2026-01-10T14:00:00Z",
        "requires_auth": False,
        "relevance_score": 0.87,
    },
]

MOCK_AI_TEXT = (
    "Una red LAN (Local Area Network) conecta dispositivos dentro de un área geográfica "
    "limitada como un edificio o campus. Utiliza tecnologías como Ethernet (IEEE 802.3) "
    "y Wi-Fi (IEEE 802.11) para transmitir datos. El módulo 5 del curso explica los "
    "protocolos de capa de red y transporte que operan sobre la infraestructura LAN, "
    "incluyendo IP, TCP y UDP."
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "platform": "mock_laptop",
        "components": {
            "llm_engine": "mock",
            "retriever":  "mock",
            "stt":        "mock",
            "thermal":    "nominal",
            "chroma_chunks": 42,
        },
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    """Responde inmediatamente con JSON (sin streaming). Útil para probar el contrato."""
    return {
        "query": req.query,
        "cdn_results": MOCK_CDN_RESULTS,
        "ai_overview": {
            "text": MOCK_AI_TEXT,
            "level": "L1",
            "grounding": {"coverage_score": 0.87, "is_grounded": True},
            "language_detected": "es",
        },
        "ui_hints": {"suggested_queries": ["¿Qué es TCP/IP?", "Diferencia LAN y WAN"]},
    }


@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    """Simula SSE streaming token a token con delay artificial."""
    words = MOCK_AI_TEXT.split()

    async def event_generator():
        # Primero emitir los cdn_results
        import json
        yield f"data: {json.dumps({'type': 'cdn_results', 'data': MOCK_CDN_RESULTS})}\n\n"
        await asyncio.sleep(0.3)

        # Luego simular tokens del AI Overview
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            await asyncio.sleep(0.04)   # ~25 tokens/s para simular

        yield f"data: {json.dumps({'type': 'done', 'grounding': {'coverage_score': 0.87}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.post("/api/voice-search")
async def voice_search():
    return {
        "query_transcribed": "¿Qué es una red LAN?",
        "query": "¿Qué es una red LAN?",
        "cdn_results": MOCK_CDN_RESULTS,
        "ai_overview": {"text": MOCK_AI_TEXT, "level": "L1"},
    }


@app.post("/api/ingest")
async def ingest(body: dict):
    return {"status": "queued", "content_id": body.get("content_id"), "mock": True}
EOF
```

Arrancar el mock:

```bash
source ai_env/bin/activate
# Usar siempre "python -m uvicorn" — garantiza que se use el uvicorn del venv,
# no el del sistema (/usr/bin/uvicorn que corre con Python sin paquetes)
python -m uvicorn ai_engine.mock_main:app --port 8000 --reload
```

Con esto puedes desarrollar y probar **todo el Node.js y todo el React** sin Jetson ni GPU.

---

## 5. Implementar el ai_engine (FastAPI — Python)

Este es el bloque de código más grande. Sigue el orden de dependencias.

### 5.1 Orden de implementación recomendado

```
1. models/schemas.py           ← primero (todas las demás lo importan)
2. services/resource_manager.py
3. services/ingestion/chunker.py
4. services/ingestion/thumbnail_generator.py
5. services/ingestion/pdf_processor.py
6. services/ingestion/video_processor.py
7. services/hybrid_retriever.py   ← completar el esqueleto existente
8. services/hyde_expander.py
9. services/intent_router.py
10. services/grounding_verifier.py
11. services/stt.py              ← completar el esqueleto existente
12. services/llm_engine.py       ← completar esqueleto (mock en laptop, real en Jetson)
13. routers/ingest.py            ← completar esqueleto
14. routers/search.py            ← completar esqueleto
15. routers/voice_search.py      ← completar esqueleto
16. tests/                       ← escribir tests a medida que implementas
```

### 5.2 Cómo probar sin GPU en la laptop

`services/llm_engine.py` es el único componente que realmente necesita la Jetson para funcionar con calidad. Durante el desarrollo en laptop, hay dos opciones:

**Opción A — Mock hardcoded** (rápido, para desarrollar UI y flujo):
El `mock_main.py` del §4 ya lo hace. No requiere ningún modelo.

**Opción B — llama.cpp en CPU** (lento, pero el pipeline real funciona):
```bash
pip install llama-cpp-python

# Descargar un modelo GGUF pequeño para pruebas en CPU (~800 MB)
wget https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
     -O ~/jetson_models/llama32-1b-q4.gguf
```

Añadir en `services/llm_engine.py`, el bloque `init()`:
```python
# Detección automática de entorno: en laptop usa llama.cpp, en Jetson usa TRT-LLM
import platform
if platform.machine() == "aarch64" and settings.LLM_BACKEND == "tensorrt_llm":
    # Producción: TRT-LLM en Jetson
    ...
else:
    # Desarrollo: llama.cpp en laptop (CPU, lento pero funcional)
    from llama_cpp import Llama
    self._dev_model = Llama(
        model_path=os.path.expanduser("~/jetson_models/llama32-1b-q4.gguf"),
        n_ctx=512, n_threads=4, verbose=False
    )
```

### 5.3 Probar el ai_engine localmente (sin mock)

```bash
# Activar .env de desarrollo
cp ai_engine/config/platforms/orin_nano_8gb.env ai_engine/.env
# Ajustar rutas en .env para que apunten a tu laptop, no a /mnt/ssd
# CHROMADB_PATH=./chromadb_dev
# STORAGE_PATH=./storage

source ai_env/bin/activate
python -m uvicorn ai_engine.main:app --port 8000 --reload --env-file ai_engine/.env

# En otra terminal:
curl http://localhost:8000/api/health
```

---

## 6. Cambios en el CDN Backend (Node.js)

Hay **3 archivos nuevos + 2 modificaciones** en el `server/` existente.

### 6.1 Variables de entorno del server

Añadir a `server/.env`:
```bash
# AI Engine (apunta al mock en desarrollo, a la Jetson en producción)
AI_ENGINE_URL=http://localhost:8000
```

### 6.2 Los 3 archivos nuevos a crear

#### `server/src/routes/ai.ts`

```typescript
// server/src/routes/ai.ts
import { Router } from 'express';
import { authenticate } from '../middleware/auth.js';
import {
  searchHandler,
  searchStreamHandler,
  voiceSearchHandler,
} from '../controllers/aiSearchController.js';

const router = Router();

// Todas las rutas de IA requieren JWT válido
router.use(authenticate);

router.post('/search',        searchHandler);
router.post('/search/stream', searchStreamHandler);
router.post('/voice-search',  voiceSearchHandler);

export default router;
```

#### `server/src/controllers/aiSearchController.ts`

```typescript
// server/src/controllers/aiSearchController.ts
import { Request, Response } from 'express';
import { asyncHandler } from '../types/express.js';

const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';

// POST /api/ai/search — respuesta JSON completa
export const searchHandler = asyncHandler(async (req: Request, res: Response) => {
  const payload = {
    query:   req.body.query,
    context: {
      user_role:        req.user!.role,
      current_category: req.body.context?.current_category,
    },
  };

  const upstream = await fetch(`${AI_ENGINE_URL}/api/search`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  });

  if (!upstream.ok) {
    res.status(upstream.status).json({ error: 'AI Engine no disponible' });
    return;
  }

  const data = await upstream.json();
  res.json(data);
});

// POST /api/ai/search/stream — SSE proxy
export const searchStreamHandler = asyncHandler(async (req: Request, res: Response) => {
  const payload = {
    query:   req.body.query,
    context: { user_role: req.user!.role },
  };

  // Headers obligatorios para SSE — sin estos nginx/express bufferiza
  res.setHeader('Content-Type',      'text/event-stream');
  res.setHeader('Cache-Control',     'no-cache');
  res.setHeader('Connection',        'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');   // desactiva buffering de nginx

  const upstream = await fetch(`${AI_ENGINE_URL}/api/search/stream`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  });

  if (!upstream.ok || !upstream.body) {
    res.write('data: {"type":"error","message":"AI Engine no disponible"}\n\n');
    res.end();
    return;
  }

  // Pipe directo del SSE del AI Engine al cliente
  const reader = upstream.body.getReader();
  req.on('close', () => reader.cancel());

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    res.write(value);
  }
  res.end();
});

// POST /api/ai/voice-search — audio multipart → STT → search
export const voiceSearchHandler = asyncHandler(async (req: Request, res: Response) => {
  if (!req.file) {
    res.status(400).json({ error: 'Audio requerido (campo: audio)' });
    return;
  }

  const formData = new FormData();
  const blob = new Blob([req.file.buffer], { type: req.file.mimetype });
  formData.append('audio',   blob,  req.file.originalname || 'audio.wav');
  formData.append('context', JSON.stringify({ user_role: req.user!.role }));

  const upstream = await fetch(`${AI_ENGINE_URL}/api/voice-search`, {
    method: 'POST',
    body:   formData,
  });

  const data = await upstream.json();
  res.json(data);
});
```

#### `server/src/middleware/viewerAuth.ts`

```typescript
// server/src/middleware/viewerAuth.ts
// Middleware que protege las rutas /viewer/*
// Si el contenido requiere auth y no hay JWT válido → 302 al login con redirect back
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

export const viewerAuth = (req: Request, res: Response, next: NextFunction): void => {
  const token = req.cookies?.jwt || req.headers.authorization?.split(' ')[1];

  if (!token) {
    const returnTo = encodeURIComponent(req.originalUrl);
    res.redirect(302, `/login?returnTo=${returnTo}`);
    return;
  }

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as any;
    req.user = payload;
    next();
  } catch {
    const returnTo = encodeURIComponent(req.originalUrl);
    res.redirect(302, `/login?returnTo=${returnTo}`);
  }
};
```

### 6.3 Modificar `server/src/controllers/uploadController.ts`

Al final de la función `uploadContent`, justo antes del `return res.json(...)` final, añadir la notificación al AI Engine:

```typescript
// Añadir al final de uploadContent, después de actualizar el status a 'active'
// Notificar al AI Engine para indexación asíncrona
const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
fetch(`${AI_ENGINE_URL}/api/ingest`, {
  method:  'POST',
  headers: { 'Content-Type': 'application/json' },
  body:    JSON.stringify({ content_id: contentId }),
}).catch(() => {
  // Non-fatal: el CDN sigue operativo, la indexación se reintentará
  console.warn(`[AI] Engine no disponible al subir ${contentId} — se indexará después`);
});
```

### 6.4 Modificar `server/src/index.ts`

Añadir la ruta `/api/ai` y el middleware de multer para audio:

```typescript
// Añadir con los otros imports de rutas
import aiRoutes from './routes/ai.js';
import multer from 'multer';

// Multer en memoria para audio de búsqueda por voz (máx 2 MB, ~15s de audio)
const audioUpload = multer({
  storage: multer.memoryStorage(),
  limits:  { fileSize: 2 * 1024 * 1024 },
  fileFilter: (_, file, cb) => {
    const allowed = ['audio/wav', 'audio/webm', 'audio/ogg', 'audio/mp4'];
    cb(null, allowed.includes(file.mimetype));
  },
});

// Añadir con las otras rutas
app.use('/api/ai',              aiRoutes);
// Para voice-search, el audio viene como multipart — registrar multer en esa ruta
app.post('/api/ai/voice-search', audioUpload.single('audio'), aiRoutes);
```

---

## 7. El Frontend del Motor de Búsqueda — search_ui/

`search_ui/` es tu app React independiente. Ya está creada con todos sus componentes base.
`client/` es del compañero y no se toca.

### 7.1 Estructura ya creada

```
search_ui/
├── index.html
├── vite.config.ts          ← proxy /api → localhost:3000 ya configurado
├── src/
│   ├── App.tsx             ← router con una ruta: / → SearchPage
│   ├── main.tsx
│   ├── index.css           ← @import tailwindcss
│   ├── pages/
│   │   └── SearchPage.tsx  ← página principal: estado vacío + resultados
│   ├── components/search/
│   │   ├── SearchBar.tsx   ← input + Enter/Shift+Enter + VoiceButton
│   │   ├── VoiceButton.tsx ← MediaRecorder → POST /api/ai/voice-search
│   │   ├── AIOverview.tsx  ← texto streaming token a token con cursor
│   │   ├── SnippetCard.tsx ← tarjeta con enlace externo (viewer_url)
│   │   └── SearchResults.tsx ← grid con skeletons mientras carga
│   ├── hooks/
│   │   ├── useSSESearch.ts     ← SSE streaming completo
│   │   └── useVoiceRecorder.ts ← MediaRecorder + POST al backend
│   └── api/
│       └── aiSearch.ts     ← búsqueda JSON (no streaming) + health check
```

### 7.2 Cómo funciona SnippetCard — enlace externo

Cada tarjeta recibe un `viewer_url` que apunta a donde vive el contenido. El componente lo abre con `target="_blank"` — no navega dentro del `search_ui`:

```
"viewer_url": "/viewer/video/uuid-001?t=142"  → plataforma del compañero (client/)
"viewer_url": "http://biblioteca.gtr/libro/X"  → otra app del GTR
"viewer_url": "http://proyectos.gtr/proy/Y"    → portal de proyectos
```

El `search_ui` solo muestra el enlace. El usuario hace clic y navega a donde vive el recurso.

### 7.3 Arrancar en desarrollo

```bash
# Terminal 1: mock AI Engine (o el real en Jetson)
source ai_env/bin/activate
python -m uvicorn ai_engine.mock_main:app --port 8000 --reload

# Terminal 2: CDN server
cd /home/jleon/2026/PUCP/GTR/CDN/server && npm run dev

# Terminal 3: search_ui — TU frontend
cd /home/jleon/2026/PUCP/GTR/CDN/search_ui && npm run dev
# → http://localhost:5174
```

### 7.4 Qué queda por hacer en search_ui

| Tarea | Archivo | Prioridad |
|---|---|---|
| Ajustar paleta de colores / logo GTR-PUCP | `src/index.css`, `SearchPage.tsx` | Alta |
| Auth: leer/guardar JWT en localStorage | `src/context/AuthContext.tsx` (nuevo) | Alta |
| Página de login simple (o redirigir a client/) | `src/pages/LoginPage.tsx` (nuevo) | Media |
| Filtros por tipo (video / PDF / audio) | `SearchResults.tsx` | Media |
| Historial de búsquedas recientes | `useSearchHistory.ts` (nuevo) | Baja |

---

## 8. Schema SQL — Tabla de Ingesta

Hay que añadir la tabla `ai_ingestion_queue` a PostgreSQL. Ejecutar en tu PostgreSQL local:

```sql
-- scripts/init_ai_engine.sql
-- Ejecutar: psql -U cdn_user -d cdn_dev -f scripts/init_ai_engine.sql

CREATE TABLE IF NOT EXISTS ai_ingestion_queue (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id    UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'processing', 'done', 'error')),
    attempts      INT NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at  TIMESTAMPTZ
);

CREATE INDEX idx_ai_queue_status    ON ai_ingestion_queue(status);
CREATE INDEX idx_ai_queue_content   ON ai_ingestion_queue(content_id);

-- Vista útil para monitoreo
CREATE OR REPLACE VIEW ai_ingestion_status AS
SELECT
    q.status,
    COUNT(*) AS total,
    MAX(q.created_at) AS newest
FROM ai_ingestion_queue q
GROUP BY q.status;
```

```bash
# Ejecutar en tu PostgreSQL local
psql -U cdn_user -d cdn_dev -f scripts/init_ai_engine.sql

# Verificar
psql -U cdn_user -d cdn_dev -c "\d ai_ingestion_queue"
```

> Añadir también este archivo a `scripts/` del repo para que la Jetson lo ejecute al configurar la DB de producción.

---

## 9. Construir el Dataset de Calibración AWQ

La cuantización AWQ necesita al menos 512 muestras de texto educativo peruano. Este trabajo lo haces en la laptop **antes** de tener la Jetson — el resultado es un `.jsonl` que se sube al repo y se usa directamente en la Jetson.

```bash
# En la laptop, ejecutar desde la raíz del repo
source ai_env/bin/activate

python3 - << 'EOF'
import fitz, json, random, pathlib, re

chunks = []
storage = pathlib.Path("storage/documents")

# Opción A: PDFs ya subidos al CDN
if storage.exists():
    for pdf_path in storage.glob("**/*.pdf"):
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                text = page.get_text().strip()
                text = re.sub(r'\s+', ' ', text)  # normalizar espacios
                if len(text) > 200:
                    for i in range(0, min(len(text), 4000), 1000):
                        chunk = text[i:i+1000].strip()
                        if len(chunk) > 150:
                            chunks.append({"text": chunk})
            doc.close()
        except Exception as e:
            print(f"Error en {pdf_path.name}: {e}")

# Siempre incluir las semillas del repo
seeds = pathlib.Path("ai_engine/calibration/seeds.jsonl")
if seeds.exists():
    for line in seeds.read_text().splitlines():
        if line.strip():
            chunks.append(json.loads(line))

random.seed(42)
random.shuffle(chunks)

# Objetivo: 512 muestras
selected = chunks[:512]
if len(selected) < 100:
    print(f"⚠️  Solo {len(selected)} muestras. Necesitas más PDFs o textos del MINEDU.")
    print("   Descarga desde: https://www.minedu.gob.pe/textos-escolares/")
else:
    out = pathlib.Path("ai_engine/calibration/peru_educational_es.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for c in selected:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"✓ Dataset generado: {len(selected)} muestras → {out}")

EOF
```

---

## 10. Tests — Qué Probar en la Laptop

Todo esto se puede probar sin Jetson usando el mock o llama.cpp:

### 10.1 Tests del ai_engine (pytest)

```bash
source ai_env/bin/activate

# Crear tests básicos para verificar el pipeline de retrieval
pytest ai_engine/tests/ -v

# Test específico de retrieval (ChromaDB + BM25 + Cross-Encoder)
pytest ai_engine/tests/test_retrieval.py -v

# Test de chunking (no necesita GPU)
pytest ai_engine/tests/test_ingestion.py -v
```

### 10.2 Tests del server Node.js

```bash
cd server
npm test
```

### 10.3 Test end-to-end con mock

Esto simula el flujo completo sin Jetson:

```bash
# 1. Arrancar mock AI Engine
python -m uvicorn ai_engine.mock_main:app --port 8000 &

# 2. Arrancar server CDN
cd server && npm run dev &

# 3. Probar el proxy SSE end-to-end
curl -N -X POST http://localhost:3000/api/ai/search/stream \
  -H "Authorization: Bearer $(cat test_token.txt)" \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es una red LAN?"}' \
  | head -20
# Debe imprimir eventos SSE con cdn_results y tokens
```

### 10.4 Qué no se puede testear sin Jetson

- Latencia real del LLM (TRT-LLM); el mock responde en <100ms vs ~12s reales
- Comportamiento térmico NVPModel
- OOM bajo carga real
- Calidad de transcripción Whisper en audio de campo

---

## 11. Git — Flujo de Trabajo Laptop ↔ Jetson

La Jetson corre código del mismo repo que tú desarrollas en la laptop. El flujo es:

```
Laptop (desarrollas) → git push → repo remoto → Jetson: git pull
```

### 11.1 Configurar el repo remoto

```bash
# Opción A: GitHub/GitLab privado (recomendado)
git remote add origin https://github.com/tu-usuario/cdn-gtr-pucp.git
git push -u origin main

# Opción B: Servidor git local en red (si no hay internet confiable)
# En el PC que actúa de servidor:
git init --bare /srv/git/cdn.git
# En la laptop:
git remote add origin ssh://usuario@servidor-local/srv/git/cdn.git
```

### 11.2 `.gitignore` — qué NO subir al repo

Asegúrate de que el `.gitignore` incluye:

```
# Modelos (son demasiado grandes para git — usar git-lfs o rsyncs aparte)
ai_engine/models_cache/
ai_engine/trt_engines/
ai_engine/trt_checkpoints/
ai_engine/chromadb_data/
*.gguf
*.engine
*.safetensors

# Datos locales
ai_engine/.env
storage/videos/
storage/temp/

# Python
.venv/
__pycache__/
*.pyc

# Node
node_modules/
dist/
```

Los modelos se transfieren a la Jetson por **rsync o USB** (ver guia-inicio.md §7), no por git.

### 11.3 En la Jetson

```bash
# Después de hacer push desde la laptop
cd /mnt/ssd/CDN
git pull origin main

# Reiniciar el servicio para cargar el nuevo código
sudo systemctl restart ai-engine
```

---

## 12. Orden de Trabajo Recomendado por Semana

| Semana | Qué hacer en la laptop | Requiere Jetson |
|---|---|---|
| **Ahora mismo** | Descarga de modelos HF en background (§3) | No |
| **Ahora mismo** | Instalar entornos dev (§2) | No |
| **Semana 1** | `models/schemas.py` + `services/resource_manager.py` + `services/ingestion/chunker.py` | No |
| **Semana 1** | `scripts/init_ai_engine.sql` + probar con PostgreSQL local (§8) | No |
| **Semana 1** | Mock AI Engine funcional (§4) | No |
| **Semana 2** | `services/ingestion/pdf_processor.py` + `video_processor.py` + `thumbnail_generator.py` | No |
| **Semana 2** | `services/hybrid_retriever.py` completo (ChromaDB + BM25 + Cross-Encoder) | No (CPU lento) |
| **Semana 2** | Ingestar PDFs de prueba y verificar chunks en ChromaDB | No |
| **Semana 3** | `services/intent_router.py` + `services/hyde_expander.py` | No |
| **Semana 3** | `services/grounding_verifier.py` | No |
| **Semana 3** | `routers/search.py` + `routers/ingest.py` + `routers/voice_search.py` completos | No |
| **Semana 3** | `services/stt.py` completo + test con audio WAV real | No |
| **Semana 4** | `server/src/routes/ai.ts` + `controllers/aiSearchController.ts` + `middleware/viewerAuth.ts` | No |
| **Semana 4** | Ajustar `search_ui/` — auth, estilos GTR-PUCP, filtros (§7) | No |
| **Semana 4** | Dataset calibración AWQ (§9) — commit al repo | No |
| **Semana 4** | Tests end-to-end completos con mock (§10) | No |
| **Semana 4-5** | **Adquirir y flashear Jetson Orin Nano 8GB** | ✅ — guia-inicio.md §3 |
| **Semana 5** | Compilar engines TRT-LLM en Jetson (lleva 3–5h) | ✅ — guia-inicio.md §9 |
| **Semana 5** | `services/llm_engine.py` con backend TRT-LLM real | ✅ |
| **Semana 5** | Checklist end-to-end Fase 1 (guia-inicio.md §12) | ✅ |
| **Semana 6–10** | Iteración, datasets de evaluación, pruebas de carga | ✅ |
| **Semana 10** | Migración a Orin NX 16GB (guia-inicio.md §13) | ✅ |
