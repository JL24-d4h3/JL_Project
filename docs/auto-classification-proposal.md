# Propuesta: Clasificación Automática de Contenido

**Fecha:** 2026-03-17
**Estado:** Propuesta
**Problema:** Los usuarios clasifican contenido de forma incorrecta, causando ruido en los resultados de búsqueda.

---

## 1. Diagnóstico del Problema Actual

### Situación
- El usuario sube contenido y selecciona manualmente la categoría
- Esta clasificación manual es **ruidosa** e inconsistente
- El motor de búsqueda vectorial devuelve resultados con scores cercanos (0.75-0.82) sin poder discriminar bien
- Ejemplo: "SIMULADOR DE PETICIONES" aparece en búsquedas de "visión artificial" porque los embeddings no capturan suficiente contexto semántico

### Causa Raíz
El sistema actual confía en metadatos manuales que no reflejan el contenido real del archivo.

---

## 2. Arquitectura Propuesta: Doble Pipeline con IA Clasificadora

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE DE INGESTA                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [Usuario sube archivo]                                                │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────┐                                                     │
│   │  Extracción   │  ← PyMuPDF, tree-sitter, Whisper                   │
│   │  de Texto     │                                                     │
│   └───────┬───────┘                                                     │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────────────────────────────────────────────┐            │
│   │           IA CLASIFICADORA (Modelo B)                  │            │
│   │                                                        │            │
│   │  • Zero-Shot Classification (BART-MNLI)               │            │
│   │  • Extrae: categoría, subcategoría, tags, dominio     │            │
│   │  • Genera: resumen técnico (50-100 palabras)          │            │
│   │  • Detecta: lenguaje, frameworks, conceptos clave     │            │
│   └───────────────────────────────────────────────────────┘            │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────┐     ┌───────────────┐                              │
│   │  Embeddings   │     │   Metadatos   │                              │
│   │  (e5-small)   │     │  Enriquecidos │                              │
│   └───────┬───────┘     └───────┬───────┘                              │
│           │                     │                                       │
│           └─────────┬───────────┘                                       │
│                     ▼                                                   │
│            ┌─────────────────┐                                         │
│            │    ChromaDB     │                                         │
│            │  (vector + meta)│                                         │
│            └─────────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE DE CONSULTA                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [Usuario busca "visión artificial"]                                   │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────────────────────────────────────────────┐            │
│   │         CLASIFICADOR DE QUERY (ligero)                 │            │
│   │                                                        │            │
│   │  Input:  "visión artificial"                          │            │
│   │  Output: dominio="AI", área="computer_vision"         │            │
│   └───────────────────────────────────────────────────────┘            │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────────────────────────────────────────────┐            │
│   │              BÚSQUEDA FILTRADA                         │            │
│   │                                                        │            │
│   │  1. Filtro por metadatos: WHERE dominio="AI"          │            │
│   │  2. Búsqueda vectorial en subset filtrado             │            │
│   │  3. Solo candidatos semánticamente compatibles        │            │
│   └───────────────────────────────────────────────────────┘            │
│           │                                                             │
│           ▼                                                             │
│   ┌───────────────┐                                                     │
│   │   Resultados  │  ← Solo contenido de "computer_vision"             │
│   │   Precisos    │     SIMULADOR filtrado en paso 1                   │
│   └───────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Taxonomía de Clasificación Automática

### Dominios Principales (Nivel 1)
```python
DOMAINS = {
    "AI": "Inteligencia Artificial y Machine Learning",
    "CS": "Ciencias de la Computación (algoritmos, estructuras)",
    "SE": "Ingeniería de Software (arquitectura, patrones)",
    "DB": "Bases de Datos y Almacenamiento",
    "NET": "Redes y Comunicaciones",
    "MATH": "Matemáticas y Estadística",
    "OTHER": "Otros / No clasificado",
}
```

### Áreas (Nivel 2) - Ejemplo para AI
```python
AI_AREAS = {
    "computer_vision": ["opencv", "cv2", "yolo", "unet", "cnn", "imagen", "segmentación"],
    "nlp": ["transformers", "bert", "gpt", "tokenizer", "embeddings", "texto"],
    "deep_learning": ["pytorch", "tensorflow", "keras", "neural", "red neuronal"],
    "ml_general": ["sklearn", "regresión", "clasificación", "clustering"],
    "reinforcement": ["gym", "reward", "agent", "environment", "q-learning"],
}
```

### Detección por Señales
```python
SIGNALS = {
    # Imports de código
    "import cv2": ("AI", "computer_vision", 0.9),
    "from ultralytics": ("AI", "computer_vision", 0.95),
    "import torch": ("AI", "deep_learning", 0.8),

    # Términos en texto
    "segmentación de imágenes": ("AI", "computer_vision", 0.85),
    "detección de objetos": ("AI", "computer_vision", 0.9),
    "meta-learning": ("AI", "ml_general", 0.8),

    # Patrones de código
    "SELECT.*FROM": ("DB", "sql", 0.9),
    "socket.connect": ("NET", "networking", 0.85),
}
```

---

## 4. Implementación del Clasificador

### Opción A: Zero-Shot con BART-MNLI (Recomendada)

```python
from transformers import pipeline

classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli",
                      device="cpu")

def classify_content(text: str) -> dict:
    """Clasifica contenido usando zero-shot."""

    # Nivel 1: Dominio
    domains = ["inteligencia artificial", "bases de datos",
               "redes", "ingeniería de software", "matemáticas"]
    result = classifier(text[:1000], domains)
    domain = result["labels"][0]
    domain_score = result["scores"][0]

    # Nivel 2: Área específica (si es AI)
    if domain == "inteligencia artificial":
        areas = ["visión artificial", "procesamiento de lenguaje",
                 "aprendizaje profundo", "aprendizaje por refuerzo"]
        result = classifier(text[:1000], areas)
        area = result["labels"][0]
        area_score = result["scores"][0]

    return {
        "domain": domain,
        "domain_confidence": domain_score,
        "area": area,
        "area_confidence": area_score,
        "tags": extract_tags(text),  # keywords extraídos
    }
```

### Opción B: Clasificación por Señales (Más rápida, menos precisa)

```python
import re
from collections import Counter

def classify_by_signals(text: str, code: str) -> dict:
    """Clasificación rápida basada en patrones."""

    scores = Counter()

    # Analizar imports
    imports = re.findall(r'(?:import|from)\s+(\w+)', code)
    for imp in imports:
        if imp in ["cv2", "PIL", "skimage"]:
            scores[("AI", "computer_vision")] += 2
        elif imp in ["torch", "tensorflow", "keras"]:
            scores[("AI", "deep_learning")] += 1
        elif imp in ["socket", "requests", "aiohttp"]:
            scores[("NET", "networking")] += 2

    # Analizar texto
    text_lower = text.lower()
    if "visión" in text_lower or "imagen" in text_lower:
        scores[("AI", "computer_vision")] += 1
    if "yolo" in text_lower or "detección" in text_lower:
        scores[("AI", "computer_vision")] += 2

    if not scores:
        return {"domain": "OTHER", "area": "unknown", "confidence": 0.0}

    best = scores.most_common(1)[0]
    return {
        "domain": best[0][0],
        "area": best[0][1],
        "confidence": min(best[1] / 5.0, 1.0),  # normalizar
    }
```

### Opción C: Híbrida (Recomendada para producción)

```python
def classify_hybrid(text: str, code: str) -> dict:
    """
    1. Primero intenta clasificación por señales (rápida)
    2. Si confidence < 0.7, usa zero-shot (precisa)
    """

    # Paso 1: Señales
    signal_result = classify_by_signals(text, code)

    if signal_result["confidence"] >= 0.7:
        return signal_result

    # Paso 2: Zero-shot como fallback
    zero_shot_result = classify_content(text)

    # Combinar resultados
    return {
        "domain": zero_shot_result["domain"],
        "area": zero_shot_result["area"],
        "confidence": zero_shot_result["domain_confidence"],
        "method": "zero_shot",
    }
```

---

## 5. Modificaciones al Pipeline de Ingesta

### Archivo: `ai_engine/services/ingestion/pipeline.py`

```python
async def ingest_content(content_id: str) -> dict:
    """Pipeline de ingesta con clasificación automática."""

    # 1. Obtener metadata del backend
    meta = await _fetch_content_metadata(content_id)

    # 2. Extraer texto según tipo
    file_path = _resolve_file_path(meta)
    text, code = await _extract_text_and_code(file_path, meta["type"])

    # 3. NUEVO: Clasificación automática
    classification = await _classify_content(text, code)

    # 4. Generar chunks con metadatos enriquecidos
    chunks = await _create_chunks(text, meta, classification)

    # 5. Indexar en ChromaDB con metadatos de clasificación
    added = await _index_chunks(
        content_id,
        chunks,
        extra_metadata={
            "auto_domain": classification["domain"],
            "auto_area": classification["area"],
            "auto_confidence": classification["confidence"],
            "auto_tags": ",".join(classification.get("tags", [])),
        }
    )

    return {"chunks_added": added, "classification": classification}
```

---

## 6. Modificaciones a la Búsqueda

### Archivo: `ai_engine/services/hybrid_retriever.py`

```python
def _search_sync(self, query: str, k_fetch: int, k_final: int) -> list[dict]:
    """Búsqueda con pre-filtrado por clasificación."""

    # 1. Clasificar la query
    query_class = self._classify_query(query)
    # Ej: {"domain": "AI", "area": "computer_vision"}

    # 2. Construir filtro de metadatos
    where_filter = None
    if query_class["confidence"] > 0.6:
        where_filter = {
            "$and": [
                {"auto_domain": query_class["domain"]},
                # Opcional: filtrar por área también
                # {"auto_area": query_class["area"]},
            ]
        }

    # 3. Búsqueda vectorial CON filtro
    chroma_results = self._collection.query(
        query_embeddings=[query_emb],
        n_results=k_fetch,
        where=where_filter,  # ← NUEVO: pre-filtrado
        include=["documents", "metadatas", "distances"],
    )

    # ... resto del pipeline (BM25, RRF, etc.)
```

### Clasificación de Query (ligera)

```python
def _classify_query(self, query: str) -> dict:
    """Clasificación rápida de la consulta del usuario."""

    query_lower = query.lower()

    # Mapeo de términos a dominios
    if any(t in query_lower for t in ["visión", "imagen", "yolo", "opencv", "cnn", "segmentación"]):
        return {"domain": "AI", "area": "computer_vision", "confidence": 0.85}

    if any(t in query_lower for t in ["red neuronal", "deep learning", "pytorch", "tensorflow"]):
        return {"domain": "AI", "area": "deep_learning", "confidence": 0.8}

    if any(t in query_lower for t in ["sql", "query", "base de datos", "postgresql"]):
        return {"domain": "DB", "area": "sql", "confidence": 0.85}

    if any(t in query_lower for t in ["socket", "tcp", "http", "api", "servidor"]):
        return {"domain": "NET", "area": "networking", "confidence": 0.8}

    # Sin clasificación clara → búsqueda sin filtro
    return {"domain": None, "area": None, "confidence": 0.0}
```

---

## 7. Resultado Esperado

### Antes (actual)
```
Query: "visión artificial"
Resultados:
  - U-net: 0.82 ✓
  - DATA AUGMENTATION: 0.79 ✓
  - META: 0.78 ?
  - YOLO: 0.78 ✓
  - SIMULADOR DE PETICIONES: 0.75 ✗ ← RUIDO
```

### Después (propuesto)
```
Query: "visión artificial"
  ↓ Clasificación: domain=AI, area=computer_vision
  ↓ Filtro: WHERE auto_domain="AI" AND auto_area="computer_vision"

Resultados:
  - YOLO: 0.92 ✓  (clasificado como computer_vision)
  - U-net: 0.89 ✓  (clasificado como computer_vision)
  - DATA AUGMENTATION: 0.85 ✓  (clasificado como computer_vision)

  (META y SIMULADOR ni siquiera entran al ranking porque
   fueron clasificados en otros dominios)
```

---

## 8. Plan de Implementación

### Fase 1: Clasificador por Señales (1-2 días)
- [ ] Implementar `classify_by_signals()` en pipeline.py
- [ ] Agregar metadatos `auto_domain`, `auto_area` a ChromaDB
- [ ] Re-indexar contenido existente

### Fase 2: Filtrado en Búsqueda (1 día)
- [ ] Implementar `_classify_query()` en hybrid_retriever.py
- [ ] Agregar filtro `where` en búsqueda ChromaDB
- [ ] Probar con queries de prueba

### Fase 3: Zero-Shot como Fallback (2-3 días)
- [ ] Agregar modelo BART-MNLI o similar
- [ ] Implementar clasificación híbrida
- [ ] Optimizar para CPU (cuantización)

### Fase 4: UI para Corrección (opcional)
- [ ] Mostrar clasificación automática al usuario
- [ ] Permitir corrección manual (feedback)
- [ ] Usar correcciones para mejorar el clasificador

---

## 9. Recursos Necesarios

| Componente | Modelo | Tamaño | Latencia |
|------------|--------|--------|----------|
| Señales | Regex + heurísticas | 0 KB | <1ms |
| Zero-Shot | BART-MNLI | ~1.5 GB | ~500ms/doc |
| Alternativa | DistilBERT | ~250 MB | ~100ms/doc |

### Recomendación para Laptop
Usar **clasificación por señales** como método principal, con zero-shot solo para casos ambiguos. Esto mantiene la latencia baja (<50ms por ingesta).

---

## 10. Conclusión

El problema no es el motor de búsqueda vectorial, sino la **calidad de los metadatos**. Al agregar una capa de clasificación automática:

1. **Eliminamos el error humano** en la categorización
2. **Pre-filtramos** resultados por dominio antes de la búsqueda vectorial
3. **Aumentamos la precisión** sin cambiar el modelo de embeddings
4. **Reducimos el ruido** - contenido irrelevante ni siquiera es considerado

La clasificación ocurre **una sola vez** al subir el archivo, por lo que el costo computacional es aceptable incluso en CPU.
