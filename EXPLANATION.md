# EXPLANATION.md — Explicación Completa del Proyecto

> **Proyecto**: GTR-PUCP — CDN Educativa Offline  
> **Fecha**: Marzo 2026  
> **Para quién**: Cualquier miembro del equipo que quiera entender **cómo funciona el código** desde adentro — qué hace cada carpeta, cada archivo, cada función, y cómo fluye una petición de principio a fin.

---

## Índice

1. [Visión General del Sistema](#1-visión-general-del-sistema)
2. [Mapa de carpetas del repositorio](#2-mapa-de-carpetas-del-repositorio)
3. [Carpeta `server/` — Backend CDN (Node.js)](#3-carpeta-server--backend-cdn-nodejs)
4. [Carpeta `ai_engine/` — Motor IA (Python/FastAPI)](#4-carpeta-ai_engine--motor-ia-pythonfastapi)
5. [Carpeta `search_ui/` — Frontend Buscador IA (React)](#5-carpeta-search_ui--frontend-buscador-ia-react)
6. [Carpeta `client/` — Frontend Plataforma Educativa (React)](#6-carpeta-client--frontend-plataforma-educativa-react)
7. [Carpeta `storage/` — Almacenamiento de archivos](#7-carpeta-storage--almacenamiento-de-archivos)
8. [Carpeta `scripts/` — SQL de inicialización](#8-carpeta-scripts--sql-de-inicialización)
9. [Carpeta `docs/` — Documentación técnica](#9-carpeta-docs--documentación-técnica)
10. [Flujos completos de principio a fin](#10-flujos-completos-de-principio-a-fin)

---

## 1. Visión General del Sistema

El sistema tiene **dos grandes procesos** que corren de forma independiente:

```
┌─────────────────────────────────────────────────────────────────────┐
│  PROCESO 1: CDN Backend                                              │
│  Tecnología: Node.js + Express + TypeScript                         │
│  Puerto: 3000                                                        │
│  Rol: gestionar usuarios, subir/servir contenido, streaming, cache  │
│  Base de datos: PostgreSQL (metadatos) + Redis (cache)               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  PROCESO 2: AI Engine                                                │
│  Tecnología: Python + FastAPI                                        │
│  Puerto: 8000                                                        │
│  Rol: búsqueda inteligente con LLM + embeddings + STT               │
│  Durante desarrollo: mock sin GPU ni LLM real                        │
└─────────────────────────────────────────────────────────────────────┘

Ambos procesos son completamente independientes: si el AI Engine falla,
el CDN backend sigue sirviendo contenido normalmente.
```

Y **dos frontends** que el usuario ve en el navegador:

```
search_ui (React, :5174)  →  interfaz del buscador con IA
client    (React, :5173)  →  plataforma educativa (catálogo, visor)
```

---

## 2. Mapa de carpetas del repositorio

```
CDN/
├── server/           → Backend Node.js/TypeScript (CDN principal)
│   └── src/
│       ├── index.ts            ← Punto de entrada del servidor
│       ├── config/             ← Conexiones PostgreSQL y Redis
│       ├── routes/             ← Definición de rutas HTTP
│       ├── controllers/        ← Lógica de cada endpoint
│       ├── middleware/         ← Auth JWT, upload con Multer
│       ├── services/           ← Lógica de negocio (storage, ffmpeg)
│       ├── models/             ← Tipos TypeScript (interfaces, DTOs)
│       └── types/              ← Extensiones de tipos Express
│
├── ai_engine/        → Motor IA Python/FastAPI (AI backend)
│   ├── main.py                 ← Entrada real (con LLM, para Jetson)
│   ├── mock_main.py            ← Entrada mock (para desarrollo/PC)
│   ├── config/
│   │   ├── settings.py         ← Configuración multi-plataforma
│   │   └── prompts.py          ← System prompts del LLM por nivel
│   ├── routers/
│   │   ├── health.py           ← GET /api/health
│   │   ├── search.py           ← POST /api/search + /search/stream (SSE) ✓
│   │   ├── voice_search.py     ← POST /api/voice-search (STT + pipeline) ✓
│   │   └── ingest.py           ← POST /api/ingest + GET /ingest/status + reindex-all ✓
│   ├── services/
│   │   ├── thermal_manager.py  ← Control térmico Jetson
│   │   ├── hybrid_retriever.py ← BM25 + ChromaDB + Cross-Encoder (pipeline completo) ✓
│   │   ├── llm_engine.py       ← TRT-LLM + HF fallback + speculative decoding ✓
│   │   ├── stt.py              ← Whisper Tiny/Small STT ✓
│   │   └── ingestion/          ← Subpaquete de ingesta ✓
│   │       ├── __init__.py     ← Exporta ingest_content()
│   │       ├── chunker.py      ← Chunking jerárquico summary/section/sentence
│   │       ├── pdf_extractor.py← PyMuPDF + OCR Tesseract + python-docx
│   │       ├── thumbnail_generator.py ← FFmpeg/PyMuPDF por tipo de contenido
│   │       └── pipeline.py     ← Orquestador principal del pipeline de ingesta
│   └── calibration/
│       └── seeds.jsonl         ← Dataset para calibración AWQ
│
├── search_ui/        → Frontend React del buscador IA (:5174)
│   └── src/
│       ├── pages/SearchPage.tsx      ← Página principal
│       ├── components/search/        ← Componentes UI
│       └── hooks/                    ← Lógica de llamadas a la API
│
├── client/           → Frontend React de la plataforma (:5173)
│   └── src/
│
├── storage/          → Archivos físicos del CDN
│   ├── videos/       ← Videos subidos
│   ├── documents/    ← PDFs subidos
│   ├── thumbnails/   ← Miniaturas generadas por FFmpeg
│   └── temp/         ← Área temporal de uploads (se vacía)
│
├── scripts/          → SQL para inicializar la base de datos
│   ├── init_database_v2.sql  ← Schema completo con tablas de IA
│   └── init_ai_engine.sql    ← Schema específico del AI Engine
│
└── docs/             → Documentación técnica
```

---

## 3. Carpeta `server/` — Backend CDN (Node.js)

### ¿Qué hace en una frase?
Es el **corazón del sistema**. Gestiona usuarios, recibe archivos subidos, los procesa con FFmpeg, los guarda en disco y los sirve al navegador mediante streaming HTTP/Range.

---

### `server/src/index.ts` — Punto de entrada

**¿Qué hace?**  
Es el primer archivo que se ejecuta cuando corres `npm run dev`. Crea la app Express, registra todos los middlewares y rutas, y arranca el servidor escuchando en el puerto 3000.

**Flujo de arranque**:
1. `dotenv.config()` → carga las variables del archivo `.env`
2. Se crea la app `express()`
3. Se aplican middlewares globales:  
   - `helmet()` → añade cabeceras HTTP de seguridad (X-Frame-Options, etc.)  
   - `cors()` → permite peticiones desde los frontends (5173, 5174)  
   - `express.json()` → parsea cuerpos JSON automáticamente
4. Se registran las rutas: `/api/auth`, `/api/categories`, `/api/content`, `/api/upload`
5. Se define el endpoint `/health` que consulta PostgreSQL y Redis en tiempo real
6. Al final: `app.listen(PORT, ...)` — el servidor empieza a aceptar conexiones

---

### `server/src/config/database.ts` — Conexión a PostgreSQL

**¿Qué hace?**  
Crea y exporta un **pool de conexiones** a PostgreSQL usando la librería `pg`. Un pool reutiliza conexiones en lugar de abrir una nueva por cada petición — mejora el rendimiento enormemente.

**Funciones clave**:

| Función | Para qué se llama | Por qué |
|---------|------------------|---------|
| `query(sql, params)` | Desde cualquier controller | Ejecuta un SQL y retorna los resultados; encapsula errores y mide tiempo |
| `getClient()` | En operaciones de múltiples pasos que necesitan transacción | Obtiene una conexión exclusiva del pool con timeout de 5 s para evitar leaks |
| `testConnection()` | Al arrancar en `index.ts` y en el endpoint `/health` | Verifica que PostgreSQL es alcanzable antes de servir tráfico |

**El pool**: configurado con máximo 20 conexiones simultáneas. Si hay 20 queries corriendo a la vez, la 21ª espera a que una se libere. `idleTimeoutMillis: 30000` cierra conexiones inactivas después de 30 s.

---

### `server/src/config/redis.ts` — Conexión a Redis

**¿Qué hace?**  
Redis es el **cache** del sistema. En lugar de consultar PostgreSQL en cada request (costoso), ciertos resultados se guardan en Redis por un tiempo configurable (TTL).

**Funciones clave**:

| Función | Para qué se llama | Por qué |
|---------|------------------|---------|
| `cacheGet(key)` | Al inicio de `getContent()` y `getContentById()` | Primero revisar si ya hay resultado guardado; evita consultas innecesarias a la DB |
| `cacheSet(key, value, ttl)` | Después de consultar la DB | Guarda el resultado para las próximas N segundos (defecto: 3600 s = 1 hora) |
| `cacheDelete(pattern)` | Cuando se modifica contenido | Invalida el cache para que los datos no queden obsoletos |
| `testRedisConnection()` | Al arrancar en `index.ts` | Verifica que Redis responde; si falla el sistema sigue pero sin cache |

**¿Por qué serializar con JSON?** Redis solo guarda strings. Por eso `cacheSet` hace `JSON.stringify(value)` antes de guardar, y `cacheGet` hace `JSON.parse(cached)` al recuperar.

---

### `server/src/routes/` — Definición de rutas

Estos archivos son **puras definiciones de rutas** — conectan una URL + método HTTP con un controller. No contienen lógica.

| Archivo | Rutas que define |
|---------|-----------------|
| `auth.ts` | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| `categories.ts` | `GET /api/categories`, `POST /api/categories`, `PUT /api/categories/:id`, `DELETE /api/categories/:id` |
| `content.ts` | `GET /api/content`, `GET /api/content/:id`, `GET /api/content/:id/stream`, `GET /api/content/:id/thumbnail` |
| `upload.ts` | `POST /api/upload` (protegida con `authenticate` middleware) |

**¿Por qué separar rutas de controllers?**  
Principio de separación de responsabilidades: las rutas definen **qué URL → qué función**, los controllers definen **qué hace esa función**. Facilita agregar middlewares a rutas específicas (por ejemplo, solo `/api/upload` necesita autenticación).

---

### `server/src/controllers/authController.ts` — Login y sesiones

**¿Qué hace?**  
Gestiona el proceso de autenticación completo: login, logout, y consulta del usuario actual.

**Función `login()` — flujo detallado**:

```
POST /api/auth/login { username, password }
     │
     ▼
1. Buscar usuario en DB por username
     │
     ▼
2. ¿Está bloqueado? (locked_until > NOW())
     │  sí → error 423 "Account locked"
     │  no → continuar
     ▼
3. bcrypt.compare(password, user.password_hash)
     │  falla → incrementar login_attempts
     │          ¿intentos >= 5? → bloquear 15 minutos
     │  ok → continuar
     ▼
4. Resetear login_attempts = 0; actualizar last_login
     │
     ▼
5. jwt.sign({ id, username, role }, JWT_SECRET, { expiresIn: '7d' })
     │
     ▼
6. Guardar sesión en tabla `sessions` con hash SHA-256 del token
     │
     ▼
7. Responder con { token, user: { id, username, role } }
```

**¿Por qué guardar la sesión en DB además del JWT?**  
El JWT es autocontenido (no necesita DB para validarse), pero si el usuario cierra sesión o el admin desactiva una cuenta, necesitamos poder invalidar el token antes de que expire. La tabla `sessions` permite eso: el middleware `authenticate` verifica que la sesión exista Y esté activa en la DB.

---

### `server/src/middleware/auth.ts` — Middleware de autenticación

**¿Qué hace?**  
Es el **guardián** de todas las rutas protegidas. Se ejecuta **antes** del controller en las rutas que lo usan.

**Flujo de `authenticate()`**:
```
Petición entra con header: Authorization: Bearer eyJhbGc...
     │
     ▼
1. Extraer token del header
     │
     ▼
2. jwt.verify(token, JWT_SECRET)    ← valida firma y expiración
     │  inválido → 401
     │  ok → objeto { id, username, role }
     ▼
3. Calcular SHA-256(token) → tokenHash
   Buscar en tabla sessions WHERE token_hash = tokenHash AND is_active = true AND expires_at > NOW()
     │  no existe o expirada → 401 "Invalid or expired token"
     │  ok → actualizar last_activity
     ▼
4. req.user = { id, username, role }   ← disponible en el controller
     │
     ▼
5. next()   ← pasa al controller
```

**`authorize(...roles)`**:  
Un middleware de fábrica — lo llamas así: `authorize('teacher', 'superadmin')`. Retorna una función middleware que verifica que `req.user.role` esté en la lista de roles permitidos.

---

### `server/src/controllers/contentController.ts` — Listar y buscar contenido

**¿Qué hace?**  
Gestiona la consulta del catálogo de contenido con filtros, paginación, búsqueda de texto y cache.

**Función `getContent()` — flujo**:
```
GET /api/content?search=redes&type=video&page=2&sort=popular
     │
     ▼
1. Extraer parámetros de req.query
     │
     ▼
2. Intentar cacheGet("content:list:{params}")
     │  cache hit → responder inmediatamente (sin tocar DB)
     │  cache miss → continuar
     ▼
3. Construir WHERE dinámico:
   - Siempre: "deleted_at IS NULL AND status = 'active'"
   - Si hay category: "AND category_id = $1"
   - Si hay type: "AND type = $2"
   - Si hay search: "AND to_tsvector('spanish', title || description) @@ plainto_tsquery('spanish', $3)"
           ← búsqueda de texto completo en español con PostgreSQL
     │
     ▼
4. Ejecutar query con LIMIT/OFFSET para paginación
     │
     ▼
5. cacheSet(key, result, 300)   ← guardar 5 minutos en Redis
     │
     ▼
6. Responder con { data: [...], pagination: { total, page, limit } }
```

**¿Por qué `to_tsvector`?**  
PostgreSQL tiene búsqueda de texto completo integrada. `to_tsvector('spanish', texto)` tokeniza el texto normalizando palabras (singular/plural, acentos). `plainto_tsquery` convierte la búsqueda del usuario en una query de texto completo. Es mucho más potente que `ILIKE '%palabra%'` y mucho más eficiente para datasets grandes.

---

### `server/src/controllers/uploadController.ts` — Subir contenido

**¿Qué hace?**  
Orquesta el pipeline completo de subida de un archivo: temp → validar → hash → storage permanente → FFmpeg → thumbnail → base de datos.

**Flujo completo de `uploadContent()`**:
```
POST /api/upload (multipart/form-data)
     │  Multer intercepta: guarda archivo en /storage/temp/
     ▼
1. Validar: ¿hay archivo? ¿hay título? ¿hay category_id?
     │
     ▼
2. storageService.moveToStorage(file.path, tipo, extensión)
     │  → calcula SHA-256 del archivo (streaming, sin cargar en RAM)
     │  → nombre del archivo = hash.ext  (ej: a3f9b2...c1.mp4)
     │  → mueve a /storage/videos/ o /storage/documents/
     ▼
3. Verificar duplicados: SELECT id FROM content WHERE file_hash = $1
     │  duplicado → error 409 "Duplicate file"
     │  nuevo → continuar
     ▼
4. Si es video: ffmpegService.getVideoMetadata(filePath)
     │  → duración, resolución, bitrate, formato
     │  → genera thumbnail: frame a los 10 segundos → /storage/thumbnails/
     ▼
5. Si es PDF: extraer número de páginas (pdfparse o similar)
     ▼
6. INSERT INTO content (title, type, file_path, file_hash, file_size,
                        duration_seconds, thumbnail_path, metadata, ...)
   con status = 'active'
     ▼
7. Responder 201 { content_id, message }
```

**¿Por qué el nombre del archivo es el hash?**
- Previene duplicados en disco: dos uploads del mismo archivo producen el mismo hash → mismo nombre → el segundo no sobreescribe, solo se detecta en el paso 3
- Hace que el almacenamiento sea **content-addressable** (como Git): el nombre identifica el contenido, no el origen

---

### `server/src/controllers/streamController.ts` — Streaming de video

**¿Qué hace?**  
Sirve archivos de video con soporte para **HTTP Range Requests**, que es como funciona el streaming de video en los navegadores modernos.

**Función `streamContent()` — flujo**:
```
GET /api/content/:id/stream
Headers: Range: bytes=0-1048575
     │
     ▼
1. Buscar en DB: file_path, file_size, mime_type, type
     │  no existe o inactivo → 404
     ▼
2. Construir ruta absoluta: path.resolve(STORAGE_PATH, content.file_path)
     │  archivo no existe en disco → 404
     ▼
3. Registrar acceso en access_log (sin await — no bloquea la respuesta)
     ▼
4. ¿Hay header Range?
   SÍ → parse "bytes=start-end"
       → fs.createReadStream(filePath, { start, end })
       → headers: Content-Range, Content-Length, HTTP 206 Partial Content
       → file.pipe(res)   ← envía los bytes al cliente
   
   NO → enviar archivo completo
       → headers: Accept-Ranges: bytes, HTTP 200
       → fs.createReadStream(filePath).pipe(res)
```

**¿Por qué 206 Partial Content?**  
Los navegadores piden el video en **trozos** (chunks) conforme el usuario lo reproduce. Primero piden bytes 0-1MB, los reproducen, luego piden el siguiente MB, etc. Esto permite empezar a reproducir sin descargar el archivo entero, y permite al usuario hacer seek (ir a un tiempo específico).

---

### `server/src/services/storageService.ts` — Gestión de archivos

**Clase `StorageService`**

| Método | Para qué se llama | Por qué |
|--------|------------------|---------|
| `calculateFileHash(filePath)` | Desde `moveToStorage()` | Calcula SHA-256 del archivo en streaming con `crypto.createHash('sha256')` para no cargar el archivo entero en RAM |
| `moveToStorage(tempPath, type, ext)` | Desde `uploadController` | Mueve el archivo del directorio temporal al permanente, usando el hash como nombre de archivo; si ya existe por hash, elimina el temporal |
| `fileExists(relativePath)` | Desde controllers de stream | Verifica existencia antes de intentar leer, para dar error claro |

---

### `server/src/services/ffmpegService.ts` — Procesamiento de video

**¿Qué hace?**  
Usa FFmpeg (herramienta externa del sistema) para extraer metadatos de videos y generar thumbnails.

Métodos clave (inferidos del uso en uploadController):
- `getVideoMetadata(filePath)` → llama `ffprobe` para extraer duración, resolución, bitrate
- `generateThumbnail(filePath, outputPath, seconds)` → extrae un frame en el segundo especificado y lo guarda como JPG en `/storage/thumbnails/`

**¿Por qué usar FFmpeg y no una librería pura Node.js?**  
FFmpeg es el estándar de la industria para procesamiento multimedia. Soporta prácticamente todos los formatos de video/audio. Una librería pura JS no tendría esa cobertura y rendería peor.

---

## 4. Carpeta `ai_engine/` — Motor IA (Python/FastAPI)

### ¿Qué hace en una frase?
Es el **cerebro inteligente** del sistema. Recibe una pregunta (texto o voz), la procesa con embeddings + BM25 + LLM, y devuelve un resumen generado + tarjetas con los contenidos del CDN más relevantes.

> **Estado actual**: Pipeline completo implementado. En PC sin TRT-LLM ni GPU el sistema arranca con fallback graceful; para pruebas reales de frontend usar `mock_main.py` que no necesita ningún modelo.

---

### `ai_engine/main.py` — Entrada real (para Jetson)

**¿Qué hace?**  
Define la app FastAPI con su ciclo de vida completo.

**Función `lifespan(app)` — arranque ordenado**:

```python
# Se ejecuta UNA SOLA VEZ cuando arranca el servidor

1. thermal_manager.start()
   ← Lo primero. Si la Jetson está muy caliente, reducir carga ANTES 
     de cargar modelos pesados

2. retriever.init()
   ← Carga el modelo de embeddings (intfloat/multilingual-e5-small)
     y conecta ChromaDB desde disco

3. llm_engine.init()
   ← Carga los engines TensorRT-LLM en VRAM:
     draft model (LLaMA 3.2 1B INT4) + target model (Phi-3.5 Mini o LLaMA 3 8B INT4)
     Esta es la operación MÁS LARGA del arranque (~30-60 segundos)

4. stt.init()
   ← Carga Whisper Tiny en CPU (para transcribir consultas de voz)

yield   ← El servidor está listo para recibir peticiones

# Al cerrar (Ctrl+C):
5. thermal_manager.stop()    ← detiene el loop de monitoreo
6. llm_engine.shutdown()     ← libera VRAM
```

**¿Por qué este orden?**  
El gestor térmico debe estar activo antes de cargar modelos porque TRT-LLM genera calor durante la carga. Si la Jetson ya está caliente y se carga el modelo, puede hacer thermal throttling en medio de la carga y corromperse.

---

### `ai_engine/mock_main.py` — Servidor mock (para PC / desarrollo)

**¿Qué hace?**  
Es una versión del AI Engine que responde con **datos ficticios pre-definidos** sin necesitar GPU, LLM ni ninguna dependencia pesada. Solo necesita FastAPI.

**Flujo de `search_stream()`**:
```python
POST /api/search/stream { "query": "redes LAN" }
     │
     ▼
1. yield SSE: { "type": "cdn_results", "data": MOCK_CDN_RESULTS }
   ← Primero las tarjetas mock (2 resultados ficticios de TCP/IP y CISCO)
     con un pequeño delay de 0.3s para simular latencia real
     │
     ▼  
2. Para cada palabra en MOCK_AI_TEXT:
   yield SSE: { "type": "token", "text": "palabra " }
   await asyncio.sleep(0.05)
   ← Simula el streaming token a token de un LLM real
     │
     ▼
3. yield SSE: { "type": "done", "suggestions": [...] }
   ← Cierre del stream con sugerencias de búsqueda
```

**¿Por qué es útil el mock?**  
Permite desarrollar y probar **el frontend al 100%** sin tener la Jetson. El formato SSE del mock es idéntico al del AI Engine real, entonces cuando se conecte a la Jetson real, el frontend funciona sin cambios.

---

### `ai_engine/config/settings.py` — Configuración multi-plataforma

**¿Qué hace?**  
Es el **único lugar** donde se define la configuración de cada plataforma. Cambiar de una Jetson Orin Nano a una Orin NX es tan simple como cambiar una variable de entorno.

**Cómo funciona**:
```python
PLATFORM = os.getenv("AI_PLATFORM", "orin_nx_16gb")

_CONFIGS = {
    "orin_nano_8gb": { ... configuración conservadora ... },
    "orin_nx_8gb":   { ... configuración media ... },
    "orin_nx_16gb":  { ... configuración estándar ... },
    "agx_orin_32gb": { ... configuración máxima ... },
}

# Exportar constantes directamente para import limpio
LLM_BACKEND = _cfg["LLM_BACKEND"]
EMBED_DEVICE = _cfg["EMBED_DEVICE"]   # "cuda" en Jetson, "cpu" en PC
TOP_K_FINAL  = _cfg["TOP_K_FINAL"]    # cuántos resultados finales mostrar
...
```

**¿Por qué no usar un solo .env?**  
Porque los parámetros de cada plataforma son interdependientes: la Orin Nano usa `TOP_K=15` porque tiene poca memoria, la AGX usa `TOP_K=30` porque tiene más. Si usaras un .env per platform tendrías que acordarte de cambiar múltiples valores. Aquí cambias un solo string y todo se reconfigura.

---

### `ai_engine/config/prompts.py` — System prompts del LLM

**¿Qué hace?**  
Define los **textos de instrucción** que le dicen al LLM cómo debe comportarse según el nivel de triaje.

**Los cuatro niveles** (el "triaje adaptativo"):

| Nivel | Cuándo se usa | Qué hace el LLM |
|-------|--------------|-----------------|
| `L1` | Hay fuentes CDN relevantes | Responde SOLO con información de las fuentes, sin inventar nada (modo más estricto) |
| `L2` | Fuentes CDN parciales | Puede complementar con conocimiento general, pero marcando claramente qué viene de CDN y qué de conocimiento general |
| `L3` | Sin fuentes CDN | Solo conocimiento general; avisa al usuario que no hay contenido local sobre el tema |
| `L4` | Consulta ambigua | Formula preguntas aclaratorias en lugar de responder |

**¿Por qué niveles y no siempre L2?**  
L1 es el modo más seguro — imposibilita alucinaciones pero requiere fuentes buenas. Si siempre usaras L2, el LLM podría mezclar datos inventados con datos reales sin que el usuario lo sepa. El triaje decide qué nivel usar según la calidad de los resultados del retriever.

**`SOURCE_TEMPLATE`**:  
Cada chunk recuperado se formatea como `[FUENTE N] Título: ... Fragmento: ...` para que el LLM pueda citar las fuentes por número.

---

### `ai_engine/routers/ingest.py` — Ingesta al índice vectorial ✓

**¿Qué hace?**  
Recibe el `content_id` de un contenido recién subido y dispara el pipeline de indexación en background.

**Endpoints implementados**:

| Endpoint | Descripción |
|----------|-------------|
| `POST /ingest` | Encola la ingesta de un contenido; retorna 202 inmediatamente con `status: "queued"` |
| `GET /ingest/status/{id}` | Consulta el estado del job: `queued → running → ok/error` |
| `POST /ingest/reindex-all` | Reindexado completo; requiere `{"confirm": true}` para protección |

**Flujo de `POST /ingest`**:
```
POST /ingest { content_id: "uuid" }
     │
     ▼  Si ya hay un job running para ese id → retorna {status: "running"}
     │
     ▼  background_tasks.add_task(_run_ingest_job, content_id)
     │  → retorna 202 {status: "queued"} inmediatamente
     │
     │  [En background:]    pipeline.ingest_content(content_id)
     │  1. GET /api/content/{id} al CDN backend → metadata
     │  2. Extraer texto (STT / PDF / DOCX según tipo)
     │  3. Chunking jerárquico
     │  4. Embeddings → ChromaDB  +  BM25 update
     │  5. Generar thumbnail si no existe
     │  6. PATCH /api/content/{id} → ai_indexed=true
```

**Estado del job** se guarda en `_job_status: dict[str, dict]` en memoria (Redis en producción futura).

---

### `ai_engine/services/ingestion/` — Subpaquete de ingesta ✓

#### `chunker.py` — Chunking jerárquico

**¿Qué hace?**  
Convierte texto plano o segmentos Whisper en tres niveles de chunks para indexación vectorial:

| Nivel | Tokens máx | Uso |
|-------|-----------|-----|
| `summary` | 256 | Representación completa del documento; para ranking inicial |
| `section` | 512 (overlap 64) | Párrafos; para contexto RAG en el LLM |
| `sentence` | 128 | Oraciones individuales; para snippets y grounding |

**Dos funciones públicas**:
- `chunk_text(text, source_type)` → para PDFs, DOCX, texto libre
- `chunk_transcript(segments)` → para transcripciones Whisper; **preserva timestamps** de cada segmento para hacer deep links `?t=segundos`

**¿Por qué tres niveles?**  
Diferentes niveles sirven para diferentes fases de la búsqueda: `summary` para encontrar el documento correcto, `section` para darle contexto al LLM, `sentence` para mostrar el snippet exacto al usuario.

---

#### `pdf_extractor.py` — Extracción de texto

**¿Qué hace?**  
Extrae texto de documentos con estrategia de dos niveles:
1. **PyMuPDF** (`fitz`) — extrae texto embebido directamente (rápido, sin GPU)
2. **Tesseract OCR** — fallback automático si una página tiene < 50 chars de texto embebido (páginas escaneadas)

**Función unificada `extract_text(file_path, mime_type)`**:
- `.pdf` → PyMuPDF + OCR por página según umbral
- `.docx` / `.doc` → python-docx
- `.txt` / `.md` → lectura directa UTF-8

---

#### `thumbnail_generator.py` — Generación de miniaturas

**¿Qué hace?**  
Genera miniaturas JPG (320×180) según el tipo de contenido:

| Tipo | Estrategia |
|------|------------|
| `video` | FFmpeg: extrae frame en t=10s |
| `pdf` / `document` | PyMuPDF: renderiza primera página |
| `audio` | Copia ícono estático de la categoría |
| `image` | FFmpeg: redimensiona y aplica padding |

Si FFmpeg o PyMuPDF no están disponibles, usa un ícono genérico negro de fallback.

---

#### `pipeline.py` — Orquestador principal ✓

**¿Qué hace?**  
Es el corazón de la ingesta. Coordina todos los pasos en orden:

```
ingest_content(content_id)
     │
     ▼  Semáforo de concurrencia (1-2 tareas según INGESTION_MODE)
     │
     ▼  1. _fetch_content_metadata() → GET al CDN backend
     │
     ▼  2. Según content_type:
     │    video/audio → stt.transcribe_for_ingest() → chunk_transcript()
     │    pdf/document → extract_text() → chunk_text()
     │    image → chunk_text(title + description)
     │
     ▼  3. _index_chunks() → retriever.add_chunks(ids, texts, metadatas)
     │    Cada chunk tiene metadata: content_id, chunk_type, title,
     │    category, timestamp_start/end (para deep links en videos)
     │
     ▼  4. _update_bm25() → retriever.update_bm25(texts)
     │
     ▼  5. generate_thumbnail() si no existe
     │
     ▼  6. _notify_indexed() → PATCH al CDN backend
```

**Control de concurrencia**:  
`INGESTION_MODE="semaphore_cautious"` (Orin Nano) permite solo 1 ingesta simultánea para no competir con las búsquedas en tiempo real.  
`INGESTION_MODE="realtime"` (Orin NX+) permite 2.

---

### `ai_engine/routers/search.py` — Búsqueda con SSE streaming ✓

**¿Qué hace?**  
Implementa el pipeline completo de búsqueda conectando retriever + LLM y sirviéndolo como stream SSE.

**Triaje adaptativo** (función `_triage_from_query_and_chunks`):

| Nivel | Condición | System prompt |
|-------|------------|---------------|
| L1 | ≥ 1 chunk con score ≥ 0.70 | Solo fuentes CDN, sin inventar |
| L2 | ≥ 1 chunk con score ≥ 0.35 | Fuentes CDN + conocimiento general marcado |
| L3 | Sin chunks útiles | Solo conocimiento general con aviso |
| L4 | Sin chunks + query ≤ 3 palabras | Hace preguntas aclaratorias |

**Endpoint `POST /search/stream`** (principal, usado por `useSSESearch.ts`):
```
Orden de eventos SSE:
1. cdn_results  → tarjetas CDN (el frontend las renderiza de inmediato)
2. token × N    → fragmentos del resumen generado por el LLM
3. done         → cierre con nivel de triáje, sugerencias y grounding score
```

**Endpoint `POST /search`** (no-streaming, útil para testing/curl):
- Agrega todos los tokens y retorna JSON completo.

**Tarjetas CDN** (`_chunks_to_cdn_cards`): deduplica por `content_id`, preserva el chunk de mayor score por contenido, construye `viewer_url` con `?t=segundos` para videos (deep link al tiempo exacto de la transcripción).

---

### `ai_engine/routers/voice_search.py` — STT + búsqueda ✓

**¿Qué hace?**  
Reúcne en un solo endpoint el ciclo completo: audio → texto → búsqueda semántica.

**Flujo del endpoint `POST /voice-search`**:
```
1. Validar audio: formato (.webm, .wav, .ogg, .mp3, .m4a, .flac), tamaño (≤ 5 MB)
2. Guardar bytes en /tmp/audio_xxxx.webm
3. stt.transcribe(tmp_path) → {"text": "...", "language": "es"}
4. Borrar archivo temporal (finally)
5. retriever.search(text) → chunks
6. llm_engine.generate_stream(prompt) → agregar tokens
7. Retornar JSON con:
   query_transcribed, language_detected, cdn_results,
   ai_overview { text, level, grounding }, suggestions
```

Retorna **JSON** (no SSE) porque el cliente espera la transcripción primero y luego puede lanzar una búsqueda SSE nueva. El frontend (`useVoiceRecorder.ts`) recibe `query_transcribed` y actualiza el `SearchBar`.

---

### `ai_engine/routers/health.py` — Endpoint de salud

**Función `health()`**:
```python
GET /api/health
     │
     ▼
Consulta el estado de TODOS los componentes:
- llm_engine.is_ready     → True si los engines TRT-LLM cargaron
- retriever.is_ready      → True si ChromaDB y embedder cargaron  
- stt.is_ready            → True si Whisper cargó
- thermal_manager.current_profile → "nominal" / "warm" / "critical"
- retriever.chunk_count() → cuántos fragmentos hay indexados en ChromaDB
     │
     ▼
Retorna JSON con estado de cada componente + config activa
```

Se usa para: verificar que el arranque fue exitoso, monitoreo en producción, y diagnóstico cuando algo no funciona.

---

### `ai_engine/services/thermal_manager.py` — Gestión térmica (Jetson)

**¿Qué hace?**  
Monitorea la temperatura de la Jetson cada N segundos y **ajusta dinámicamente** el nivel de rendimiento para evitar el apagado por temperatura.

**Cómo funciona `_monitor_loop()`**:
```python
while True:
    temp = self._read_temp_celsius()  
    # Lee todos los /sys/class/thermal/thermal_zone*/temp
    # Toma el máximo
    
    for profile in self._profiles:  # nominal → warm → critical
        if temp < profile["max_temp"]:
            # Estamos en este perfil térmico
            self.current_gamma = profile["draft_gamma"]
            # gamma más bajo = speculative decoding más conservador = menos tokens por paso
            # Esto reduce la carga de GPU y baja la temperatura
            break
    
    await asyncio.sleep(5)  # checar cada 5 segundos
```

**Tabla de perfiles para Orin NX 16GB**:
- `nominal` (< 55°C): NVPModel 4, gamma 5 → máximo rendimiento
- `warm` (< 68°C): NVPModel 3, gamma 4 → rendimiento ligeramente reducido
- `hot` (< 78°C): NVPModel 2, gamma 3 → rendimiento moderado
- `critical` (> 78°C): NVPModel 1, gamma 2 → mínimo rendimiento para enfriar

**¿Qué es `gamma` en speculative decoding?**  
El draft model propone `gamma` tokens de una vez, el target model los valida o rechaza. Mayor gamma = más rápido pero más riesgo de rechazo. Cuando hace calor, bajar gamma = menos trabajo para el target model = menos calor.

---

### `ai_engine/services/hybrid_retriever.py` — Retrieval (esqueleto)

**¿Qué debería hacer cuando esté implementado?**

```
query_text: "¿Qué es el protocolo TCP?"
     │
     ▼
1. HyDE (Hypothetical Document Embeddings):
   Generar una respuesta hipotética con el LLM draft
   → "TCP es un protocolo de transporte que garantiza entrega ordenada..."
   ← Esto mejora la búsqueda semántica porque buscamos por el tipo de
     documento que queremos, no por la pregunta
     │
     ▼
2. Embedding de la query (y del HyDE):
   intfloat/multilingual-e5-small → vector de 384 dimensiones
     │
     ▼
3. Búsqueda vectorial en ChromaDB:
   TOP_K=20 chunks más similares por coseno
     │
     ▼
4. Búsqueda léxica con BM25:
   Índice en memoria sobre todos los chunks del CDN
   → TOP_K resultados por relevancia lexical
     │
     ▼
5. RRF (Reciprocal Rank Fusion):
   Combina rankings de ChromaDB y BM25:
   score = Σ 1/(k + rank_i)
   ← Mejor que promediar scores porque los rankings son comparables
     │
     ▼
6. Cross-Encoder reranking (cross-encoder/ms-marco-MiniLM-L-6-v2):
   Para cada par (query, chunk) calcular score de relevancia preciso
   → TOP_K_FINAL=5 chunks finales
     │
     ▼
7. Retornar lista de chunks con { text, title, content_id, score }
```

**Todos los métodos implementados** ✓

| Método | Estado | Para qué |
|--------|--------|----------|
| `init()` | ✓ | Carga ChromaDB, multilingual-e5, cross-encoder; reconstruye BM25 desde ChromaDB |
| `search(query, top_k)` | ✓ | Pipeline completo: embed → ChromaDB → BM25 → RRF → Cross-Encoder |
| `add_chunks(ids, texts, metadatas)` | ✓ | Embed con prefijo `passage:` + upsert en ChromaDB |
| `delete_by_content_id(content_id)` | ✓ | Borra todos los chunks de un contenido antes de reindexar |
| `update_bm25(new_texts)` | ✓ | Extiende el corpus y reconstruye BM25Okapi en memoria |

**Prefijos multilingual-e5**: Las consultas usan `"query: {texto}"` y los documentos usan `"passage: {texto}"` — esto es obligatorio para que el modelo de embeddings funcione correctamente (entrenado con estos prefijos).

**RRF k=60**: La constante k=60 es el estándar en la literatura. Evita que un resultado en posición 1 domine demasiado sobre los demás — hace el fusion más robusto.

---

### `ai_engine/services/llm_engine.py` — Motor LLM (esqueleto)

**¿Qué debería hacer cuando esté implementado?**

**`init()`**: Carga dos modelos TensorRT-LLM:
- **Draft model**: LLaMA 3.2 1B INT4 — modelo pequeño y rápido
- **Target model**: Phi-3.5 Mini INT4 (Orin Nano) o LLaMA 3.1 8B INT4 (Orin NX 16GB)

**`generate_stream(prompt, gamma)`** ✓ — Speculative decoding implementado:
```
1. Draft model genera `gamma` tokens rápidamente (LLaMA 3.2 1B INT4)
2. Target model verifica los `gamma` tokens en paralelo (LLaMA 3.1 8B INT4)
3. Si acepta todos → avanzar gamma tokens (eficiencia máxima)
4. Si rechaza alguno → descartar a partir del rechazo, continuar
5. Yield cada token verificado → frontend recibe texto en tiempo real
```

**Modos de fallback** (cuando TRT-LLM no está disponible):

| Modo | Cuándo | Comportamiento |
|------|--------|-----------------|
| `trtllm` | Jetson con TRT-LLM instalado | Speculative decoding real |
| `hf` | PC con `transformers` y modelo local | AutoModelForCausalLM con TextIteratorStreamer |
| `none` | PC sin modelos | Mensaje informativo de placeholder |

**¿Por qué speculative decoding?**  
El cuello de botella es la latencia de memoria del target model (grande). Con el draft model (pequeño/rápido) proponemos varios tokens a la vez, y el target verifica todos en paralelo. Resultado: 2.5-3× más rápido sin pérdida de calidad.

---

### `ai_engine/services/stt.py` — Speech-to-Text (esqueleto)

**¿Qué debería hacer cuando esté implementado?**

**`transcribe(audio_path)`**: Usa `faster_whisper` (implementación CTranslate2 más eficiente que el Whisper original de OpenAI):
```python
result = _model.transcribe(
    audio_path,
    language=None,          # auto-detectar: detecta español y puede detectar quechua
    task="transcribe",
)
return {"text": result.text.strip(), "language": result.language}
```

Se usa el modelo "tiny" (39M params) para consultas en tiempo real (objetivo < 1s) y "small" (244M params) para transcripción de videos en ingesta batch.

**`transcribe_for_ingest(audio_path)`** ✓ — versión para ingesta batch:
- Usa Whisper **Small** (más preciso, `beam_size=5`)
- Retorna lista de `{"text": str, "start": float, "end": float}` (segmentos con timestamps)
- Timestamps permiten hacer deep links `video.mp4?t=183` en los resultados de búsqueda

**¿Por qué two-model strategy?**  
Tiny prioriza velocidad (el usuario espera su respuesta). Small prioriza precisión (la transcripción de videos se hace offline en segundo plano).

---

### `ai_engine/calibration/seeds.jsonl` — Dataset de calibración AWQ

**¿Para qué sirve?**  
La cuantización AWQ (Activation-Aware Weight Quantization) necesita un dataset representativo del dominio de uso para calibrar las activaciones antes de cuantizar. Si usas datos de calibración genéricos, el modelo quantizado perderá precisión en vocabulario educativo peruano.

Este archivo tiene 20 muestras de preguntas-respuestas educativas en español del contexto peruano. Antes de compilar el modelo TRT-LLM en la Jetson, se expande a 512 muestras (ver `docs/guia-laptop.md §9`).

---

## 5. Carpeta `search_ui/` — Frontend Buscador IA (React)

### ¿Qué hace en una frase?
Es la **interfaz web del buscador con IA**. Similar a Google pero mostrando contenido del CDN local con un resumen generado por el LLM.

---

### `search_ui/src/pages/SearchPage.tsx` — Página principal

**¿Qué hace?**  
Es el único "page" del buscador. Orquesta todos los componentes y maneja la lógica de mostrar el estado inicial vs. el estado con resultados.

**Estado inicial** (sin resultados):
```
─────────────────────────────────
        ¿Qué quieres aprender?
   [SearchBar centrado en pantalla]
   Escribe tu pregunta o usa el micrófono
─────────────────────────────────
```

**Con resultados** (tras buscar):
```
─────────────────────────────────
 GTR-PUCP [SearchBar en header]  [Cancelar]
─────────────────────────────────
 Resultados para: "redes LAN"
 ┌─────────────────────────────┐
 │ Resumen generado por IA...  │ ← AIOverview (streaming)
 └─────────────────────────────┘
 [Card video] [Card PDF] [Card...] ← SearchResults
─────────────────────────────────
```

**¿Por qué este diseño de dos estados?**  
Imita la UX de Google: la primera vez, la barra de búsqueda está centrada (toda la pantalla es para escribir). Tras buscar, la barra se "sube" al header (estilo Google después de hacer una búsqueda).

---

### `search_ui/src/hooks/useSSESearch.ts` — Hook de búsqueda por SSE

**¿Qué hace?**  
Es el "cerebro" de la comunicación con el AI Engine. Gestiona el stream SSE (Server-Sent Events) del endpoint `/api/ai/search/stream`.

**Función `search(query)`**:
```typescript
1. Cancelar búsqueda previa si hay una en curso
   abortRef.current?.abort()   ← AbortController cancela el fetch

2. Reset de estado: cards=[], overview='', isStreaming=true

3. fetch('/api/ai/search/stream', { method: 'POST', body: {query} })
   ← El proxy de Vite redirige esto a http://localhost:8000/api/search/stream

4. res.body.getReader()   ← Leer el stream byte a byte

5. Por cada chunk del stream:
   buffer += decode(chunk)
   lines = buffer.split('\n')   ← SSE usa \n como separador
   
   Por cada línea que empieza con "data: ":
   msg = JSON.parse(línea)
   
   switch(msg.type):
     'cdn_results' → setState({ cards: msg.data })
     'token'       → setState({ overview: prev + msg.text })  ← concatenar token
     'done'        → setState({ isStreaming: false, suggestions: msg.suggestions })
```

**¿Por qué SSE y no WebSocket?**  
SSE es unidireccional (servidor → cliente), que es exactamente lo que necesitamos. Es más simple que WebSocket, funciona sobre HTTP estándar, y los proxies/firewalls lo manejan mejor.

---

### `search_ui/src/hooks/useVoiceRecorder.ts` — Hook de grabación de voz

**¿Qué hace?**  
Gestiona el ciclo completo de grabación de audio: pedir permiso al micrófono → grabar → enviar al AI Engine para transcripción.

**Flujo**:
```typescript
start():
  1. navigator.mediaDevices.getUserMedia({ audio: true })
     ← Pide permiso al navegador para usar el micrófono; abre el diálogo

  2. new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
     ← webm/opus: buena calidad, buen tamaño, soportado por Whisper

  3. recorder.start()   → estado: 'recording'

stop():
  1. recorder.stop()    → state: 'processing'
  
  2. Blob(chunks, { type: 'audio/webm' })   ← unir todos los chunks grabados
  
  3. FormData con el blob como campo 'audio'
  
  4. POST /api/ai/voice-search   ← enviar al AI Engine
     ← El AI Engine transcribe con Whisper y retorna { query_transcribed: "..." }
  
  5. onResult(query_transcribed)   ← callback que actualiza SearchBar y lanza búsqueda
```

---

### `search_ui/src/components/search/SearchBar.tsx`

**¿Qué hace?**  
Barra de búsqueda con textarea (para queries multilínea), botón de voz y botón de enviar.

- `handleSubmit(e)` → previene recarga de página, llama `onSearch(query)`
- `handleKeyDown(e)` → Enter sin Shift envía el formulario; Enter+Shift crea nueva línea
- `handleVoiceResult(transcribed)` → actualiza el estado del textarea y lanza la búsqueda

---

### `search_ui/src/components/search/AIOverview.tsx`

**¿Qué hace?**  
Caja principal que muestra el resumen generado por la IA con streaming en tiempo real y renderizado enriquecido.

**Características actuales**:
- Renderiza Markdown completo vía `react-markdown` con plugins: tablas GFM (`remark-gfm`), ecuaciones LaTeX (`remark-math` + `rehype-katex`)
- Bloques de código con syntax highlighting tema `nightOwl` (morado/naranja/verde/blanco) sobre fondo azul noche `rgba(11,16,40,0.93)` con borde azul tenue
- Tema limpiado en JS para eliminar los `borderBottom` inline que Prism inyecta en cada token span
- Botón de copiar código por bloque con feedback visual (icono verde al copiar)
- Inline code con pill azul traslúccido
- Indicador pulsante animado mientras el modelo genera tokens
- Expand/colapsar respuesta con botón y degradado de fade
- Si `text` está vacío Y `isStreaming=false` → no renderiza nada

**`CodeRenderer` — cómo funciona**:
```tsx
function CodeRenderer({ inline, className, children }) {
  const lang = /language-(\w+)/.exec(className)?.[1] ?? 'text'
  if (inline) return <code className="pill-azul">{children}</code>
  return (
    <div className="code-block-wrap">   // clase para CSS overrides
      <header style={{ background: 'rgba(7,10,26,0.98)' }}>
        <span>{lang}</span>  <CopyButton />
      </header>
      <SyntaxHighlighter
        style={cleanNightOwl}           // nightOwl sin borders inline
        showLineNumbers={false}         // sin números de línea
        customStyle={{ background: 'rgba(11,16,40,0.93)' }}
      />
    </div>
  )
}
```

---

## 6. Carpeta `client/` — Frontend Plataforma Educativa (React)

**¿Qué hace?**  
Es la **interfaz principal del catálogo educativo**: permite navegar el contenido disponible, reproducir videos (con el player), visualizar PDFs, y (para profesores/admins) subir nuevo contenido.

Estructura creada como scaffold de Vite + React + TypeScript + Tailwind. Los detalles de implementación de cada componente están pendientes de completar (ver `docs/guia-laptop.md §7`).

Corre en el puerto **5173** (puerto default de Vite).

---

## 7. Carpeta `storage/` — Almacenamiento de archivos

**¿Qué hace?**  
Es el **filesystem del CDN**. Todos los archivos subidos se almacenan aquí. La base de datos solo guarda metadatos; los bytes reales están en esta carpeta.

```
storage/
├── videos/
│   └── a3f9b2c1d4e5f6...7890.mp4   ← nombre = SHA-256 del archivo
│
├── documents/
│   └── b7c8d9e0f1a2b3...4567.pdf
│
├── images/                          ← imágenes educativas (JPG, PNG, GIF, WebP)
│   └── c5d6e7f8a9b0c1...2345.jpg
│
├── audio/                           ← archivos de audio (MP3, WAV, OGG, M4A)
│   └── d9e0f1a2b3c4d5...6789.mp3
│
├── thumbnails/
│   └── content-uuid-aqui.jpg       ← nombre = UUID del registro en DB
│
└── temp/
    └── upload-xxxxxx.tmp           ← archivos en proceso de upload
                                       (se limpian automáticamente)
```

> **Sobre `audio/` e `images/`**: ya están contempladas en el código. `upload.ts` acepta sus MIME types. `storageService.ts` tiene `'images' | 'audio'` en su firma. Las carpetas se crean automáticamente con `fs.mkdir(..., { recursive: true })` en el primer upload de ese tipo — no hay que crearlas manualmente.

**¿Por qué nombre = hash del archivo?**
- Autodetección de duplicados: si dos profesores suben el mismo video, el hash es idéntico y el sistema lo detecta
- Inmutabilidad: el nombre no puede cambiar si el contenido no cambia
- Sin colisiones: la probabilidad de dos archivos distintos con el mismo SHA-256 es astronómicamente baja

**¿Por qué thumbnails usan UUID en lugar de hash?**  
El thumbnail es **generado** (no subido), así que no existe antes del procesamiento. El UUID del registro en DB es lo más conveniente para relacionarlo.

---

## 8. Carpeta `scripts/` — SQL de inicialización

**`init_database_v2.sql`**: Schema completo de PostgreSQL. Define todas las tablas del sistema:
- `users` — usuarios con roles (viewer, teacher, superadmin), login_attempts, lock
- `sessions` — sesiones JWT activas (para invalidación)
- `categories` — categorías de contenido
- `content` — metadatos de cada archivo (title, type, file_path, file_hash, duration, etc.)
- `access_log` — cada vez que alguien reproduce un video se registra (para analytics)
- `ai_ingestion_queue` — cola de proceso para el AI Engine (pendiente)
- Índices de búsqueda de texto completo (`to_tsvector`)
- Funciones de auto-actualización de timestamps (`updated_at`)

**`init_ai_engine.sql`**: Tablas adicionales específicas para el AI Engine.

**`init_database.sql`**: Versión anterior del schema (para referencia).

---

## 9. Carpeta `docs/` — Documentación técnica

| Archivo | Contenido |
|---------|-----------|
| `ai-search-engine-plan.md` | Plan completo de 20 secciones para implementar el AI Engine. La referencia principal para implementar los esqueletos. 1349 líneas. |
| `architecture.md` | Diseño de alto nivel, diagrama de componentes, decisiones técnicas |
| `guia-inicio.md` | Paso a paso para configurar y desplegar en la Jetson Orin |
| `guia-laptop.md` | Paso a paso para desarrollar en laptop/PC (tiene la guía de entorno Python completa) |
| `database-design.md` | Schema SQL explicado en detalle |
| `jetson-comparison.md` | Comparativa de las 4 plataformas Jetson y cuándo usar cada una |
| `roadmap.md` | Timeline del proyecto, hitos, métricas |
| `testing-strategy.md` | Estrategia de tests unitarios, integración y E2E |

---

## 10. Flujos completos de principio a fin

### Flujo A: Un estudiante busca "protocolo TCP"

```
[Navegador :5174]
     │  El usuario escribe "protocolo TCP" y presiona Enter
     ▼
[useSSESearch.search("protocolo TCP")]
     │  fetch POST /api/ai/search/stream
     │  (proxy Vite → localhost:8000)
     ▼
[AI Engine :8000 — mock_main.py o main.py]
     │
     │  [Si es el REAL, no el mock:]
     │  1. hybrid_retriever.search("protocolo TCP")
     │     a. HyDE: llm_engine genera texto hipotético sobre TCP
     │     b. embedder.encode([query, hyde_text]) → vectores
     │     c. ChromaDB.query(vector, top_k=20)  → chunks semánticos
     │     d. BM25.search("protocolo TCP") → chunks léxicos
     │     e. RRF fusion → ranking combinado
     │     f. cross_encoder.predict([(query, chunk)...]) → top 5
     │
     │  2. Construir prompt con los 5 chunks como fuentes
     │     [FUENTE 1] Título: Manual CISCO... Fragmento: TCP garantiza...
     │
     │  3. llm_engine.generate_stream(prompt)
     │
     ▼
SSE stream → [useSSESearch]
     │
     │  data: {"type":"cdn_results","data":[{title:"Redes Módulo 5",...},...]}
     │     → setState({ cards: [...] })
     │     → SearchResults renderiza las tarjetas inmediatamente
     │
     │  data: {"type":"token","text":"TCP "}
     │  data: {"type":"token","text":"es "}
     │  data: {"type":"token","text":"un "}
     │     ...
     │     → setState({ overview: overview + token })
     │     → AIOverview re-renderiza con cada token nuevo
     │
     │  data: {"type":"done","suggestions":["¿Qué es UDP?","Diferencia TCP/IP"]}
     │     → setState({ isStreaming: false, suggestions: [...] })
     ▼
[Navegador :5174]
     El usuario ve el resumen completo + tarjetas con links a los videos
```

---

### Flujo B: Un profesor sube un video

```
[Navegador :5173 - client]
     │  El profesor selecciona un .mp4 y rellena título/categoría
     ▼
POST /api/upload (multipart/form-data con el archivo)
     │  Header: Authorization: Bearer TOKEN
     ▼
[middleware authenticate]
     │  Verifica JWT + sesión activa en DB
     ▼
[uploadController.uploadContent()]
     │
     ▼  1. storageService.moveToStorage(tempPath, 'videos', '.mp4')
     │     → SHA-256 del archivo (streaming)
     │     → mv /storage/temp/upload-xxx.mp4 → /storage/videos/a3f9b2...mp4
     │
     ▼  2. SELECT id FROM content WHERE file_hash = 'a3f9b2...'
     │     → no duplicado, continuar
     │
     ▼  3. ffmpegService.getVideoMetadata('/storage/videos/a3f9b2...mp4')
     │     → duración: 1243s, resolución: 1920×1080, bitrate: 2500kbps
     │
     ▼  4. ffmpegService.generateThumbnail(filePath, outputPath, 10)
     │     → extrae frame del segundo 10
     │     → guarda /storage/thumbnails/UUID.jpg
     │
     ▼  5. INSERT INTO content (title, type='video', file_path, file_hash,
     │                          duration_seconds, thumbnail_path, ...)
     │     → retorna el UUID generado
     │
     │  6. POST http://localhost:8000/api/ingest { content_id: UUID }  ✓
     │     Fire-and-forget: no bloquea la respuesta al cliente
     │     AI_ENGINE_URL desde .env (default: http://localhost:8000)
     │     → AI Engine procesa el video en background:
     │       transcribe audio con Whisper small → chunks de texto
     │       genera embeddings → indexa en ChromaDB
     │
     ▼
Respuesta 201: { content_id: "uuid...", message: "Content uploaded successfully" }
```

---

### Flujo C: Un estudiante busca por voz ("¿qué es una red LAN?")

```
[Navegador :5174 - search_ui]
     │  El usuario presiona el botón de micrófono
     ▼
[useVoiceRecorder.start()]
     │  navigator.mediaDevices.getUserMedia({ audio: true })
     │  Grabación empieza...
     ▼
[El usuario habla: "¿qué es una red LAN?"]
     │  El usuario suelta el botón
     ▼
[useVoiceRecorder.stop()]
     │  Blob(chunks, { type: 'audio/webm' })
     │  POST /api/ai/voice-search (FormData con el blob de audio)
     ▼
[AI Engine — voice_search.py]
     │  [Cuando esté implementado:]
     │  1. Guardar audio en /tmp/query_xxxx.webm
     │  2. stt.transcribe('/tmp/query_xxxx.webm')
     │     → Whisper Tiny en CPU: "¿qué es una red LAN?"
     │     → language detected: "es"
     │  3. Ejecutar el mismo pipeline que /api/search con "¿qué es una red LAN?"
     │  4. Retornar JSON normal (no SSE) con query_transcribed + cdn_results + ai_overview
     ▼
[useVoiceRecorder.onstop]
     │  data.query_transcribed = "¿qué es una red LAN?"
     │  onResult("¿qué es una red LAN?")  ← callback al SearchBar
     ▼
[SearchBar]
     │  setQuery("¿qué es una red LAN?")
     │  onSearch("¿qué es una red LAN?")  ← lanza búsqueda SSE normal
     ▼
→ Continúa como el Flujo A desde aquí
```

---

### Flujo D: El frontend consulta el catálogo de contenido

```
[Navegador :5173 - client]
     │  Usuario abre la plataforma
     ▼
GET /api/content?page=1&limit=20&sort=recent
     ▼
[contentController.getContent()]
     │
     ▼  cacheGet("content:list:{page:1,limit:20,sort:recent}")
     │     → cache miss (primera vez)
     │
     ▼  Construir WHERE: "deleted_at IS NULL AND status = 'active'"
     │
     ▼  SELECT c.id, c.title, c.type, c.thumbnail_path, cat.name...
        FROM content c LEFT JOIN categories cat ON c.category_id = cat.id
        WHERE deleted_at IS NULL AND status = 'active'
        ORDER BY c.created_at DESC
        LIMIT 20 OFFSET 0
     │
     ▼  cacheSet("content:list:...", result, 300)
     │     → guardar 5 minutos en Redis para las próximas peticiones
     │
     ▼  Responder { data: [...20 items...], pagination: { total, page } }
     │
     ▼  [Segunda petición del mismo usuario en los próximos 5 minutos:]
     ▼  cacheGet() → HIT → respuesta instantánea sin tocar PostgreSQL
```

---

---

## 11. Estado actual del sistema

### ✅ Completamente implementado

| Componente | Archivo |
|------------|---------|
| CDN backend completo | `server/src/` |
| STT Whisper Tiny + Small | `ai_engine/services/stt.py` |
| Chunking jerárquico (3 niveles + timestamps) | `ai_engine/services/ingestion/chunker.py` |
| Extracción PDF/DOCX/OCR | `ai_engine/services/ingestion/pdf_extractor.py` |
| Generación de miniaturas | `ai_engine/services/ingestion/thumbnail_generator.py` |
| Pipeline de ingesta completo | `ai_engine/services/ingestion/pipeline.py` |
| Router de ingesta (queue + status) | `ai_engine/routers/ingest.py` |
| Retrieval híbrido completo (BM25+ChromaDB+RRF+CE) | `ai_engine/services/hybrid_retriever.py` |
| LLM Engine (TRT-LLM + HF fallback + placeholder) | `ai_engine/services/llm_engine.py` |
| Búsqueda SSE con triáje L1-L4 | `ai_engine/routers/search.py` |
| Voice search (STT + pipeline) | `ai_engine/routers/voice_search.py` |
| Llamada a ingest tras upload | `server/src/controllers/uploadController.ts` |
| Configuración multi-plataforma | `ai_engine/config/settings.py` |
| System prompts y triáje | `ai_engine/config/prompts.py` |
| Servidor mock para desarrollo | `ai_engine/mock_main.py` |
| Frontend buscador (SSE, voz, tarjetas) | `search_ui/src/` |

### ⚠️ Requiere hardware (no implementable en PC)

| Pendiente | Condición |
|-----------|----------|
| TRT-LLM real funcionando | Jetson Orin + JetPack 6 + modelos INT4 compilados |
| Embeddings en CUDA (`EMBEDDING_DEVICE=cuda`) | GPU NVIDIA disponible |
| Gestor térmico real | `/sys/class/thermal/` solo existe en Jetson |

### 🟡 Pendiente de implementar (software)

| Pendiente | Archivo | Impacto |
|-----------|---------|--------|
| Frontend `client/` (catálogo, visor, upload) | `client/src/` | Sin interfaz para profesores/estudiantes |
| Tests unitarios e integración | `ai_engine/tests/` | Necesarios antes de despliegue |
| Variable `AI_ENGINE_URL` en `.env` del server | `server/.env` | Necesaria si AI Engine corre en otra IP |

*Documento generado para el proyecto GTR-PUCP — CDN Educativa Offline, Marzo 2026.*
