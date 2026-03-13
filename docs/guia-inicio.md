# Guía de Inicio — Motor de Búsqueda IA

> **Proyecto**: GTR-PUCP — CDN Educativa Offline  
> **Fecha**: Febrero 2026  
> **Fase 1**: Jetson Orin Nano 8GB (~Semanas 1–4)  
> **Fase 2**: Jetson Orin NX 16GB (~Semanas 5–10)

Esta guía cubre todo lo necesario desde cero: hardware, software, descargas, compilación y verificación. Sigue el orden estrictamente — algunos pasos tardan horas y conviene lanzarlos antes de irse.

---

## Índice

0. [Visión general y estructura de carpetas](#0-visión-general-y-estructura-de-carpetas)
1. [Lista de compras y hardware necesario](#1-lista-de-compras-y-hardware-necesario)
2. [Paso previo: preparación en tu PC (antes de tocar la Jetson)](#2-paso-previo-preparación-en-tu-pc-antes-de-tocar-la-jetson)
3. [Flash JetPack 6.x en la Jetson Orin Nano 8GB](#3-flash-jetpack-6x-en-la-jetson-orin-nano-8gb)
4. [Configuración inicial del OS en la Jetson](#4-configuración-inicial-del-os-en-la-jetson)
5. [Instalación de dependencias del sistema](#5-instalación-de-dependencias-del-sistema)
6. [Clonar el repositorio y estructura del proyecto](#6-clonar-el-repositorio-y-estructura-del-proyecto)
7. [Descarga de modelos de HuggingFace](#7-descarga-de-modelos-de-huggingface)
8. [Construcción del dataset de calibración AWQ](#8-construcción-del-dataset-de-calibración-awq)
9. [Cuantización AWQ + compilación de engines TensorRT-LLM](#9-cuantización-awq--compilación-de-engines-tensorrt-llm)
10. [Instalación del AI Engine (FastAPI)](#10-instalación-del-ai-engine-fastapi)
11. [Integración con el CDN existente (Node.js)](#11-integración-con-el-cdn-existente-nodejs)
12. [Verificación end-to-end — Fase 1](#12-verificación-end-to-end--fase-1)
13. [Migración a Fase 2: Jetson Orin NX 16GB](#13-migración-a-fase-2-jetson-orin-nx-16gb)

---

## 0. Visión General y Estructura de Carpetas

### Por qué una sola base de código sirve a ambas plataformas

El código del AI Engine es **100% idéntico** en Fase 1 y Fase 2. Lo que cambia es una variable de entorno:

```
AI_PLATFORM=orin_nano_8gb   →  Fase 1, modelos 1B+3.8B, 30K chunks, semáforo cauteloso
AI_PLATFORM=orin_nx_16gb    →  Fase 2, modelos 1B+8B, 100K chunks, plan original completo
```

No hay carpetas separadas por plataforma. Hay **archivos `.env` separados** que se cargan según cuál Jetson está activa.

### Estructura final en el repo

```
CDN/
├── server/                  ← CDN existente (cambios mínimos)
│   └── src/
│       ├── routes/
│       │   └── ai.ts                     ← NUEVO (proxy hacia FastAPI)
│       ├── controllers/
│       │   └── aiSearchController.ts     ← NUEVO
│       └── middleware/
│           └── viewerAuth.ts             ← NUEVO
│
├── ai_engine/               ← NUEVO — corre EN la Jetson
│   ├── main.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings.py            ← selector de plataforma vía AI_PLATFORM
│   │   ├── prompts.py             ← system prompts L1/L2/L3/L4
│   │   └── platforms/
│   │       ├── orin_nano_8gb.env  ← variables Fase 1
│   │       └── orin_nx_16gb.env   ← variables Fase 2
│   ├── routers/
│   │   ├── search.py
│   │   ├── voice_search.py
│   │   ├── ingest.py
│   │   └── health.py
│   ├── services/
│   │   ├── resource_manager.py
│   │   ├── intent_router.py
│   │   ├── hybrid_retriever.py
│   │   ├── hyde_expander.py
│   │   ├── llm_engine.py
│   │   ├── grounding_verifier.py
│   │   ├── thermal_manager.py
│   │   └── ingestion/
│   │       ├── pdf_processor.py
│   │       ├── video_processor.py
│   │       ├── thumbnail_generator.py
│   │       └── chunker.py
│   ├── models/
│   │   └── schemas.py
│   ├── calibration/
│   │   └── peru_educational_es.jsonl   ← dataset AWQ (construir en §8)
│   └── tests/
│       ├── test_retrieval.py
│       ├── test_grounding.py
│       ├── test_stt.py
│       └── eval_dataset.jsonl
│
└── docs/
    ├── ai-search-engine-plan.md
    ├── jetson-comparison.md
    └── guia-inicio.md          ← este archivo
```

---

## 1. Lista de Compras y Hardware Necesario

### Hardware obligatorio (Fase 1)

| Ítem | Especificación mínima | Nota |
|---|---|---|
| **Jetson Orin Nano 8GB** | Developer Kit (incluye carrier board) | No comprar el módulo solo — necesita carrier board |
| **Active Heat Sink** | Para Orin Nano Developer Kit | Viene incluido en el developer kit oficial de NVIDIA |
| **SSD NVMe M.2** | 250 GB mínimo, PCIe 3.0 | Samsung 980 o WD SN570; la microSD es lenta para modelos |
| **Cable USB-C** | Para flashing inicial | El que viene con el kit suele funcionar |
| **PC de desarrollo** | Linux Ubuntu 20.04/22.04 x86_64 | Para NVIDIA SDK Manager (no funciona en VM con GPU passthrough limitado) |

**Alternativa si no tienes PC Linux para flashing**: La Jetson Orin Nano 8GB soporta boot desde NVMe directamente y puede comprarse con JetPack preinstalado en algunos vendedores (Seeed Studio, Waveshare).

### Hardware adicional Fase 2

| Ítem | Especificación | Nota |
|---|---|---|
| **Jetson Orin NX 16GB** | Developer Kit o módulo + carrier board Recomputer J4012 | La Recomputer J4012 de Seeed tiene mejor refrigeración para el NX |
| **Active Heat Sink** | **Obligatorio** para Orin NX — TDP 25W | Sin disipador activo el throttling corta el rendimiento a la mitad |
| **SSD NVMe M.2** | 500 GB — los engines 8B son ~8 GB compilados | El del Orin Nano (250 GB) no alcanza cómodamente para ambos engines |

### Cuentas necesarias (gratuitas)

- **NVIDIA Developer**: [developer.nvidia.com](https://developer.nvidia.com) → para descargar SDK Manager y TensorRT-LLM wheels
- **HuggingFace**: [huggingface.co](https://huggingface.co) → para descargar los modelos base (Llama-3.2-1B, Phi-3.5-mini, Llama-3.1-8B)
  - Llama-3.1-8B requiere aceptar la licencia de Meta en HF (tarda ~2 min)

---

## 2. Paso Previo: Preparación en tu PC (antes de tocar la Jetson)

Estos pasos corren en tu **PC de desarrollo** (Ubuntu 20.04/22.04 x86_64), no en la Jetson. Aprovecha para hacerlos mientras esperas el hardware o mientras flasheas.

### 2.1 Instalar NVIDIA SDK Manager (solo para flashing)

```bash
# Descarga desde: https://developer.nvidia.com/sdk-manager
# Elige: Linux_for_Tegra → JetPack 6.1 (o la última 6.x estable)
sudo apt install ./sdkmanager_*.deb
sdkmanager
```

> Si ya tienes la Jetson con JetPack 6.x preinstalado (comprado con imagen), salta directamente al §4.

### 2.2 Descargar los modelos base en el PC

Los modelos base de HuggingFace son grandes. Descárgalos en el PC mientras preparas la Jetson y luego los transfieres.

```bash
pip install huggingface_hub

# Autenticarse (necesario para Llama-3.x)
huggingface-cli login
# → Pega tu token desde https://huggingface.co/settings/tokens

# Crear directorio local de modelos
mkdir -p ~/jetson_models/hf_models

# Fase 1 — Orin Nano 8GB
python -c "
from huggingface_hub import snapshot_download
# Draft model (~2.4 GB)
snapshot_download('meta-llama/Llama-3.2-1B-Instruct',
                  local_dir='~/jetson_models/hf_models/Llama-3.2-1B-Instruct')
# Target model Fase 1 (~7.6 GB)
snapshot_download('microsoft/Phi-3.5-mini-instruct',
                  local_dir='~/jetson_models/hf_models/Phi-3.5-mini-instruct')
"

# Fase 2 — Orin NX 16GB (puedes descargar ahora también)
python -c "
from huggingface_hub import snapshot_download
# Target model Fase 2 (~16 GB)
snapshot_download('meta-llama/Llama-3.1-8B-Instruct',
                  local_dir='~/jetson_models/hf_models/Llama-3.1-8B-Instruct')
"
```

> **Tiempo estimado** con conexión de 50 Mbps: 1B (~45 min), Phi-3.5-mini (~2.5h), 8B (~45 min).  
> Lánzalos todos juntos y déjalos correr.

### 2.3 Instalar TensorRT-LLM en el PC para cuantizar (opcional)

La cuantización AWQ y la compilación de engines TRT-LLM se puede hacer **en la Jetson directamente** o en el PC con una GPU NVIDIA. Si tienes GPU NVIDIA en el PC es más rápido hacerlo allí.

Si no tienes GPU en el PC, no te preocupes — el §9 muestra cómo hacerlo directamente en la Jetson.

---

## 3. Flash JetPack 6.x en la Jetson Orin Nano 8GB

> **Salta este paso** si compraste la Jetson con JetPack preinstalado.

### 3.1 Proceso con SDK Manager

1. Conecta la Jetson al PC por USB-C **en modo recovery**: mantén apretado el botón `REC` mientras conectas la alimentación.
2. Abre SDK Manager y selecciona:
   - **Target Hardware**: Jetson Orin Nano 8GB Developer Kit
   - **JetPack version**: 6.1 (o la más reciente 6.x)
   - **Components**: `Jetson OS` + `Jetson SDK Components` (incluye CUDA 12.x, cuDNN, TensorRT)
3. Acepta licencias → Flash. Tarda ~45 minutos.

### 3.2 Verificar que JetPack flasheó correctamente

```bash
# En la Jetson (conectada por SSH o con monitor)
cat /etc/nv_tegra_release
# Debe mostrar: # R36 (release), REVISION: 4.x  (JetPack 6.x)

nvcc --version
# Debe mostrar: Cuda compilation tools, release 12.x

python3 -c "import tensorrt; print(tensorrt.__version__)"
# Si SDK Components se instalaron: 10.x.x
```

---

## 4. Configuración Inicial del OS en la Jetson

### 4.1 Primera arrancada

Completa el wizard de Ubuntu (usuario, contraseña, zona horaria Lima/Peru).  
Nombre de host recomendado: `jetson-cdn-dev` para Fase 1, `jetson-cdn-prod` para Fase 2.

### 4.2 Actualización y herramientas básicas

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    git curl wget htop nvtop \
    build-essential cmake ninja-build \
    python3-pip python3-venv python3-dev \
    ffmpeg \
    tesseract-ocr tesseract-ocr-spa \
    libpq-dev \
    redis-server \
    postgresql postgresql-contrib \
    nginx
```

### 4.3 Montar el SSD NVMe (si se usa)

```bash
# Identificar el disco
lsblk
# Típicamente aparece como /dev/nvme0n1

# Formatear (solo la primera vez)
sudo mkfs.ext4 /dev/nvme0n1

# Montar
sudo mkdir -p /mnt/ssd
sudo mount /dev/nvme0n1 /mnt/ssd

# Montar automáticamente al arrancar
echo "/dev/nvme0n1  /mnt/ssd  ext4  defaults  0  2" | sudo tee -a /etc/fstab

# Crear directorios del proyecto en el SSD
sudo mkdir -p /mnt/ssd/{models,trt_engines,trt_checkpoints,chromadb_data}
sudo chown -R $USER:$USER /mnt/ssd
```

### 4.4 Configurar el perfil de energía NVPModel

```bash
# Fase 1 — Orin Nano 8GB: Modo máximo (15W)
sudo nvpmodel -m 0
sudo jetson_clocks

# Verificar modo activo
sudo nvpmodel -q
# Debe mostrar: NV Power Mode: MAXN

# Instalar jtop para monitoreo (muy útil)
sudo pip3 install jetson-stats
sudo jtop   # interfaz de monitoreo completa
```

### 4.5 Configurar swap (obligatorio para compilación TRT-LLM)

```bash
# 8 GB de swap en el SSD — necesario para compilar engines grandes
sudo fallocate -l 8G /mnt/ssd/swapfile
sudo chmod 600 /mnt/ssd/swapfile
sudo mkswap /mnt/ssd/swapfile
sudo swapon /mnt/ssd/swapfile
echo "/mnt/ssd/swapfile  none  swap  sw  0  0" | sudo tee -a /etc/fstab

free -h
# Debe mostrar ~8G en Swap
```

---

## 5. Instalación de Dependencias del Sistema

### 5.1 spaCy con modelo español

```bash
pip3 install spacy==3.7.4
python3 -m spacy download es_core_news_sm
```

### 5.2 TensorRT-LLM (wheel ARM64 específico para JetPack 6.x)

Este es el paso más largo (~2 horas de compilación la primera vez).

```bash
# Opción A — Wheel precompilado de NVIDIA (recomendado si existe para tu JetPack)
# Verificar wheels disponibles:
# https://developer.nvidia.com/tensorrt-llm  (busca "ARM64 / Jetson")

pip3 install --extra-index-url https://pypi.ngc.nvidia.com \
    tensorrt-llm==0.10.0

# Verificar instalación
python3 -c "import tensorrt_llm; print('TRT-LLM OK:', tensorrt_llm.__version__)"
```

```bash
# Opción B — Compilar desde fuente (si no hay wheel precompilado)
# ⚠️ Tarda ~2-3 horas. Lanzar antes de dormir.
git clone https://github.com/NVIDIA/TensorRT-LLM.git --branch v0.10.0
cd TensorRT-LLM
pip3 install -r requirements.txt
python3 scripts/build_wheel.py --trt_root /usr/lib/aarch64-linux-gnu/ --python /usr/bin/python3
pip3 install build/tensorrt_llm-*.whl
```

### 5.3 Resto de dependencias Python

```bash
pip3 install \
    fastapi==0.111.0 \
    uvicorn[standard]==0.29.0 \
    pydantic==2.7.0 \
    python-multipart==0.0.9 \
    chromadb==0.5.0 \
    sentence-transformers==3.0.0 \
    rank_bm25==0.2.2 \
    transformers==4.41.0 \
    openai-whisper==20231117 \
    pymupdf==1.24.0 \
    pytesseract==0.3.10 \
    langdetect==1.0.9 \
    prometheus-client==0.20.0 \
    aiofiles==23.2.0 \
    httpx==0.27.0 \
    diskcache==5.6.3 \
    python-dotenv==1.0.0
```

> **Torch**: JetPack 6.x incluye PyTorch preinstalado para ARM64 con CUDA. No instales torch desde PyPI (se instalaría la versión CPU). Verifica: `python3 -c "import torch; print(torch.cuda.is_available())"` → debe imprimir `True`.

### 5.4 Verificar CUDA funcional con Python

```bash
python3 -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA disponible:', torch.cuda.is_available())
print('GPU:', torch.cuda.get_device_name(0))
x = torch.randn(1000, 1000, device='cuda')
print('Tensor en GPU OK, shape:', x.shape)
"
```

---

## 6. Clonar el Repositorio y Estructura del Proyecto

```bash
# En la Jetson
cd /mnt/ssd
git clone <url-de-tu-repo> CDN
cd CDN

# Crear symlinks para almacenamiento pesado en el SSD
ln -s /mnt/ssd/models          ai_engine/models_cache
ln -s /mnt/ssd/trt_engines     ai_engine/trt_engines
ln -s /mnt/ssd/trt_checkpoints ai_engine/trt_checkpoints
ln -s /mnt/ssd/chromadb_data   ai_engine/chromadb_data
```

### .env activo para Fase 1

```bash
# Copiar el .env de Fase 1 como .env activo
cp ai_engine/config/platforms/orin_nano_8gb.env ai_engine/.env

# Verificar que la plataforma cargará bien
python3 -c "
from dotenv import load_dotenv; import os
load_dotenv('ai_engine/.env')
print('Plataforma activa:', os.getenv('AI_PLATFORM'))
"
# → orin_nano_8gb
```

---

## 7. Descarga de Modelos de HuggingFace

Si ya descargaste los modelos en el PC (§2.2), transfiérelos por rsync:

```bash
# Desde el PC, hacia la Jetson
rsync -avz --progress ~/jetson_models/hf_models/ \
    usuario@jetson-cdn-dev:/mnt/ssd/models/hf_models/
```

Si no los tienes en el PC, descarga directamente en la Jetson:

```bash
# En la Jetson
pip3 install huggingface_hub
huggingface-cli login

python3 - <<'EOF'
from huggingface_hub import snapshot_download

# Draft model — Fase 1 y 2 comparten el mismo draft
snapshot_download(
    "meta-llama/Llama-3.2-1B-Instruct",
    local_dir="/mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct"
)
print("✓ Draft Llama-3.2-1B descargado")

# Target model Fase 1
snapshot_download(
    "microsoft/Phi-3.5-mini-instruct",
    local_dir="/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct"
)
print("✓ Target Phi-3.5-mini descargado")
EOF
```

### Whisper (modelo STT)

```bash
python3 -c "
import whisper
# Tiny: para STT de consultas en tiempo real (~39 MB)
whisper.load_model('tiny', download_root='/mnt/ssd/models/whisper')
# Small: para ingesta de videos en batch (~244 MB)
whisper.load_model('small', download_root='/mnt/ssd/models/whisper')
print('Whisper OK')
"
```

### multilingual-e5-small (embeddings)

```bash
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(
    'intfloat/multilingual-e5-small',
    cache_folder='/mnt/ssd/models/embeddings'
)
test = model.encode(['Hola mundo'], device='cuda')
print('e5-small OK, shape:', test.shape)
"
```

### Cross-Encoder (re-ranker)

```bash
python3 -c "
from sentence_transformers import CrossEncoder
model = CrossEncoder(
    'cross-encoder/ms-marco-MiniLM-L-6-v2',
    max_length=512
)
score = model.predict([('¿Qué es OSPF?', 'OSPF es un protocolo de enrutamiento...')])
print('Cross-Encoder OK, score:', score)
"
```

---

## 8. Construcción del Dataset de Calibración AWQ

La cuantización AWQ **preserva mejor la calidad** cuando el dataset de calibración refleja el dominio real. Para el proyecto GTR-PUCP, el dominio es educación secundaria peruana.

### 8.1 Estructura del dataset

El archivo `ai_engine/calibration/peru_educational_es.jsonl` debe tener mínimo **512 muestras** con este formato:

```jsonl
{"text": "Las redes de área local (LAN) permiten conectar computadoras en un mismo edificio..."}
{"text": "La fotosíntesis es el proceso mediante el cual las plantas producen glucosa..."}
{"text": "El teorema de Pitágoras establece que en un triángulo rectángulo..."}
```

### 8.2 Fuentes recomendadas para construir el dataset

```bash
# Opción A — Textos del MINEDU (dominio público)
# Descargar libros de texto de secundaria desde:
# https://www.minedu.gob.pe/textos-escolares/
# Extraer texto con PyMuPDF y samplear fragmentos de 256 tokens

# Opción B — Contenido ya indexado en la CDN
# Si ya tienes PDFs en /storage/documents/, extraer texto:
python3 - <<'EOF'
import fitz, json, random, pathlib

chunks = []
for pdf_path in pathlib.Path("/home/jleon/2026/PUCP/GTR/CDN/storage/documents").glob("*.pdf"):
    doc = fitz.open(str(pdf_path))
    for page in doc:
        text = page.get_text().strip()
        if len(text) > 200:
            # Tomar fragmentos de ~256 tokens (~1200 caracteres)
            for i in range(0, min(len(text), 3000), 1200):
                chunk = text[i:i+1200].strip()
                if len(chunk) > 200:
                    chunks.append({"text": chunk})

random.shuffle(chunks)
selected = chunks[:512]

out = pathlib.Path("ai_engine/calibration/peru_educational_es.jsonl")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    for c in selected:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

print(f"Dataset generado: {len(selected)} muestras → {out}")
EOF
```

> Si aún no tienes contenido en la CDN: usa los textos de muestra del directorio `ai_engine/calibration/seeds/` (se incluirán muestras iniciales en el repo). Son suficientes para comenzar; el dataset puede enriquecerse después.

---

## 9. Cuantización AWQ + Compilación de Engines TensorRT-LLM

> ⚠️ **Tiempo total estimado para Fase 1**: ~3–5 horas.  
> Lanzar en un `tmux` o `screen` para que continúe si se cierra la terminal.

```bash
# Instalar tmux si no lo tienes
sudo apt install -y tmux
tmux new -s trt_build
```

### 9.1 Cuantizar el draft model (Llama-3.2-1B) — Común a Fase 1 y 2

```bash
python3 -c "
import tensorrt_llm
from tensorrt_llm.quantization import quantize_and_export

quantize_and_export(
    model_dir='/mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct',
    output_dir='/mnt/ssd/trt_checkpoints/llama32-1b-int4-awq',
    qformat='int4_awq',
    calib_size=512,
    calib_dataset='/mnt/ssd/CDN/ai_engine/calibration/peru_educational_es.jsonl',
    dtype='float16',
)
print('Cuantización 1B completada')
"
```

### 9.2 Compilar el engine del draft model

```bash
trtllm-build \
    --checkpoint_dir /mnt/ssd/trt_checkpoints/llama32-1b-int4-awq \
    --output_dir     /mnt/ssd/trt_engines/llama32-1b-int4 \
    --gemm_plugin auto \
    --gpt_attention_plugin auto \
    --max_batch_size 1 \
    --max_input_len  1024 \
    --max_seq_len    1280 \
    --use_paged_context_fmha enable \
    --speculative_decoding_mode draft_tokens_external

echo "✓ Engine draft 1B compilado"
ls -lh /mnt/ssd/trt_engines/llama32-1b-int4/
```

### 9.3 Cuantizar el target model Fase 1 (Phi-3.5-mini-3.8B)

```bash
python3 -c "
import tensorrt_llm
from tensorrt_llm.quantization import quantize_and_export

quantize_and_export(
    model_dir='/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct',
    output_dir='/mnt/ssd/trt_checkpoints/phi35-mini-int4-awq',
    qformat='int4_awq',
    calib_size=512,
    calib_dataset='/mnt/ssd/CDN/ai_engine/calibration/peru_educational_es.jsonl',
    dtype='float16',
)
print('Cuantización Phi-3.5-mini completada')
"
```

### 9.4 Compilar el engine del target model Fase 1

```bash
trtllm-build \
    --checkpoint_dir /mnt/ssd/trt_checkpoints/phi35-mini-int4-awq \
    --output_dir     /mnt/ssd/trt_engines/phi35-mini-int4 \
    --gemm_plugin auto \
    --gpt_attention_plugin auto \
    --max_batch_size 1 \
    --max_input_len  1024 \
    --max_seq_len    1536 \
    --use_paged_context_fmha enable \
    --speculative_decoding_mode draft_tokens_external

echo "✓ Engine target 3.8B compilado"
ls -lh /mnt/ssd/trt_engines/phi35-mini-int4/
```

### 9.5 Verificación rápida de los engines

```bash
python3 - <<'EOF'
import tensorrt_llm
from tensorrt_llm.runtime import ModelRunnerCpp
import pathlib

DRAFT_DIR  = "/mnt/ssd/trt_engines/llama32-1b-int4"
TARGET_DIR = "/mnt/ssd/trt_engines/phi35-mini-int4"

for name, engine_dir in [("Draft 1B", DRAFT_DIR), ("Target 3.8B", TARGET_DIR)]:
    runner = ModelRunnerCpp.from_dir(engine_dir, rank=0)
    test_ids = [[1, 2, 3, 4, 5]]
    output = runner.generate(test_ids, max_new_tokens=10)
    print(f"✓ {name}: generación OK, shape: {output.output_ids.shape}")
    del runner
EOF
```

---

## 10. Instalación del AI Engine (FastAPI)

### 10.1 Configurar variables de entorno

```bash
# Verificar que el .env de Fase 1 está activo
cat ai_engine/.env | grep AI_PLATFORM
# → AI_PLATFORM=orin_nano_8gb

# Variables adicionales de entorno
cat >> ai_engine/.env << 'EOF'
# Rutas de engines (deben coincidir con §9)
DRAFT_MODEL_DIR=/mnt/ssd/trt_engines/llama32-1b-int4
TARGET_MODEL_DIR=/mnt/ssd/trt_engines/phi35-mini-int4
WHISPER_MODEL_DIR=/mnt/ssd/models/whisper
EMBED_MODEL_DIR=/mnt/ssd/models/embeddings
CHROMADB_PATH=/mnt/ssd/chromadb_data
STORAGE_PATH=/mnt/ssd/CDN/storage

# CDN Backend
CDN_BACKEND_URL=http://localhost:3000
AI_ENGINE_HOST=0.0.0.0
AI_ENGINE_PORT=8000
EOF
```

### 10.2 Primer arranque del AI Engine

```bash
cd /mnt/ssd/CDN
uvicorn ai_engine.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --env-file ai_engine/.env \
    --workers 1 \
    --log-level info
```

### 10.3 Verificar health check

```bash
# En otra terminal
curl http://localhost:8000/api/health | python3 -m json.tool
```

Respuesta esperada:

```json
{
  "status": "ok",
  "platform": "orin_nano_8gb",
  "components": {
    "llm_engine": "ready",
    "retriever": "ready",
    "stt": "ready",
    "thermal": "nominal",
    "chroma_chunks": 0
  }
}
```

### 10.4 Configurar servicio systemd (arranque automático)

```bash
sudo tee /etc/systemd/system/ai-engine.service << 'EOF'
[Unit]
Description=GTR-PUCP AI Engine (FastAPI)
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=jleon
WorkingDirectory=/mnt/ssd/CDN
EnvironmentFile=/mnt/ssd/CDN/ai_engine/.env
ExecStart=/usr/bin/python3 -m uvicorn ai_engine.main:app \
    --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
RestartSec=10
StandardOutput=append:/mnt/ssd/CDN/logs/ai_engine.log
StandardError=append:/mnt/ssd/CDN/logs/ai_engine.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-engine
sudo systemctl start ai-engine
sudo systemctl status ai-engine
```

---

## 11. Integración con el CDN Existente (Node.js)

### 11.1 Cambios mínimos en el servidor Node.js existente

Solo hay **3 archivos nuevos** que añadir al `server/` existente. El resto del CDN no se toca.

```bash
# Instalar dependencias necesarias en el servidor Node.js
cd /mnt/ssd/CDN/server
npm install
# (httpx ya está disponible como fetch nativo en Node 18+)
```

### 11.2 Variable de entorno en el server

```bash
# Añadir al server/.env
echo "AI_ENGINE_URL=http://localhost:8000" >> server/.env
```

### 11.3 Verificar proxy end-to-end (antes de implementar el frontend)

```bash
# Con el AI Engine corriendo en :8000
# Y el CDN server corriendo en :3000

# Test directo al AI Engine (sin CDN)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es una red LAN?", "context": {"user_role": "student"}}'

# Test a través del CDN (requiere JWT válido)
curl -X POST http://localhost:3000/api/ai/search \
  -H "Authorization: Bearer <tu_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es una red LAN?"}'
```

---

## 12. Verificación End-to-End — Fase 1

Sigue esta secuencia en orden. Cada ítem es un gate — no avanzar si falla el anterior.

### ✅ Checklist de preparación de hardware

- [ ] `sudo nvpmodel -q` → muestra `MAXN` (modo 15W)
- [ ] `sudo jetson_clocks` ejecutado
- [ ] Fan girando (audible o visible en `jtop` → Fans)
- [ ] SSD montado: `df -h /mnt/ssd` muestra espacio disponible
- [ ] Swap activo: `free -h` muestra ~8G en Swap
- [ ] Temperatura en reposo < 45°C: `cat /sys/class/thermal/thermal_zone*/temp`

### ✅ Checklist de stack software

- [ ] `python3 -c "import tensorrt_llm; print('OK')"` → OK
- [ ] `python3 -c "import torch; print(torch.cuda.is_available())"` → True
- [ ] `python3 -c "import chromadb; print('OK')"` → OK
- [ ] `systemctl is-active postgresql` → active
- [ ] `systemctl is-active redis` → active
- [ ] `systemctl is-active ai-engine` → active

### ✅ Checklist de engines TRT-LLM

- [ ] `ls /mnt/ssd/trt_engines/llama32-1b-int4/` → muestra archivos `.engine`
- [ ] `ls /mnt/ssd/trt_engines/phi35-mini-int4/` → muestra archivos `.engine`
- [ ] Test de generación del §9.5 pasa sin errores

### ✅ Checklist funcional

- [ ] `GET /api/health` → status: ok, platform: orin_nano_8gb
- [ ] Ingestar un PDF de prueba: `POST /api/ingest` con content\_id de un PDF existente
- [ ] `GET /api/health` → chroma\_chunks > 0
- [ ] Búsqueda texto: `POST /api/search` con query simple → recibe SSE con tokens
- [ ] Latencia primera respuesta < 20s (esperado ~12s; si supera 30s revisar thermal)
- [ ] Búsqueda por voz: `POST /api/voice-search` con archivo WAV de 5s → transcribe + busca
- [ ] Test de carga mínima: 2 búsquedas consecutivas sin OOM

### ✅ Checklist térmico

```bash
# Correr 5 búsquedas seguidas y monitorear temperatura
watch -n 2 'cat /sys/class/thermal/thermal_zone*/temp | awk "{print \$1/1000 \"°C\"}"'
# Temperatura bajo carga sostenida en Orin Nano 8GB con disipador activo: < 65°C
```

---

## 13. Migración a Fase 2: Jetson Orin NX 16GB

Cuando el desarrollo y pruebas de la Fase 1 estén completos, la migración tarda **~4 horas**, casi todo en compilación del engine 8B.

### 13.1 Preparar la Jetson Orin NX 16GB

Repetir los pasos §3 y §4 en la nueva Jetson, o usar clonado de imagen si los vendors lo permiten. La nueva Jetson también necesita:
- JetPack 6.x
- El mismo SSD (transferir o usar uno nuevo de 500 GB)
- Active Heat Sink **instalado y conectado**

### 13.2 Cambiar el .env activo

```bash
# En la Jetson Orin NX 16GB
cp ai_engine/config/platforms/orin_nx_16gb.env ai_engine/.env

# Verificar
python3 -c "
from dotenv import load_dotenv; import os
load_dotenv('ai_engine/.env')
print('Plataforma activa:', os.getenv('AI_PLATFORM'))
"
# → orin_nx_16gb
```

### 13.3 Cuantizar y compilar el target model 8B

```bash
# El draft model ya está compilado en Fase 1 — copiar o recompilar
# Si se usa el mismo SSD: ya existe /mnt/ssd/trt_engines/llama32-1b-int4/

# Cuantizar Llama-3.1-8B (si no se descargó antes, ver §2.2)
python3 -c "
import tensorrt_llm
from tensorrt_llm.quantization import quantize_and_export

quantize_and_export(
    model_dir='/mnt/ssd/models/hf_models/Llama-3.1-8B-Instruct',
    output_dir='/mnt/ssd/trt_checkpoints/llama31-8b-int4-awq',
    qformat='int4_awq',
    calib_size=512,
    calib_dataset='/mnt/ssd/CDN/ai_engine/calibration/peru_educational_es.jsonl',
    dtype='float16',
)
print('Cuantización 8B completada')
"

# Compilar engine 8B (~2-3 horas, lanzar en tmux)
trtllm-build \
    --checkpoint_dir /mnt/ssd/trt_checkpoints/llama31-8b-int4-awq \
    --output_dir     /mnt/ssd/trt_engines/llama31-8b-int4 \
    --gemm_plugin auto \
    --gpt_attention_plugin auto \
    --max_batch_size 1 \
    --max_input_len  2560 \
    --max_seq_len    3584 \
    --use_paged_context_fmha enable \
    --speculative_decoding_mode draft_tokens_external

echo "✓ Engine target 8B compilado"
```

### 13.4 Actualizar el .env con las nuevas rutas

```bash
# El orin_nx_16gb.env ya configura el TARGET_MODEL_DIR correcto
# Solo verificar que el path existe:
ls /mnt/ssd/trt_engines/llama31-8b-int4/
```

### 13.5 Re-indexar ChromaDB a capacidad completa (100K chunks)

```bash
# Si en Fase 1 se limitó CHROMA_MAX=30000, ahora se amplía a 100000
# El .env de orin_nx_16gb ya tiene CHROMA_MAX=100000

# Re-ingestar todo el contenido del CDN
curl -X POST http://localhost:8000/api/ingest/reindex-all \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'

# Monitorear progreso
curl http://localhost:8000/api/health | python3 -m json.tool
# → chroma_chunks irá aumentando
```

### 13.6 Cambios en Node.js para Fase 2

**Ninguno.** El CDN backend (`server/`) no cambia nada. Solo el AI Engine en la Jetson recibe la config nueva.

### 13.7 Verificar Fase 2

Repetir el checklist del §12 con estos valores objetivo:

| Métrica | Fase 1 (Nano 8GB) | Fase 2 (NX 16GB) |
|---|---|---|
| Latencia primera respuesta texto | ~12–15 s | ~7–9 s |
| Temperatura bajo carga sostenida | < 65°C | < 70°C |
| `chroma_chunks` máximo útil | 30,000 | 100,000 |
| Calidad de respuesta LLM | Funcional (3.8B) | Producción (8B) |
| `platform` en `/api/health` | `orin_nano_8gb` | `orin_nx_16gb` |

---

## Apéndice A: Solución de Problemas Comunes

### OOM (Out Of Memory) al arrancar los engines

```bash
# Verificar swap activo
free -h   # debe mostrar ~8G en Swap

# Verificar cuánta RAM libre hay antes de cargar
cat /proc/meminfo | grep AvailableMem
# Si hay < 2 GB libres antes de cargar el engine, cerrar procesos pesados
sudo systemctl stop postgresql  # temporal para diagnóstico
```

### TRT-LLM no encuentra los engines al arrancar

```bash
# Verificar que las rutas en .env apuntan exactamente al directorio con los .engine
ls /mnt/ssd/trt_engines/llama32-1b-int4/
# Debe mostrar: config.json, rank0.engine (o similar)
```

### Temperatura muy alta bajo carga (>80°C en Nano)

```bash
# Bajar al modo 1 (10W) temporalmente
sudo nvpmodel -m 1
# El thermal_manager.py hará esto automáticamente si está funcionando correctamente
```

### Fan no gira o no es reconocido

```bash
cat /sys/class/thermal/cooling_device*/type
# Debe mostrar "pwm-fan" en alguna línea
# Si no aparece: verificar conexión del conector del fan en la carrier board
```

### Whisper transcribe incorrectamente en español

```bash
# Forzar idioma español en el transcribe
result = stt_model.transcribe(audio_path, language="es", fp16=False)
# Solo usar language=None si se quiere detección automática para quechua
```

---

## Apéndice B: URLs de Descarga y Recursos

| Recurso | URL |
|---|---|
| NVIDIA SDK Manager | https://developer.nvidia.com/sdk-manager |
| JetPack 6.x Release Notes | https://developer.nvidia.com/embedded/jetpack-sdk-61 |
| TensorRT-LLM repositorio | https://github.com/NVIDIA/TensorRT-LLM |
| Llama-3.2-1B (HF) | https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct |
| Phi-3.5-mini (HF) | https://huggingface.co/microsoft/Phi-3.5-mini-instruct |
| Llama-3.1-8B (HF) | https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct |
| multilingual-e5-small (HF) | https://huggingface.co/intfloat/multilingual-e5-small |
| ms-marco-MiniLM-L-6-v2 (HF) | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Textos MINEDU (calibración) | https://www.minedu.gob.pe/textos-escolares/ |
| jetson-stats (jtop) | https://github.com/rbonghi/jetson_stats |
