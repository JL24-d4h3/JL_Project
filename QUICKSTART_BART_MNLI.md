# QUICKSTART: Activar Clasificación Automática BART-MNLI

## TL;DR

```bash
# 1. Re-indexar todo el contenido con BART-MNLI
python3 reindex_with_classification.py

# 2. (Opcional) Verificar que funciona
python3 test_search_with_filtering.py

# 3. Hecho. Las búsquedas ahora filtran por dominio automáticamente.
```

---

## ¿Qué va a pasar?

### Antes de ejecutar:
- Búsqueda de "visión artificial" podría devolver "SIMULADOR DE PETICIONES" ✗
- Contenido indexado sin clasificación automática BART-MNLI

### Después de ejecutar:
- Búsqueda de "visión artificial" solo devuelve contenido AI/computer_vision ✓
- Todo contenido reclasificado con BART-MNLI
- Filtrados activados (`WHERE auto_domain = ...`)

---

## Paso a Paso

### 1. Re-indexación (5-10 minutos)

```bash
cd /home/jleon/2026/PUCP/GTR/CDN

# Ejecutar re-indexación
python3 reindex_with_classification.py

# Verás output como:
# ======================================================================
# INICIANDO RE-INDEXACIÓN CON BART-MNLI
# ======================================================================
# Encontrados 42 content_id únicos para re-indexar
# 
# [1/42] Re-indexando: content-abc123
#   ✓ Re-indexados 5 chunks
# [2/42] Re-indexando: content-abc124
#   ✓ Re-indexados 3 chunks
# ...
# 
# ======================================================================
# RE-INDEXACIÓN COMPLETADA
#   Exitosos: 42/42
#   Fallidos:  0/42
# ======================================================================
```

**Qué está pasando internamente:**
1. Conecta a ChromaDB (archivo: `/home/jleon/2026/PUCP/GTR/CDN/chromadb/`)
2. Lee todos los `content_id` únicos de los chunks indexados
3. Para cada uno:
   - Obtiene metadata del CDN backend
   - Descarga el archivo original
   - Extrae texto y código
   - **CLASIFICA CON BART-MNLI** ← Nuevo
   - Re-indexa en ChromaDB con `auto_domain`, `auto_area`, `auto_confidence`

### 2. Verificación (30 segundos)

```bash
python3 test_search_with_filtering.py

# Output esperado:
# ======================================================================
# TEST: Búsqueda con Filtrado por Clasificación
# ======================================================================
# 
# Query: 'visión artificial'
# Clasificación: domain=AI, area=computer_vision, confidence=92%
# Resultados: 5 chunks encontrados
# 
#   1. [AI] U-net (type=pdf, score=0.96)
#   2. [AI] YOLO (type=pdf, score=0.92)
#   3. [AI] Data Augmentation (type=pdf, score=0.91)
#   4. [AI] etc...
#   ✓ Correcto: 'SIMULADOR' está correctamente filtrado
# 
# Query: 'TCP socket MQTT'
# Clasificación: domain=NET, area=networking, confidence=90%
# ...
# ✓ Correcto: 'YOLO' está correctamente filtrado
#
# ======================================================================
# ✓ TODOS LOS TESTS PASARON
# ======================================================================
```

### 3. Verificar en el CDN (opcional)

Una vez que se ejecute la re-indexación, en el CDN frontend:
1. Busca "visión artificial"
2. Verifica que NO aparece "SIMULADOR DE PETICIONES"
3. Solo aparecen resultados de computer vision

---

## Instalación de Dependencias (si es necesario)

BART-MNLI se descargará automáticamente en `~/.cache/huggingface/`:

```bash
# Primera ejecución: descarga ~1.5 GB (una sola vez)
# Siguientes ejecuciones: carga desde caché (~instantáneo)

# Si hay problemas, actualizar transformers:
pip install --upgrade transformers==4.41.0
```

---

## Solución de Problemas

### "Error: ChromaDB no encontrado"
```bash
# Verificar que el path es correcto:
ls -la /home/jleon/2026/PUCP/GTR/CDN/chromadb/

# Si no existe, la indexación anterior falló. Revisar logs.
```

### "Error: No hay content_id para re-indexar"
```bash
# ChromaDB está vacío. Primero debe indexarse contenido:
# - Subir archivos al CDN
# - Esto dispara ingest_content() automáticamente
# - Entonces ejecutar reindex_with_classification.py
```

### "BART-MNLI tarda muchísimo"
```bash
# Primera ejecución: puede tardar 5-10 minutos (descarga modelo)
# Siguientes ejecuciones: 30-60 segundos (desde caché)

# Si aún tarda, posible problema de red. Verificar:
# - Conexión a internet (para descargar modelo)
# - Espacio en disco (~2 GB para caché)
```

### "Test dice que 'SIMULADOR' todavía aparece"
```bash
# El contenido antiguo no fue re-indexado. Ejecutar:
python3 reindex_with_classification.py

# Luego verificar de nuevo:
python3 test_search_with_filtering.py
```

---

## Cómo Funciona Internamente

```
┌─────────────────────────────────────────────────────────────┐
│ Usuario busca: "visión artificial"                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────┐
         │ 1. Clasificar Query (rápido)   │
         │    ↓                           │
         │    classify_query(query)       │
         │    ↓ Output:                   │
         │    domain=AI                   │
         │    area=computer_vision        │
         │    confidence=0.92             │
         └─────────────┬──────────────────┘
                       │
         ┌─────────────▼──────────────────────────┐
         │ 2. Generar Filtro WHERE (ChromaDB)     │
         │    ↓                                   │
         │    if confidence >= 0.6:              │
         │      where = {auto_domain: "AI"}      │
         └─────────────┬──────────────────────────┘
                       │
         ┌─────────────▼───────────────────────────────────────┐
         │ 3. Búsqueda Vectorial en ChromaDB                  │
         │    ↓                                                │
         │    collection.query(                               │
         │      embeddings=[...],                             │
         │      where={auto_domain: "AI"}  ← FILTRO ACTIVO   │
         │    )                                               │
         │    ↓ Resultado: Solo chunks donde auto_domain="AI"│
         │    ✓ SIMULADOR (auto_domain="NET") descartado    │
         └─────────────┬───────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────┐
         │ 4. BM25 + Cross-Encoder        │
         │    (en subset ya filtrado)     │
         └─────────────┬──────────────────┘
                       │
         ┌─────────────▼──────────────────┐
         │ Resultados Finales:            │
         │  - YOLO                        │
         │  - U-net                       │
         │  - Data Augmentation           │
         │  (solo AI/computer_vision)     │
         └──────────────────────────────────┘
```

---

## ¿Qué se Clasificará?

Después de re-indexar, el sistema clasificará automáticamente:

| Dominio | Área | Ejemplos |
|---------|------|----------|
| **AI** | computer_vision | YOLO, U-net, cv2, Image detection |
| | nlp | Transformers, BERT, Tokenization |
| | deep_learning | PyTorch, TensorFlow, Neural networks |
| | ml_general | Sklearn, XGBoost, Classification |
| **NET** | networking | MQTT, sockets, TCP/IP, requests |
| | distributed | Distributed systems |
| **DB** | sql | PostgreSQL, MySQL, SQL queries |
| | nosql | MongoDB, Redis |
| **CS** | algorithms | Big O, data structures |
| **SE** | architecture | Design patterns, microservices |
| **WEB** | frontend | React, Vue, HTML/CSS |
| | backend | FastAPI, Node.js, APIs |
| **SYS** | containers | Docker, Kubernetes |
| | cloud | AWS, GCP, Azure |
| **MATH** | statistics | Probability, distributions |

---

## Monitoreo en Producción

### Logs a revisar:

```bash
# Mientras se ejecuta reindex_with_classification.py:
tail -f reindex_with_classification.py  # Ver progreso

# En el CDN/servidor:
# - Ver que nuevos chunks tienen auto_domain correcto
# - Ver que búsquedas en hybrid_retriever.py aplican where_filter
# - Verificar ChromaDB: select * from chunks where auto_domain='AI' limit 5;
```

### Métricas de Éxito:

- ✓ `reindex_with_classification.py` completa sin errores
- ✓ `test_search_with_filtering.py` pasa todos los tests
- ✓ Búsquedas de "visión artificial" no incluyen "SIMULADOR"
- ✓ ChromaDB chunks de AI/NET están separados correctamente

---

## Resumen

| Antes | Después |
|-------|---------|
| Búsquedas ruidosas | Búsquedas filtradas por dominio |
| "SIMULADOR" aparecía en IA | "SIMULADOR" filtrado automáticamente |
| Clasificación manual del usuario | Clasificación automática BART-MNLI |
| Confianza ~70% | Confianza ~90%+ |

---

**¿Preguntas?** Ver [BART_MNLI_IMPLEMENTATION_STATUS.md](BART_MNLI_IMPLEMENTATION_STATUS.md) para detalle técnico.
