# Guía Completa — Pruebas en PC de Escritorio

> **Proyecto**: GTR-PUCP — CDN Educativa Offline  
> **Fecha**: Marzo 2026  
> **Para quién**: Cualquier miembro del equipo que necesite levantar y probar el sistema completo **en una PC de escritorio**, sin necesitar la Jetson ni hardware especializado.

La guía existente [`docs/guia-inicio.md`](docs/guia-inicio.md) cubre el despliegue en la **Jetson Orin** (flash, TensorRT-LLM, producción real). Esta guía cubre todo lo necesario para **transportar el proyecto a cualquier PC x86-64** y ejecutar un entorno funcional completo para demostración, desarrollo y pruebas — usando el **mock del AI Engine** en lugar del LLM real.

> **¿Qué vas a tener al final?**  
> - CDN backend (Node.js + PostgreSQL + Redis) corriendo en tu PC  
> - AI Engine en modo mock (responde sin GPU, sin LLM real)  
> - Frontend de búsqueda IA (`search_ui`) en tu navegador  
> - Frontend de la plataforma educativa (`client`) en tu navegador  
> - Pruebas end-to-end completas: subir contenido, buscarlo, ver resultados de IA

---

## Índice

1. [¿Qué NO va a funcionar en la PC?](#1-qué-no-va-a-funcionar-en-la-pc)
2. [Transportar el proyecto a la PC](#2-transportar-el-proyecto-a-la-pc)
3. [Requisitos del sistema](#3-requisitos-del-sistema)
4. [Instalar dependencias del sistema](#4-instalar-dependencias-del-sistema)
5. [Clonar / copiar el repositorio](#5-clonar--copiar-el-repositorio)
6. [Configurar PostgreSQL](#6-configurar-postgresql)
7. [Configurar Redis](#7-configurar-redis)
8. [Configurar el servidor CDN (Node.js)](#8-configurar-el-servidor-cdn-nodejs)
9. [Configurar el AI Engine mock (Python)](#9-configurar-el-ai-engine-mock-python)
10. [Configurar los frontends (React)](#10-configurar-los-frontends-react)
11. [Iniciar todos los servicios](#11-iniciar-todos-los-servicios)
12. [Pruebas paso a paso](#12-pruebas-paso-a-paso)
13. [Subir contenido de prueba](#13-subir-contenido-de-prueba)
14. [Probar el buscador IA](#14-probar-el-buscador-ia)
15. [Solución de problemas comunes](#15-solución-de-problemas-comunes)
16. [Resumen rápido de puertos y URLs](#16-resumen-rápido-de-puertos-y-urls)

---

## 1. ¿Qué NO va a funcionar en la PC?

Antes de empezar, ten claro esto:

| Función | En PC de escritorio (x86-64) | En Jetson Orin (ARM64) |
|---------|------------------------------|------------------------|
| CDN backend (Node.js) | ✅ Funciona completo | ✅ Funciona completo |
| Streaming de video/PDF | ✅ Funciona completo | ✅ Funciona completo |
| Upload de contenido | ✅ Funciona completo | ✅ Funciona completo |
| Auth JWT | ✅ Funciona completo | ✅ Funciona completo |
| Frontend search_ui | ✅ Funciona completo | ✅ Funciona completo |
| Frontend client | ✅ Funciona completo | ✅ Funciona completo |
| AI Engine **mock** | ✅ Funciona (respuestas falsas) | ✅ Se puede usar |
| Embeddings reales (sentence-transformers) | ✅ CPU (lento pero funciona) | ✅ GPU CUDA |
| Whisper STT real | ✅ CPU (más lento) | ✅ GPU CUDA |
| ChromaDB retrieval real | ✅ Funciona en CPU | ✅ Funciona en GPU |
| **LLM real (TensorRT-LLM)** | ❌ Solo ARM64 + CUDA Jetson | ✅ Único entorno válido |
| Gestión térmica (NVPModel) | ❌ No aplica | ✅ Obligatorio en Jetson |

**Conclusión**: Todo el sistema es testeable en PC excepto la inferencia LLM real. El mock replica exactamente el formato de la API para que el frontend funcione al 100%.

---

## 2. Transportar el proyecto a la PC

Tienes tres opciones según tu situación:

### Opción A: Clonar desde Git (recomendado si tienes repositorio remoto)

```bash
# En la PC de destino
git clone https://github.com/TU_ORG/CDN.git
cd CDN
```

### Opción B: Copiar con rsync por red local (si ambas máquinas están en la misma red)

```bash
# Desde la máquina de origen (donde ya tienes el proyecto)
# Sustituye USUARIO e IP_PC_DESTINO por los valores reales
rsync -avz --exclude='node_modules' --exclude='.git' --exclude='ai_env' \
  --exclude='storage/videos' --exclude='storage/documents' \
  /home/jleon/2026/PUCP/GTR/CDN/ \
  USUARIO@IP_PC_DESTINO:/home/USUARIO/CDN/
```

> **¿Por qué excluir esas carpetas?**  
> - `node_modules` y `ai_env`: se reinstalan en destino (binary-incompatible entre distros)  
> - `storage/videos` y `storage/documents`: son archivos grandes de contenido; cópialos por separado si los necesitas

### Opción C: USB / disco externo

```bash
# En la máquina origen — crear un tarball excluyendo carpetas pesadas
tar --exclude='node_modules' --exclude='.git' --exclude='ai_env' \
    --exclude='storage/videos/*.mp4' \
    -czf CDN_proyecto.tar.gz \
    -C /home/jleon/2026/PUCP/GTR CDN

# Mover el .tar.gz al USB, luego en la PC destino:
cd /home/USUARIO
tar -xzf /media/USB/CDN_proyecto.tar.gz
```

---

## 3. Requisitos del sistema

### Sistema operativo recomendado
- **Ubuntu 22.04 LTS** o **24.04 LTS** (64-bit)
- Alternativa válida: cualquier Debian/Ubuntu derivado

### Hardware mínimo para pruebas

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 4 GB | 8 GB+ |
| CPU | 2 cores | 4 cores+ |
| Disco libre | 10 GB | 30 GB+ |
| GPU | No requerida | No requerida |

### Software necesario (se instala en §4)

- Node.js >= 18.0
- Python 3.12 (Python 3.13 no es compatible con algunos paquetes)
- PostgreSQL 14+
- Redis 7+
- FFmpeg
- Git, curl, wget

---

## 4. Instalar dependencias del sistema

Ejecuta estos comandos en **orden** en la PC de escritorio:

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar PostgreSQL 16
sudo apt install -y postgresql postgresql-contrib

# Verificar que está corriendo
sudo systemctl status postgresql
# Debe mostrar: active (running)

# Instalar Redis 7
sudo apt install -y redis-server

# Verificar Redis
redis-cli ping
# Debe responder: PONG

# Instalar Node.js 18 LTS (vía NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

node --version   # Debe mostrar v18.x.x
npm --version    # Debe mostrar 9.x.x o superior

# Instalar FFmpeg (necesario para procesar videos en upload)
sudo apt install -y ffmpeg
ffmpeg -version  # Debe mostrar version 4.x o superior

# Instalar Python 3.12 con venv
sudo apt install -y python3.12 python3.12-venv python3.12-dev

python3.12 --version  # Debe mostrar Python 3.12.x

# Herramientas adicionales
sudo apt install -y git curl wget vim htop build-essential
```

---

## 5. Clonar / copiar el repositorio

Si usaste la Opción A del paso 2:

```bash
# El repositorio ya está en tu máquina; navega a él
cd /home/USUARIO/CDN
ls
# Debes ver: server/ ai_engine/ search_ui/ client/ storage/ docs/ ...
```

Si usaste Opción B o C ya tienes los archivos. Comprueba la estructura:

```bash
ls /home/USUARIO/CDN
# server/    ai_engine/   search_ui/   client/   storage/   docs/
# README.md  QUICKSTART.md   docker-compose.dev.yml   ...
```

> **Nota de ruta**: El resto de esta guía asume que el proyecto está en `/home/USUARIO/CDN`. Adapta las rutas según donde lo tengas.

---

## 6. Configurar PostgreSQL

### 6.1 Crear usuario y base de datos

```bash
# Acceder como usuario postgres
sudo -u postgres psql
```

Dentro de `psql`:

```sql
-- Crear usuario
CREATE USER cdn_user WITH PASSWORD 'cdn_pass_dev';

-- Crear base de datos
CREATE DATABASE cdn_dev OWNER cdn_user;

-- Conectar a la nueva base de datos y habilitar extensiones
\c cdn_dev

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Verificar
\dx
-- Debe mostrar las tres extensiones instaladas

\q
```

### 6.2 Cargar el schema de la base de datos

```bash
cd /home/USUARIO/CDN

# Usar el schema más completo (v2, incluye tabla de ingesta AI)
psql -U cdn_user -h localhost -d cdn_dev -f scripts/init_database_v2.sql

# Si pide contraseña: cdn_pass_dev
```

### 6.3 Crear un usuario administrador para pruebas

```bash
# Generar hash bcrypt para la contraseña "admin123"
cd /home/USUARIO/CDN/server
node generate-hash.js admin123
# Copia el hash que genera (empieza con $2b$...)
```

```bash
# Insertar el usuario admin en la base de datos
psql -U cdn_user -h localhost -d cdn_dev
```

```sql
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES (
  'admin',
  'admin@gtr-pucp.edu.pe',
  '$2b$10$EL_HASH_QUE_COPIASTE_AQUI',
  'superadmin',
  true
);

\q
```

### 6.4 Verificar la conexión

```bash
psql -U cdn_user -h localhost -d cdn_dev -c "SELECT COUNT(*) FROM users;"
# Debe mostrar: count = 1
```

---

## 7. Configurar Redis

Redis ya está instalado. Verifica que esté corriendo y configurado:

```bash
# Verificar estado
sudo systemctl status redis-server
# Debe mostrar: active (running)

# Test rápido
redis-cli ping
# Respuesta: PONG

# Si no está corriendo, iniciarlo
sudo systemctl start redis-server
sudo systemctl enable redis-server   # para que inicie con el sistema
```

---

## 8. Configurar el servidor CDN (Node.js)

### 8.1 Instalar dependencias

```bash
cd /home/USUARIO/CDN/server
npm install
```

### 8.2 Crear el archivo `.env`

```bash
cp .env.example .env
```

Edita el `.env` con tu editor favorito:

```bash
nano .env     # o code .env si tienes VS Code
```

Contenido del `.env` para PC de escritorio:

```dotenv
# Entorno
NODE_ENV=development
PORT=3000

# Base de datos
DATABASE_URL=postgresql://cdn_user:cdn_pass_dev@localhost:5432/cdn_dev

# Redis
REDIS_URL=redis://localhost:6379

# JWT (cambia este secret en cualquier despliegue real)
JWT_SECRET=mi_secret_de_desarrollo_gtr_pucp_2026
JWT_EXPIRES_IN=7d

# Ruta al storage — AJUSTA esta ruta a tu máquina
STORAGE_PATH=/home/USUARIO/CDN/storage

# Tamaño máximo de archivo: 500 MB
MAX_FILE_SIZE=524288000

# FFmpeg (confirmar rutas con: which ffmpeg && which ffprobe)
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe

# URL del AI Engine (mock corre en :8000)
AI_ENGINE_URL=http://localhost:8000
```

> **Importante**: reemplaza `/home/USUARIO/CDN` con la ruta real donde está el proyecto.

### 8.3 Crear las carpetas de storage

```bash
mkdir -p /home/USUARIO/CDN/storage/{videos,documents,thumbnails,temp}
```

### 8.4 Verificar la compilación TypeScript

```bash
cd /home/USUARIO/CDN/server
npm run build
# No debe haber errores de TypeScript
```

Si hay errores reporta qué dice para depurarlos.

---

## 9. Configurar el AI Engine mock (Python)

Para pruebas en PC usamos el **mock** (`ai_engine/mock_main.py`). Este servidor responde exactamente con el mismo formato JSON/SSE que el AI Engine real, pero sin LLM, sin GPU, y sin ninguna dependencia pesada.

### 9.1 Crear el entorno virtual Python 3.12

```bash
cd /home/USUARIO/CDN

# Crear venv con Python 3.12 explícito
python3.12 -m venv ai_env

# Activar
source ai_env/bin/activate

# Verificar versión
python3 --version   # Debe mostrar Python 3.12.x
```

### 9.2 Instalar dependencias mínimas para el mock

El mock solo necesita FastAPI y uvicorn — sin torch, sin chromadb, sin whisper. Esto se instala en segundos:

```bash
# Asegúrate de que el venv está activo (ves "(ai_env)" al inicio del prompt)
pip install --upgrade pip

pip install fastapi==0.111.0 "uvicorn[standard]==0.29.0" pydantic==2.7.0

# Verificar
python3 -c "import fastapi, uvicorn; print('OK', fastapi.__version__)"
```

> **¿Quieres instalar el stack completo para pruebas más reales?**  
> Consulta la sección §2.3 de [`docs/guia-laptop.md`](docs/guia-laptop.md) para el proceso completo con sentence-transformers, chromadb y faster-whisper.

### 9.3 Crear el `.env` del AI Engine (opcional para el mock)

El mock no usa settings.py por defecto, pero si luego quieres usar el main real:

```bash
cat > /home/USUARIO/CDN/ai_engine/.env << 'EOF'
AI_PLATFORM=orin_nx_16gb
CHROMADB_PATH=/home/USUARIO/CDN/chromadb_data
STORAGE_PATH=/home/USUARIO/CDN/storage
CDN_BACKEND_URL=http://localhost:3000
AI_ENGINE_HOST=0.0.0.0
AI_ENGINE_PORT=8000
EOF
```

---

## 10. Configurar los frontends (React)

### 10.1 search_ui — Buscador IA (puerto 5174)

```bash
cd /home/USUARIO/CDN/search_ui
npm install
```

Verificar la configuración de Vite (debe proxiar `/api/ai` al AI Engine):

```bash
cat vite.config.ts
# Confirma que tiene proxy hacia localhost:8000 para /api/ai
# y hacia localhost:3000 para /api
```

### 10.2 client — Plataforma educativa (puerto 5173)

```bash
cd /home/USUARIO/CDN/client
npm install
```

---

## 11. Iniciar todos los servicios

Necesitas **4 terminales** abiertas al mismo tiempo (o usar `tmux`/`screen`).

### Terminal 1 — Servidor CDN (Node.js)

```bash
cd /home/USUARIO/CDN/server
npm run dev
```

Salida esperada:
```
🔍 Verificando conexiones...
✅ Conectado a PostgreSQL
✅ Conectado a Redis
🚀 CDN Server corriendo en http://localhost:3000
📁 Storage: /home/USUARIO/CDN/storage
```

### Terminal 2 — AI Engine mock (Python)

```bash
cd /home/USUARIO/CDN
source ai_env/bin/activate
python -m uvicorn ai_engine.mock_main:app --host 0.0.0.0 --port 8000 --reload
```

Salida esperada:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Terminal 3 — Frontend search_ui (buscador IA)

```bash
cd /home/USUARIO/CDN/search_ui
npm run dev
```

Salida esperada:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5174/
```

### Terminal 4 — Frontend client (plataforma educativa)

```bash
cd /home/USUARIO/CDN/client
npm run dev
```

Salida esperada:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

### Estado esperado de servicios

| Servicio | URL | Puerto |
|---------|-----|--------|
| CDN Backend API | http://localhost:3000 | 3000 |
| AI Engine mock | http://localhost:8000 | 8000 |
| Buscador IA (search_ui) | http://localhost:5174 | 5174 |
| Plataforma educativa (client) | http://localhost:5173 | 5173 |
| PostgreSQL | localhost | 5432 |
| Redis | localhost | 6379 |

---

## 12. Pruebas paso a paso

### 12.1 Test 1 — Health check del CDN backend

```bash
curl -s http://localhost:3000/health | python3 -m json.tool
```

Respuesta esperada:
```json
{
    "status": "healthy",
    "timestamp": "2026-03-02T...",
    "environment": "development",
    "services": {
        "database": "connected",
        "redis": "connected"
    }
}
```

Si `database` dice `disconnected`: verifica PostgreSQL (`sudo systemctl status postgresql`) y las credenciales en el `.env`.

### 12.2 Test 2 — Health check del AI Engine mock

```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
```

Respuesta esperada:
```json
{
    "status": "ok",
    "platform": "mock_laptop",
    "components": {
        "llm_engine": "mock",
        "retriever": "mock",
        "stt": "mock",
        "thermal": "nominal",
        "chroma_chunks": 42
    }
}
```

### 12.3 Test 3 — Login de administrador

```bash
curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | python3 -m json.tool
```

Respuesta esperada (guarda el token que te da):
```json
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
        "id": "...",
        "username": "admin",
        "role": "superadmin"
    }
}
```

```bash
# Guarda el token en una variable de shell para los siguientes tests
TOKEN="eyJhbGciOiJIUzI1NiIs..."
```

### 12.4 Test 4 — Listar categorías

```bash
curl -s http://localhost:3000/api/categories | python3 -m json.tool
```

Si la DB tiene datos de seed, verás categorías. Si está vacía, es normal — agrega una:

```bash
curl -s -X POST http://localhost:3000/api/categories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Matemáticas", "description": "Videos y PDFs de matemática escolar"}' \
  | python3 -m json.tool
```

Guarda el `id` de la categoría creada.

### 12.5 Test 5 — Listar contenido (debe estar vacío al inicio)

```bash
curl -s "http://localhost:3000/api/content?limit=5" | python3 -m json.tool
```

Respuesta esperada si aún no has subido contenido:
```json
{
    "success": true,
    "data": [],
    "pagination": {
        "total": 0,
        "page": 1,
        "limit": 5
    }
}
```

### 12.6 Test 6 — Búsqueda en el AI Engine mock (texto)

```bash
curl -s -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "redes de computadoras LAN"}' | python3 -m json.tool
```

Debes ver una respuesta con `cdn_results` (tarjetas mock) y `ai_overview` con texto explicativo.

### 12.7 Test 7 — Búsqueda streaming SSE

```bash
curl -s -X POST http://localhost:8000/api/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "protocolo TCP"}' \
  --no-buffer
```

Debes ver una secuencia de eventos SSE:
```
data: {"type": "cdn_results", "data": [...]}

data: {"type": "token", "text": "Una "}

data: {"type": "token", "text": "red "}
...
data: {"type": "done", "suggestions": [...]}
```

---

## 13. Subir contenido de prueba

Estas pruebas verifican el pipeline completo de upload, procesamiento con FFmpeg y almacenamiento.

### 13.1 Obtener el ID de una categoría

```bash
curl -s http://localhost:3000/api/categories | python3 -m json.tool
# Guarda algún "id" de categoría
CATEGORY_ID="el-uuid-de-la-categoria"
```

### 13.2 Subir un PDF de prueba

```bash
# Crear un PDF ficticio para la prueba (necesita ghostscript o cualquier PDF)
# Si no tienes un PDF, puedes descargar uno de internet o usar cualquier PDF del sistema

curl -s -X POST http://localhost:3000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/ruta/a/un/documento.pdf" \
  -F "title=Manual de Prueba" \
  -F "description=PDF de prueba para demostración" \
  -F "category_id=$CATEGORY_ID" \
  | python3 -m json.tool
```

Respuesta exitosa:
```json
{
    "success": true,
    "content_id": "uuid-del-contenido",
    "message": "Content uploaded successfully"
}
```

### 13.3 Subir un video de prueba

```bash
# Crear un video corto de prueba con FFmpeg (5 segundos de video en negro con tono)
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=25 \
       -f lavfi -i sine=frequency=440:duration=5 \
       -c:v libx264 -c:a aac /tmp/video_prueba.mp4

# Subirlo
curl -s -X POST http://localhost:3000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/video_prueba.mp4" \
  -F "title=Video de prueba GTR-PUCP" \
  -F "description=Video generado para pruebas del sistema" \
  -F "category_id=$CATEGORY_ID" \
  | python3 -m json.tool
```

### 13.4 Verificar el contenido subido

```bash
curl -s http://localhost:3000/api/content | python3 -m json.tool
# Debe mostrar los archivos que subiste con status 'active'
```

### 13.5 Probar el streaming de video

```bash
# Obtén el ID del video subido del paso anterior
VIDEO_ID="uuid-del-video"

# Test de streaming con petición de rango
curl -I -H "Range: bytes=0-1023" \
  http://localhost:3000/api/content/$VIDEO_ID/stream
# Debe responder con HTTP/1.1 206 Partial Content
```

---

## 14. Probar el buscador IA

### 14.1 Desde el navegador

1. Abre `http://localhost:5174` en tu navegador
2. Verás la interfaz del buscador IA con el título "¿Qué quieres aprender?"
3. Escribe cualquier consulta, por ejemplo: **"protocolo de redes LAN"**
4. Presiona Enter o el botón **Buscar**
5. Deberás ver:
   - Las tarjetas de contenido mock apareciendo primero
   - El texto del AI Overview apareciendo token a token (streaming)
   - Sugerencias de búsqueda relacionadas al final

### 14.2 Probar el botón de voz

1. Haz clic en el botón de micrófono (🎤) en la barra de búsqueda
2. Permite el acceso al micrófono cuando el navegador lo solicite
3. Habla durante 2-3 segundos ("¿Qué es una red LAN?")
4. El audio se envía al AI Engine mock, que responde con una transcripción ficticia
5. La búsqueda se ejecuta automáticamente con el texto transcrito

> **Nota**: El mock devuelve siempre `"[stub] Transcripción pendiente de implementación"` como texto de voz. Esto es esperado. El STT real requiere Whisper instalado.

### 14.3 Desde `http://localhost:5173` (client — plataforma educativa)

1. Abre `http://localhost:5173`
2. Esta es la interfaz principal del catálogo de contenido
3. Deberías ver el contenido que subiste en el paso anterior

---

## 15. Solución de problemas comunes

### "Cannot connect to PostgreSQL"

```bash
# Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# Verificar que el usuario y base de datos existen
sudo -u postgres psql -c "\du"    # listar usuarios
sudo -u postgres psql -c "\l"     # listar bases de datos

# Probar conexión directa
psql -U cdn_user -h localhost -d cdn_dev
# Si pide contraseña: cdn_pass_dev
```

### "Redis connection refused"

```bash
sudo systemctl start redis-server
redis-cli ping   # debe responder PONG
```

### "FFmpeg not found" al subir video

```bash
which ffmpeg        # debe mostrar /usr/bin/ffmpeg
ffmpeg -version     # debe mostrar información de versión
# Si no está instalado:
sudo apt install -y ffmpeg
```

### El mock del AI Engine no inicia: "ModuleNotFoundError: No module named 'fastapi'"

```bash
# Verificar que el venv está activo
which python3   # debe mostrar .../ai_env/bin/python3
# Si no, activar:
source /home/USUARIO/CDN/ai_env/bin/activate
pip install fastapi uvicorn pydantic
```

### "CORS error" en el browser al usar search_ui

El vite.config.ts de `search_ui` tiene un proxy configurado. Si ves errores de CORS es porque el frontend está intentando llamar directamente al backend sin pasar por el proxy. Asegúrate de que:
1. Estás accediendo a `http://localhost:5174` (no a un IP o dominio distinto)
2. El servidor Node.js corre en el puerto 3000
3. El AI Engine mock corre en el puerto 8000

### El schema SQL falla con "already exists"

```bash
# Si necesitas recrear la DB desde cero:
sudo -u postgres psql -c "DROP DATABASE cdn_dev;"
sudo -u postgres psql -c "CREATE DATABASE cdn_dev OWNER cdn_user;"
psql -U cdn_user -h localhost -d cdn_dev -f scripts/init_database_v2.sql
```

### `npm run dev` del servidor falla con error de TypeScript

```bash
cd /home/USUARIO/CDN/server
# Compilar primero para ver errores claramente
npm run build 2>&1 | head -40
```

---

## 16. Resumen rápido de puertos y URLs

```
┌─────────────────────────────────────────────────────────────────┐
│                   SERVICIOS EN PC DE ESCRITORIO                  │
│                                                                   │
│  Puerto 3000  →  CDN Backend (Node.js/Express)                   │
│               →  http://localhost:3000/health                     │
│               →  http://localhost:3000/api/auth/login             │
│               →  http://localhost:3000/api/content                │
│               →  http://localhost:3000/api/upload                 │
│                                                                   │
│  Puerto 8000  →  AI Engine mock (Python/FastAPI)                  │
│               →  http://localhost:8000/api/health                 │
│               →  http://localhost:8000/api/search                 │
│               →  http://localhost:8000/api/search/stream          │
│               →  http://localhost:8000/docs  ← Swagger UI        │
│                                                                   │
│  Puerto 5174  →  search_ui (React — Buscador IA)                  │
│               →  http://localhost:5174                            │
│                                                                   │
│  Puerto 5173  →  client (React — Plataforma educativa)            │
│               →  http://localhost:5173                            │
│                                                                   │
│  Puerto 5432  →  PostgreSQL (base de datos)                       │
│  Puerto 6379  →  Redis (cache)                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Documentación interactiva del AI Engine

Una vez que el mock está corriendo, puedes explorar todos los endpoints en:

```
http://localhost:8000/docs      ← Swagger UI interactivo
http://localhost:8000/redoc     ← Documentación ReDoc
```

Esto es especialmente útil para entender exactamente qué espera y retorna cada endpoint sin revisar el código.

---

## Apéndice — Usando tmux para múltiples terminales

Si prefieres no tener 4 ventanas abiertas, puedes usar `tmux`:

```bash
# Instalar tmux si no lo tienes
sudo apt install -y tmux

# Crear sesión llamada "cdn"
tmux new-session -d -s cdn

# Panel superior: CDN backend
tmux send-keys -t cdn "cd /home/USUARIO/CDN/server && npm run dev" ENTER

# Crear ventana nueva para AI Engine
tmux new-window -t cdn
tmux send-keys -t cdn "cd /home/USUARIO/CDN && source ai_env/bin/activate && python -m uvicorn ai_engine.mock_main:app --host 0.0.0.0 --port 8000 --reload" ENTER

# Crear ventana para search_ui
tmux new-window -t cdn
tmux send-keys -t cdn "cd /home/USUARIO/CDN/search_ui && npm run dev" ENTER

# Crear ventana para client
tmux new-window -t cdn
tmux send-keys -t cdn "cd /home/USUARIO/CDN/client && npm run dev" ENTER

# Conectar a la sesión para verla
tmux attach -t cdn
# Navegar entre ventanas: Ctrl+B + número (0, 1, 2, 3)
```

---

*Guía creada para el proyecto GTR-PUCP — CDN Educativa Offline, Marzo 2026.*
