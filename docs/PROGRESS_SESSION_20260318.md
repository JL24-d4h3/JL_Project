# Progreso Session 2026-03-18: Clasificación Semántica y Pre-filtrado Adaptativo

**Fecha:** 18 de marzo de 2026  
**Status:** En progreso ⚙️  
**Commit:** `4701b5e` (clean-history)

---

## 🎯 Objetivos Alcanzados

### 1. **Clasificación de Queries con Embeddings Semánticos** ✅
- Reemplazamos keyword-based classification con `multilingual-e5-small` embeddings
- Queries se clasifican generando embedding y comparando similaridad coseno con domain descriptions
- **Ventaja:** Agnóstico del idioma, robusto a typos menores, entiende significado real

```python
# ANTES (hardcoded keywords, frágil):
if "visión" in query.lower() or "imagen" in query.lower():
    domain = "AI"  # Falla con "vison artificial" (typo)

# AHORA (embeddings semánticos, robusto):
query_embedding = embedder.encode(f"query: {query}")
similarity = cosine_similarity(query_embedding, domain_embeddings)
domain = domains[argmax(similarity)]  # Entiende significado
```

**Resultados:**
- "visión artificial" → AI (confidence: 0.85) ✓
- "algoritmo" → AI (confidence: 0.86) ✓
- "tcp socket" → NET (confidence: 0.87) ✓

---

### 2. **Pre-filtrado en ChromaDB** ✅
- Implementado filtro `WHERE auto_domain = query_domain` en búsqueda vectorial
- Solo procesa chunks del dominio correcto
- **Mejora:** Elimina 60-80% de candidatos irrelevantes antes de ranking

```python
query_class = classify_query(query)  # domain=AI, confidence=0.85

where_filter = None
if query_class["confidence"] >= 0.6 and query_class["domain"]:
    where_filter = {"auto_domain": query_class["domain"]}

# ChromaDB solo busca en chunks con auto_domain="AI"
results = collection.query(
    query_embeddings=[...],
    where=where_filter,  # ← Pre-filtrado
    n_results=20
)
```

**Resultado:** "SIMULADOR DE PETICIONES" [NET] filtrado correctamente en búsquedas [AI] ✓

---

### 3. **Pre-filtrado en BM25** ✅
- Bug fix: El filtro de dominio NO se aplicaba a BM25 (keyword search)
- Implementamos mapping `_bm25_metadata` alineado con `_bm25_corpus` (índice → metadata)
- Ahora BM25 también respeta el pre-filtro por dominio

```python
# ANTES (BM25 ignoraba filtro):
for rank, idx in enumerate(top_bm25_idx):
    bm25_items.append({...})  # Todos los resultados BM25

# AHORA (BM25 aplica filtro):
for rank, idx in enumerate(top_bm25_idx):
    corpus_meta = self._bm25_metadata[idx]  # O(1) lookup
    
    if where_filter and corpus_meta:
        if corpus_meta.get("auto_domain") != filter_domain:
            continue  # Saltar si no coincide dominio
    
    bm25_items.append({...})
```

**Resultado:** Fusión RRF (Reciprocal Rank Fusion) ahora combina solo resultados relevantes ✓

---

## ⚠️ Problemas Aún Pendientes

### 1. **Typos y Variaciones Ortográficas** ❌
Queries con caracteres faltantes o permutados fallan:
- "algtimia" (falta 'o') → No reconocido como "algoritmia"
- "simulador d petciones" → No find como "SIMULADOR DE PETICIONES"
- Embedding similarity disminuye drásticamente con typos

**Impacto:** Usuarios escriben mal → sin resultados

---

### 2. **Clasificación de Contenido Incorrecta** ❌
"Algoritmo de Dijkstra" clasificado como `SE` (Software Engineering) cuando debería ser `CS` (Ciencias de la Computación):

```
Chunks existentes:
├── Algoritmo de Dijkstra [SE]  ← INCORRECTO (debería ser CS/algorithms)
├── YOLO [AI]
├── U-net [AI]
└── SIMULADOR DE PETICIONES [NET]

Query: "algoritmia", "algoritmo"
├── Clasificada como: AI (confidence: 0.86)
└── Filtro: WHERE auto_domain="AI"
    └── RESULTADO: Algoritmo Dijkstra NO APARECE (clasificado como SE)
```

**Impacto:** Contenido válido filtrado por mala clasificación inicial

---

### 3. **Queries con Confianza Borderline (0.5-0.6)** ⚠️
Cuando `0.5 <= confidence < 0.6`:
- Threshold actual: `>= 0.6` para aplicar filtro
- Resultado: Sin filtro → búsqueda sin dominio restricción
- Puede mezclar dominios (e.g., NET con AI)

**Impacto:** Resultados inconsistentes dependiendo de umbral

---

### 4. **Sistema No Adaptativo** ❌
Actualmente:
- Si usuario busca "algoritmo" (clasificado como AI) y no encuentra "Algoritmo de Dijkstra" (clasificado como SE)
- Sistema no detecta el conflicto
- Clasificaciones estáticas → sin auto-corrección

**Impacto:** Errores se perpetúan; sin aprendizaje de usuario

---

### 5. **Búsquedas Exactas Retornan Vacío** ❌
Query: "simulador de peticiones" exact match
- ChromaDB búsqueda vectorial con filtro: encuentra nada
- BM25 búsqueda con filtro: encuentra nada
- **Razón:** Ambas búsquedas filtran por dominio de la query
- Si la query no tiene dominio claro, se busca sin filtro
- Pero SIMULADOR está [NET] y query podría interpretarse como [CS] o [OTHER]

**Impacto:** Búsquedas por nombre exacto pueden fallar

---

## 🛠️ Plan de Solución: Arquitectura Adaptativa en 3 Capas

### **Layer 1: Búsqueda Rápida (Actual)** ⚡
**Condiciones:**
- Query clasifica con `confidence >= 0.6`
- Pre-filtro aplicado
- Resultados encontrados (>= 3)

**Acción:** Devolver resultados
**Latencia:** <50ms

```python
if query_confidence >= 0.6 and len(results) >= 3:
    return results  # ✓ Fin
```

---

### **Layer 2: Clasificación Mejorada con Llama 3.2-1B** 🧠
**Condiciones:**
- Confidence baja (`0.3 < confidence < 0.6`)
- O sin resultados encontrados
- O typos detectados

**Acciones:**
1. **Normalización ortográfica:**
   ```python
   query = "algtimia"
   corrected = spell_check(query)  # → "algoritmia"
   ```

2. **Expansión de query:**
   ```python
   query = "algoritmo"
   expanded = ["algoritmia", "algoritmo", "algorithms", "algorithm"]
   # Buscar con todas las variantes
   ```

3. **Re-clasificación con Llama:**
   ```python
   # Llama entiende contexto mejor
   llama_prompt = f"Classifica esta query en dominio: {query}"
   domain = llama_inference(llama_prompt)  # {domain, explanation}
   ```

4. **Query expansion semántica:**
   ```python
   # Llama genera variaciones semanticas
   llama_prompt = f"Dame 3 formas de preguntar sobre: {query}"
   variations = llama_inference(llama_prompt)
   # Ejemplo: "algoritmo" → ["algoritmo dijkstra", "algoritmo grafos", "cs algorithms"]
   ```

**Latencia:** ~200-500ms (Llama es rápido en CPU)

---

### **Layer 3: Búsqueda Sin Filtro (Fallback)** 🔍
**Condiciones:**
- Layer 2 aún sin resultados claros (`confidence < 0.3`)
- O usuario esplícitamente lo solicita

**Acciones:**
1. Desactivar pre-filtro de dominio
2. Buscar en TODO el corpus
3. Devolver resultados etiquetados por dominio:
   ```python
   {
       "query": "simulador",
       "results": [
           {"title": "Simulador de Tráfico", "domain": "WEB", "score": 0.92},
           {"title": "SIMULADOR DE PETICIONES", "domain": "NET", "score": 0.88},
           {"title": "Simulador de ...", "domain": "OTHER", "score": 0.75}
       ],
       "note": "Búsqueda sin filtro por dominio (query ambigua)"
   }
   ```

**Latencia:** <100ms

---

## 📋 Implementación Paso a Paso

### **Semana 1: Layer 2 (Llama Integration)**

#### 1.1 Spell Checker (Día 1)
```python
# ai_engine/services/query_processor.py

from difflib import get_close_matches

def spell_check(query: str, similarity_threshold=0.8) -> Optional[str]:
    """Detectar y corregir typos usando terminología técnica conocida."""
    
    known_terms = [
        "algoritmia", "algoritmo", "visión artificial", "redes",
        "simulador", "peticiones", "tcp", "socket", "yolo", ...
    ]
    
    matches = get_close_matches(query, known_terms, n=1, cutoff=similarity_threshold)
    return matches[0] if matches else None

# Uso:
query = "algtimia"
corrected = spell_check(query)  # "algoritmia"
```

#### 1.2 Query Expansion (Día 1-2)
```python
def expand_query(query: str, expanded_count: int = 3) -> list[str]:
    """Generar variaciones semánticas de la query."""
    
    # Opción A: Template-based (rápido, limitado)
    templates = {
        "algoritmo": ["algoritmia", "algoritmos", "algoritmica"],
        "visión": ["visión artificial", "computer vision", "visión por computadora"],
    }
    
    # Opción B: Llama-based (lento, flexible)
    # prompt = f"Genera 3 formas equivalentes de preguntar: {query}"
    # variations = llama_infer(prompt)
    
    return templates.get(query.lower(), [query])
```

#### 1.3 Llama Integration (Día 2-3)
```python
# ai_engine/services/llm_engine.py

class LlamaClassifier:
    def __init__(self):
        # Llama 3.2-1B ya está en settings
        self.model_dir = settings.DRAFT_MODEL_DIR  # o settings.TARGET_MODEL_DIR
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, device_map="cpu")
    
    def classify_query(self, query: str) -> dict:
        """Clasificar query con Llama."""
        
        prompt = f"""You are a content classifier. Classify this query into one of these categories:
        - AI (Artificial Intelligence, Machine Learning, Computer Vision)
        - CS (Computer Science, Algorithms, Theory)
        - NET (Networking, Protocols, Distributed Systems)
        - DB (Databases, SQL, Storage)
        - SE (Software Engineering, Architecture, Design Patterns)
        - MATH (Mathematics, Statistics, Optimization)
        - WEB (Web Development, Frontend, Backend)
        - SYS (Systems, DevOps, Linux, Containers)
        - OTHER
        
        Query: {query}
        
        Respond with ONLY the category code (e.g., "AI") and confidence 0-100.
        Format: CATEGORY confidence
        """
        
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=5)
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Parse: "AI 95" → {"domain": "AI", "confidence": 0.95}
        
        return self._parse_response(response)
```

---

### **Semana 2: Classification Improvement**

#### 2.1 Auto-Reclassification (Día 1-2)
Cuando se detecta conflicto (búsqueda no encuentra contenido relevante que debería encontrar):

```python
# ai_engine/services/adaptive_classifier.py

async def detect_and_fix_misclassification(
    query: str,
    query_domain: str,
    results: list[dict],
    all_chunks: list[dict]
) -> None:
    """
    Detectar si hay chunks clasificados incorrectamente.
    
    Ejemplo:
    - Query: "algoritmo dijkstra" → domain=AI
    - Chunks relevantes encontrados: 0
    - Todos los chunks: "Algoritmo de Dijkstra" [SE]
    
    → Auto-detect: SE debería ser CS
    → Auto-fix: Reclasificar chunk a CS
    """
    
    if len(results) >= 3:
        return  # Resultados suficientes, no act
    
    # Buscar sin filtro para encontrar chunks potencialmente mal clasificados
    unfiltered_results = await search_without_filter(query, limit=10)
    
    for chunk in unfiltered_results:
        if chunk["domain"] != query_domain:
            # Verificar: ¿debería este chunk estar en query_domain?
            confidence = await llama_verify_classification(
                query=query,
                chunk_text=chunk["text"],
                suggested_domain=query_domain
            )
            
            if confidence > 0.8:
                # Reclasificar
                await update_chunk_classification(
                    chunk_id=chunk["id"],
                    new_domain=query_domain,
                    reason="auto_detected_misclassification"
                )
                logger.info(f"Reclasified {chunk['title']}: {chunk['domain']} → {query_domain}")
```

---

### **Semana 3: Testing & Optimization**

#### 3.1 Tests
```python
# test_adaptive_classification.py

def test_typo_correction():
    """Verificar que typos se corrigen."""
    queries = [
        ("algtimia", "algoritmia"),
        ("vison artifical", "visión artificial"),
        ("simulador d petciones", "simulador de peticiones"),
    ]
    
    for typo, expected in queries:
        corrected = spell_check(typo)
        assert corrected == expected, f"{typo} no se corrigió a {expected}"

def test_layer_switching():
    """Verificar que se cambia de layer correctamente."""
    # Layer 1: high confidence, results found → devuelve resultados
    # Layer 2: low confidence, no results → invoca Llama
    # Layer 3: still no results → sin filtro
```

#### 3.2 Benchmarks
```
Layer 1 (embeddings):     <50ms
Layer 2 (Llama):          200-500ms
Layer 3 (fallback):       <100ms

Total worst-case:         ~700ms (aceptable)
```

---

## 📊 Resultados Esperados

### Antes
```
Query: "algoritmia"
├─ Classification: AI (0.86)
├─ Filtro: WHERE auto_domain="AI"
├─ Resultados: 3 chunks [DATA AUGMENTATION, U-net, YOLO]
└─ Algoritmo Dijkstra: NO APARECE ✗ (clasificado como SE)

Query: "simulador de peticiones"
├─ Search: Sin resultados ✗
└─ Razón: Ambiguo, sin clasificación clara
```

### Después (con 3-layer)
```
Query: "algoritmia"
├─ Layer 1 attempt:
│  ├─ Classification: AI (0.86, >= 0.6) ✓
│  ├─ Filtro: WHERE auto_domain="AI"
│  ├─ Resultados: 3 chunks
│  └─ Sin Algoritmo Dijkstra
│
├─ Trigger Layer 2 (sin resultado esperado):
│  ├─ Llama re-classifies: Maybe CS/algorithms?
│  ├─ Expande query: ["algoritmia", "algoritmo dijkstra", "computer science"]
│  └─ Re-búsqueda con domain=CS
│     └─ ENCONTRADO: Algoritmo Dijkstra [CS] ✓
│
└─ Final resultado: 
   ├─ PRIMARY (AI): [DATA AUGMENTATION, U-net, YOLO]
   └─ RELATED (CS): [Algoritmo Dijkstra]

Query: "simulador de peticiones"
├─ Layer 1: Sin clasificación clara
├─ Layer 2 (Llama): domain=NET, confidence=0.95 ✓
├─ Búsqueda con filtro [NET]:
│  └─ ENCONTRADO: SIMULADOR DE PETICIONES ✓
└─ Final: [1 resultado exacto]
```

---

## 🎓 Aprendizajes & Decisiones Arquitectónicas

1. **Por qué 3 capas:**
   - Optimización: 95% queries rápidas (Layer 1)
   - Robustez: casos complicados resueltos por Llama (Layer 2)
   - Fallback: siempre hay un resultado (Layer 3)

2. **Por qué Llama 3.2-1B:**
   - Disponible localmente (no requiere API)
   - ~1B parámetros = rápido en CPU (~200-500ms)
   - Entiende contexto semántico (typos, variaciones)
   - Puede generar expansiones de query

3. **Por qué mantener embeddings:**
   - Layer 1 es 10x más rápido que Llama
   - Suficiente para la mayoría cases
   - Llama es fallback, no reemplazo

4. **Auto-reclassification:**
   - Aprendizaje desde errores detectados
   - Evita mecanismo manual de corrección
   - Mejora iterativa de la BD

---

## 📝 Next Steps / TODO

- [ ] Implementar `spell_check()` (fácil, 1h)
- [ ] Implementar `expand_query()` (media, 2h)
- [ ] Integrar Llama 3.2-1B (compleja, 4h)
- [ ] Auto-reclassification detector (media, 3h)
- [ ] Tests exhaustivos (media, 3h)
- [ ] Benchmarks y optimización (media, 2h)
- [ ] Documentación de API (fácil, 1h)

**Estimado total:** 1-2 semanas en paralelo mientras subes PDFs/Excels

---

## 🔗 Referencias

- Commit: `4701b5e` - Pre-filtrado en BM25
- Anterior: `auto-classification-IMPLEMENTED.md`
- Propuesta base: `auto-classification-proposal.md`

---

**Autor:** GitHub Copilot  
**Última actualización:** 2026-03-18  
**Status:** Pronto a implementar ⏳
