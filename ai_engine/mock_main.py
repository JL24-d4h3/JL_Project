"""
mock_main.py — Servidor mock del AI Engine para desarrollo en laptop.
Usa datos de ejemplo para L1/L2, y el modelo LLM local para consultas desconocidas (L3 dinámico).
Usar: uvicorn ai_engine.mock_main:app --port 8000 --reload
"""
import asyncio, json, re, os, logging
from difflib import get_close_matches
from pathlib import Path
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

# Cargar .env ANTES de importar settings para que las rutas de modelos sean correctas
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── LLM Engine (carga en background al iniciar) ──────────────────────────────
_llm = None   # instancia de LLMEngine cuando está lista
_retriever = None  # instancia de HybridRetriever cuando está lista

async def _init_llm():
    global _llm
    try:
        from ai_engine.services.llm_engine import LLMEngine
        engine = LLMEngine()
        await engine.init()
        _llm = engine
        logger.info("✓ LLM engine listo — modo: %s", engine._mode)
    except Exception as exc:
        logger.warning("LLM no disponible, usando respuestas de plantilla: %s", exc)

async def _init_retriever():
    global _retriever
    try:
        from ai_engine.services.hybrid_retriever import retriever
        await retriever.init()
        _retriever = retriever
        count = await retriever.chunk_count()
        logger.info("✓ Retriever listo — %d chunks indexados en ChromaDB", count)
    except Exception as exc:
        logger.warning("Retriever no disponible, búsqueda ChromaDB deshabilitada: %s", exc)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Arrancar retriever y LLM en background (no bloquea el servidor)
    asyncio.create_task(_init_retriever())
    asyncio.create_task(_init_llm())
    yield
    # Shutdown
    if _llm is not None and hasattr(_llm, "shutdown"):
        await _llm.shutdown()


app = FastAPI(title="AI Engine — GTR-PUCP", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Servir archivos estáticos del storage local (videos, documentos)
# ---------------------------------------------------------------------------
STORAGE_DIR = Path(__file__).parent.parent / "storage"
if STORAGE_DIR.exists():
    app.mount("/files", StaticFiles(directory=str(STORAGE_DIR)), name="files")


class SearchRequest(BaseModel):
    query: str
    context: dict = {}




# Funciones obsoletas eliminadas (_match, _is_dynamic_query) - ya no se usan desde
# que se eliminaron MOCK_DB y GENERAL_KNOWLEDGE en favor de búsqueda dinámica en ChromaDB


def _build_llm_prompt(query: str) -> str:
    """Formatea el prompt en el formato de chat de Phi-3.5-mini-instruct."""
    system = (
        "Eres un asistente educativo. Responde SIEMPRE en español.\n"
        "REGLAS ESTRICTAS:\n"
        "1. Empieza DIRECTAMENTE con la respuesta — sin saludos, sin '¡Claro!', sin introducirte.\n"
        "2. Nunca menciones plataformas, sistemas, ni te presentes.\n"
        "3. Para TODA matemática usa LaTeX directamente — sin anunciarlo ni decir 'la fórmula es:':\n"
        "   - Inline: $...$ para expresiones dentro del texto\n"
        "   - Bloque: $$...$$ para ecuaciones destacadas\n"
        "   - Fracciones: $\\frac{a}{b}$, raíces: $\\sqrt{x}$, potencias: $x^{n}$\n"
        "   - Integrales: $\\int_a^b f(x)\\,dx$, sumas: $\\sum_{i=0}^{n}$, límites: $\\lim_{x \\to \\infty}$\n"
        "4. Usa Markdown para estructura: ## título principal, ### para cada subsección o concepto,\n"
        "   **negrita** para términos clave, tablas GFM con | para comparaciones.\n"
        "5. Bloques de código ```lenguaje ... ``` solo cuando el usuario pida código o comandos.\n"
        "   NUNCA uses bloques de código para matemáticas ni para mostrar 'ejemplos de formato'.\n"
        "6. En preguntas teóricas: da una explicación completa con secciones bien estructuradas.\n"
        "   No repitas la pregunta. No añadas disclaimers ni notas finales innecesarias."
    )
    return (
        f"<|system|>\n{system}<|end|>\n"
        f"<|user|>\n{query}<|end|>\n"
        f"<|assistant|>\n"
    )


def _extract_core_topic(query: str) -> str:
    """Extrae el núcleo temático eliminando verbos, comparativos y localizaciones."""
    q = re.sub(r'[¿?¡!]', '', query.strip()).lower()

    # 1. Strip pregunta/verbo/comando inicial
    q = re.sub(
        r'^(?:qu[eé]\s+(?:es|son|fue|fueron|significa[n]?|hay(?:\s+(?:en|de))?)|'
        r'c[oó]mo\s+(?:se\s+)?(?:llama[n]?|hace[n]?|calcula[n]?|funciona[n]?|'
        r'usa[n]?|instal(?:a[rn]?|ando)?|implement[ae][r]?|define[n]?|resuelv[ae][n]?)|'
        r'cu[aá]l(?:es)?\s+(?:es|son|fue|son\s+las?|es\s+el)|'
        r'cu[aá]ndo\s+|d[oó]nde\s+|por\s+qu[eé]\s+|'
        r'(?:crea[r]?|escrib[ei][r]?|implement[ae][r]?|hazme|mu[eé]strame|muestrame|'
        r'lista[r]?|dame|dime|explica[r]?|define|menciona[r]?|nombra[r]?|desc(?:ribe|ribir))\s+'
        r'(?:los?\s+|las?\s+|un\s+|una\s+)?)\s*',
        '', q, flags=re.IGNORECASE
    ).strip()

    # 2. Strip localizaciones al final PRIMERO (antes del comparativo)
    q = re.sub(
        r'\s+en\s+(?:el\s+|la\s+)?(?:per[uú]|espa[nñ]a|am[eé]rica|m[eé]xico|'
        r'colombia|argentina|chile|latinoam[eé]rica|europa|mundo|pa[ií]s|regi[oó]n)$',
        '', q, flags=re.IGNORECASE
    ).strip()

    # 3. Strip comparativos/superlativos al final ("más complicada", "mejor pagadas", "mayor complejidad intelectual")
    q = re.sub(
        r'\s+(?:m[aá]s|menos|mayor|menor|mejor|peor)(?:\s+\w+){1,3}$',
        '', q, flags=re.IGNORECASE
    ).strip()

    # 4. Strip preposición solitaria al final
    q = re.sub(r'\s+(?:de|del|en|para|sobre|con|entre)\s*$', '', q, flags=re.IGNORECASE).strip()

    # 5. Strip artículo inicial
    q = re.sub(r'^(?:los?\s+|las?\s+|un\s+|una\s+)', '', q).strip()

    # 6. Strip "como/cómo" huérfano al inicio (no consumido por el patrón de verbos)
    q = re.sub(r'^c[oó]mo\s+', '', q, flags=re.IGNORECASE).strip()

    return q.capitalize() if q else query.strip().capitalize()


def _generate_suggestions(query: str) -> list[str]:
    """Genera búsquedas relacionadas dinámicamente a partir de la query."""
    q_lower = query.strip().lower()
    topic = _extract_core_topic(query)
    topic_cap = topic  # ya capitalizado por _extract_core_topic

    is_math = any(w in q_lower for w in [
        'integral', 'derivada', 'fracción', 'fraccion', 'ecuación', 'ecuacion',
        'transformada', 'laplace', 'fourier', 'limite', 'límite', 'matriz', 'vector',
        'probabilidad', 'estadística', 'estadistica', 'multiplicar', 'dividir', 'sumar',
    ])
    is_code = any(w in q_lower for w in [
        'código', 'codigo', 'programa', 'algoritmo', 'implementa', 'función', 'funcion',
        'clase', 'script', 'rust', 'python', 'java', 'javascript', 'typescript',
    ])
    is_how = any(w in q_lower for w in [
        'cómo', 'como', 'pasos', 'procedimiento', 'proceso', 'método', 'metodo',
    ])

    if is_math:
        return [
            f"Propiedades de {topic_cap}",
            f"Ejercicios resueltos de {topic_cap}",
            f"Aplicaciones de {topic_cap} en ingeniería",
            f"Historia y origen de {topic_cap}",
        ]
    if is_code:
        lang_match = re.search(
            r'\b(rust|python|java|javascript|typescript|c\+\+|kotlin|go|swift)\b', q_lower
        )
        lang = lang_match.group(1).capitalize() if lang_match else 'Python'
        return [
            f"Estructuras de datos en {lang}",
            f"Pruebas unitarias en {lang}",
            f"Patrones de diseño en {lang}",
            f"Complejidad algorítmica en {lang}",
        ]
    if is_how:
        return [
            f"¿Qué es {topic_cap}?",
            f"Ventajas y desventajas de {topic_cap}",
            f"Errores comunes con {topic_cap}",
            f"Guía completa de {topic_cap}",
        ]
    # General: plantillas neutrales que siempre tienen sentido gramatical
    return [
        f"Introducción a {topic_cap}",
        f"Historia de {topic_cap}",
        f"Tipos de {topic_cap}",
        f"Aplicaciones de {topic_cap}",
    ]


def _build_suggest_prompt(query: str) -> str:
    """Prompt para generar 4 búsquedas relacionadas con variedad real."""
    q_lower = query.lower()

    # Detectar si es consulta de código con lenguaje específico
    lang_match = re.search(
        r'\b(rust|python|java|javascript|typescript|c\+\+|kotlin|go|swift|c#|php|ruby)\b',
        q_lower
    )
    other_langs = []
    if lang_match:
        lang = lang_match.group(1)
        pool = ["Python", "Java", "JavaScript", "Rust", "C++", "Kotlin", "Go"]
        other_langs = [l for l in pool if l.lower() != lang.lower()][:2]

    if lang_match and other_langs:
        diversity_hint = (
            f"La consulta es sobre programación en {lang_match.group(1)}. "
            f"Genera sugerencias VARIADAS siguiendo este esquema:\n"
            f"1. El mismo tema pero en {other_langs[0]}\n"
            f"2. El mismo tema pero en {other_langs[1]}\n"  
            f"3. Una pregunta conceptual sobre el tema (¿qué es...? / definición / teoría)\n"
            f"4. Una aplicación práctica o caso de uso real del tema\n"
        )
    else:
        diversity_hint = (
            "Genera sugerencias VARIADAS siguiendo este esquema:\n"
            "1. Un concepto relacionado o prerrequisito del tema\n"
            "2. Una aplicación o uso práctico del tema\n"
            "3. Una comparación con algo similar (vs, diferencia entre...)\n"
            "4. Profundizar en un aspecto específico del tema\n"
        )

    return (
        f"<|system|>\n"
        f"Eres un motor de búsqueda educativo. Genera exactamente 4 búsquedas relacionadas.\n"
        f"{diversity_hint}"
        f"FORMATO OBLIGATORIO:\n"
        f"- Exactamente 4 líneas, una búsqueda por línea\n"
        f"- Máximo 7 palabras por línea\n"
        f"- Sin numeración, sin viñetas, sin explicaciones\n"
        f"- Solo las 4 frases, nada más\n"
        f"<|end|>\n"
        f"<|user|>\n"
        f"Consulta: {query}\n"
        f"<|end|>\n"
        f"<|assistant|>\n"
    )


async def _llm_suggestions(query: str) -> list[str]:
    """Genera sugerencias con el LLM. Fallback a plantillas si falla."""
    if _llm is None or not _llm.is_ready:
        return _generate_suggestions(query)
    try:
        prompt = _build_suggest_prompt(query)
        tokens: list[str] = []
        newline_count = 0
        async for chunk in _llm.generate_stream(prompt):  # type: ignore
            tokens.append(chunk)
            newline_count += chunk.count("\n")
            if newline_count >= 8:  # más que suficiente para 4 sugerencias
                break
        raw = "".join(tokens)
        lines = [
            re.sub(r'^[\d\.\-\*\•\)\s]+', '', ln).strip()
            for ln in raw.splitlines()
            if ln.strip()
        ]
        valid = [ln for ln in lines if 4 < len(ln) <= 80][:4]
        if len(valid) >= 2:
            return valid
    except Exception as exc:
        logger.warning("LLM suggestions fallback por error: %s", exc)
    return _generate_suggestions(query)


# ── DOMINIOS TEMÁTICOS para búsqueda CDN relacionada ─────────────────────────
_DOMAIN_SETS: list[set] = [
    # Matemáticas / Señales
    {"fourier", "transformada", "señal", "frecuencia", "espectro", "fft", "dft",
     "derivada", "integral", "cálculo", "calculo", "límite", "limite", "diferencial",
     "integración", "taylor", "laplace", "serie", "ecuacion", "ecuación", "álgebra"},
    # Redes
    {"red", "redes", "tcp", "ip", "lan", "wan", "protocolo", "cisco",
     "ethernet", "router", "socket", "subnet", "dns", "http"},
    # Programación
    {"python", "javascript", "java", "rust", "programación", "programacion",
     "algoritmo", "recursion", "poo", "oop", "typescript", "kotlin"},
    # Seguridad / Linux
    {"linux", "kali", "ubuntu", "pentest", "bash", "ciberseguridad",
     "hacking", "ransomware", "cifrado", "malware"},
    # IA / ML
    {"deep", "learning", "machine", "neural", "sklearn", "clasificación",
     "regresión", "clustering"},
]


def _strip_accents(text: str) -> str:
    """Elimina acentos/diacríticos de texto para comparación normalizada."""
    import unicodedata
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _classify_query_by_keywords(query: str, keyword_signals: dict) -> tuple[str | None, str | None]:
    """
    Clasificación simple de query por keywords (fallback cuando sklearn no está disponible).
    Normaliza acentos para que "vision" matchee "visión".
    Retorna (domain, area) o (None, None) si no hay match claro.
    """
    # Normalizar query: minúsculas + sin acentos
    query_norm = _strip_accents(query.lower())
    from collections import Counter
    scores: Counter = Counter()

    for keyword, (domain, area, weight) in keyword_signals.items():
        # Normalizar keyword también
        keyword_norm = _strip_accents(keyword.lower())
        if keyword_norm in query_norm:
            scores[(domain, area)] += weight

    if not scores:
        return None, None

    best = scores.most_common(1)[0]
    (domain, area), weight = best
    # Solo retornar si tiene un match claro (peso >= 2.0)
    if weight >= 2.0:
        return domain, area
    return None, None


async def _search_cdn(query: str) -> list[dict]:
    """Busca contenido real indexado en ChromaDB. Retorna [] si no hay resultados."""
    try:
        # Acceder directamente al singleton retriever (más robusto que usar _retriever global)
        from ai_engine.services.hybrid_retriever import retriever
        from ai_engine.services.classifier import classify_query, KEYWORD_SIGNALS

        # Lazy initialization: si no está listo, inicializarlo ahora
        if not retriever.is_ready:
            logger.info("Retriever no inicializado, inicializando ahora...")
            await retriever.init()
            logger.info("Retriever inicializado: %d chunks", await retriever.chunk_count())

        chunks = await retriever.search(query, top_k=15)
        if not chunks:
            logger.debug("ChromaDB: 0 resultados para '%s'", query[:50])
            return []

        # Clasificar la query por dominio
        # Primero intentar clasificador semántico, si falla usar keywords
        query_classification = classify_query(query)
        query_domain = query_classification.get("domain")
        query_area = query_classification.get("area")

        # Fallback a keywords si el clasificador semántico no funcionó
        if not query_domain:
            query_domain, query_area = _classify_query_by_keywords(query, KEYWORD_SIGNALS)

        logger.debug("Query '%s' clasificado como: %s/%s", query[:30], query_domain, query_area)

        # Convertir chunks del retriever al formato de tarjetas CDN
        seen: dict[str, dict] = {}
        query_norm = query.lower().strip()
        query_tokens = set(query_norm.split())

        for chunk in chunks:
            cid = chunk.get("content_id", "")
            score = float(chunk.get("score", 0.0))
            title = chunk.get("title", "").lower()
            text = chunk.get("text", "").lower()
            full_text = f"{title} {text}"

            # FILTRO 1: Threshold mínimo (ChromaDB ya hizo el trabajo semántico)
            min_score = 0.15
            if score < min_score:
                continue

            # La mayoría de chunks que pasan 0.15 son relevantes
            # Domain matching es para BOOST, no para rechazo
            full_text_norm = _strip_accents(full_text)

            # Detectar dominio del chunk (para boosting)
            chunk_domain = None
            for keyword, (domain, area, weight) in KEYWORD_SIGNALS.items():
                keyword_norm = _strip_accents(keyword.lower())
                if keyword_norm in full_text_norm and weight >= 2.0:
                    chunk_domain = domain
                    break

            # BOOST: Si la query tiene dominio específico y el chunk pertenece al mismo dominio
            if query_domain and chunk_domain == query_domain:
                score *= 1.25  # Boost significativo para domain match

                # Extra boost si además es la misma área (computer_vision)
                if query_area:
                    for keyword, (domain, area, _w) in KEYWORD_SIGNALS.items():
                        kw_norm = _strip_accents(keyword.lower())
                        if kw_norm in full_text_norm and domain == query_domain and area == query_area:
                            score *= 1.15
                            break

            if cid not in seen or score > seen[cid].get("relevance_score", 0):
                ctype = chunk.get("content_type", "document")
                ts = chunk.get("timestamp_start")
                viewer_suffix = f"?t={ts:.0f}" if ts is not None else ""
                viewer_base = f"/viewer/{'video' if ctype == 'video' else 'document'}/{cid}"
                seen[cid] = {
                    "content_id":      cid,
                    "content_type":    ctype,
                    "title":           chunk.get("title", ""),
                    "snippet":         chunk.get("text", "")[:200],
                    "thumbnail_url":   f"/storage/thumbnails/{cid}.jpg",
                    "viewer_url":      viewer_base + viewer_suffix,
                    "relevance_score": round(score, 4),
                }
        cards = sorted(seen.values(), key=lambda c: c["relevance_score"], reverse=True)

        # Tomar los top 5 resultados
        cards = cards[:5]

        logger.info("ChromaDB search: %d chunks → %d cards para '%s' (query_domain=%s)",
                    len(chunks), len(cards), query[:50], query_domain)
        return cards
    except Exception as exc:
        logger.warning("ChromaDB search falló: %s", exc)
        return []


def _generate_overview_from_results(query: str, cards: list[dict]) -> str:
    """
    Genera un overview DINÁMICO basado en los resultados REALES de ChromaDB.
    NO usa plantillas hardcodeadas - todo el contenido viene de los chunks indexados.
    """
    if not cards:
        return f"No se encontraron recursos relacionados con **{query}** en el sistema."

    # Agrupar por tipo de contenido
    by_type: dict[str, list] = {}
    for card in cards:
        ctype = card.get("content_type", "document")
        if ctype not in by_type:
            by_type[ctype] = []
        by_type[ctype].append(card)

    # Generar overview basado en contenido real
    lines = [f"## Recursos encontrados para: {query}\n"]

    type_names = {
        "video": "Videos",
        "pdf": "Documentos PDF",
        "audio": "Audio",
        "code": "Código fuente",
        "document": "Documentos",
    }

    for ctype, items in by_type.items():
        type_label = type_names.get(ctype, ctype.capitalize())
        lines.append(f"\n### {type_label} ({len(items)})\n")

        for item in items[:3]:  # Mostrar máximo 3 por tipo
            title = item.get("title", "Sin título")
            snippet = item.get("snippet", "")
            score = item.get("relevance_score", 0)

            # Limpiar título si es un hash
            if len(title) > 40 and " " not in title:
                title = f"Recurso {ctype}"

            lines.append(f"- **{title}** (relevancia: {score:.0%})")
            if snippet and len(snippet) > 20:
                # Mostrar snippet truncado
                snippet_clean = snippet[:150].replace("\n", " ").strip()
                if snippet_clean:
                    lines.append(f"  > {snippet_clean}...")

    lines.append(f"\n---\n*Contenido indexado del servidor local.*")

    return "\n".join(lines)


# ── CORRECCIÓN ORTOGRÁFICA ──────────────────────────────────────────────────
# Diccionario de términos conocidos (tecnología, ciencia, cultura)
_SPELL_DICT: list[str] = [
    "python", "javascript", "typescript", "java", "rust", "kotlin", "swift", "golang",
    "programación", "algoritmo", "función", "variable", "bucle", "clase", "objeto",
    "inteligencia artificial", "machine learning", "deep learning", "red neuronal",
    "transformada de fourier", "cálculo diferencial", "álgebra lineal", "física",
    "matemáticas", "biología", "química", "historia", "geografía", "literatura",
    "redes", "tcp ip", "protocolo", "servidor", "cliente", "base de datos", "sql",
    "linux", "ubuntu", "windows", "macos", "sistema operativo",
    "ransomware", "malware", "virus", "ciberseguridad", "hacking", "cifrado",
    "lionel messi", "fútbol", "baloncesto", "tenis", "deporte",
    "perú", "lima", "cusco", "inca", "historia del perú",
    "neurona", "perceptrón", "regresión", "clasificación", "clustering",
    "react", "vue", "angular", "django", "fastapi", "spring", "nodejs",
    "docker", "kubernetes", "devops", "git", "github",
    "electrónica", "circuito", "microcontrolador", "arduino", "raspberry",
]


# Candidatos para spell-check: SOLO entradas de una sola palabra del diccionario.
# Nunca fragmentar frases multi-palabra ("sistema operativo" → no generar "sistema", "operativo")
_SPELL_CANDIDATES: list[str] = [
    w for w in _SPELL_DICT if " " not in w and len(w) >= 3
]

# Errores comunes que el fuzzy matching no captura bien (sustituciones fonéticas)
_COMMON_TYPOS: dict[str, str] = {
    "yava": "java", "jaba": "java", "jiva": "java", "yava": "java",
    "pyton": "python", "pithon": "python", "piton": "python",
    "javasript": "javascript", "javascipt": "javascript", "javscript": "javascript",
    "tipescript": "typescript", "typescipt": "typescript",
    "reac": "react", "raect": "react",
    "angylar": "angular", "angulr": "angular",
    "djangoo": "django", "djnago": "django",
    "githb": "github", "gitub": "github",
    "dokcer": "docker", "dcoker": "docker",
    "kubernets": "kubernetes", "kubernetis": "kubernetes",
    "matematicas": "matemáticas", "matematica": "matemáticas",
    "fisica": "física", "quimica": "química", "biologia": "biología",
    "programacion": "programación", "prgrmacion": "programación",
    "algoritmo": "algoritmo",  # sin tilde ya es correcto
}


def _normalize(s: str) -> str:
    """Elimina tildes para comparación fonética."""
    return s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')


def _spell_check(query: str) -> str | None:
    """
    Detecta errores tipográficos obvios token a token.
    Solo sugiere corrección si el token no existe en el diccionario Y
    tiene una coincidencia clara (cutoff alto) con un término técnico conocido.
    Devuelve la query corregida o None si no hay sugerencia.
    """
    q_lower = query.lower().strip()
    tokens = re.split(r"\s+", q_lower)
    if len(tokens) > 6:
        return None  # Consultas largas: no corregir para evitar falsos positivos

    # Palabras comunes españolas que no deben corregirse (stopwords básicas)
    _STOPWORDS = {
        "de", "la", "el", "los", "las", "en", "un", "una", "es", "son",
        "qué", "que", "cómo", "como", "cuál", "cual", "por", "para",
        "con", "sin", "del", "al", "se", "mi", "tu", "su", "me",
        "hay", "era", "fue", "han", "has", "una", "este", "esta",
        "entre", "sobre", "también", "cuando", "donde", "porque",
        # Palabras comunes que podrían causar falsos positivos:
        "sistemas", "operativo", "operativos", "redes", "datos", "tipo",
        "tipos", "proceso", "procesos", "modelo", "modelos", "nivel",
    }

    corrections: dict[str, str] = {}
    all_candidate_words = set(_SPELL_CANDIDATES)
    # Candidatos normalizados (sin tildes) para mejor comparación fonética
    norm_candidates = [(_normalize(w), w) for w in _SPELL_CANDIDATES]
    norm_words_only = [nc[0] for nc in norm_candidates]

    for token in tokens:
        if len(token) < 4:
            continue
        if token in _STOPWORDS:
            continue
        # Comprobar primero el diccionario de errores comunes
        if token in _COMMON_TYPOS:
            corrections[token] = _COMMON_TYPOS[token]
            continue
        if token in all_candidate_words:
            continue
        # Comparar versión normalizada del token contra candidatos normalizados
        norm_token = _normalize(token)
        if norm_token in norm_words_only:
            # El token es simplemente la versión sin tilde de una palabra correcta → no corregir
            continue
        matches = get_close_matches(norm_token, norm_words_only, n=1, cutoff=0.78)
        if matches and matches[0] != norm_token:
            # Recuperar la palabra original con tildes
            original = next((orig for norm, orig in norm_candidates if norm == matches[0]), matches[0])
            corrections[token] = original

    if not corrections:
        return None

    corrected = q_lower
    for wrong, right in corrections.items():
        corrected = re.sub(r'\b' + re.escape(wrong) + r'\b', right, corrected)

    if corrected.strip().lower() == q_lower:
        return None
    return corrected.strip()


@app.post("/api/search")
async def search(req: SearchRequest):
    cdn_cards = await _search_cdn(req.query)
    spell = _spell_check(req.query)
    overview_text = _generate_overview_from_results(req.query, cdn_cards)
    level = "L2" if cdn_cards else "L4"
    suggestions = [
        f"{req.query} tutorial",
        f"{req.query} ejemplos",
        f"cómo funciona {req.query}",
    ] if cdn_cards else []
    return {
        "query": req.query,
        "spell_suggestion": spell,
        "cdn_results": cdn_cards,
        "ai_overview": {
            "text": overview_text, "level": level,
            "grounding": {"coverage_score": 0.9 if cdn_cards else 0.0, "is_grounded": bool(cdn_cards)},
            "language_detected": "es",
        },
        "ui_hints": {"suggested_queries": suggestions},
    }


@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    spell = _spell_check(req.query)
    # Solo usar LLM si está disponible Y tiene un modelo real (no placeholder)
    use_llm = _llm is not None and _llm.is_ready and _llm._mode != "none"

    if use_llm:
        # ── MODO LLM: respuesta generada por Llama 3.2 ────────────────────────────
        prompt = _build_llm_prompt(req.query)
        logger.info("LLM generando respuesta para: %s", req.query)

        async def llm_event_generator():
            cdn_cards = await _search_cdn(req.query)
            yield f"data: {json.dumps({'type': 'cdn_results', 'data': cdn_cards})}\n\n"
            await asyncio.sleep(0.1)
            try:
                async for chunk in _llm.generate_stream(prompt):  # type: ignore
                    yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            except Exception as exc:
                logger.error("Error en LLM stream: %s", exc)
                # Si el LLM falla, usar contenido real de ChromaDB como fallback
                fallback_text = _generate_overview_from_results(req.query, cdn_cards)
                for line in fallback_text.split("\n"):
                    yield f"data: {json.dumps({'type': 'token', 'text': line + chr(10)})}\n\n"
                    await asyncio.sleep(0.02)
            suggestions = await _llm_suggestions(req.query)
            yield f"data: {json.dumps({'type': 'done', 'level': 'L3', 'grounding': {'coverage_score': 0.0}, 'suggestions': suggestions, 'spell_suggestion': spell})}\n\n"

        return StreamingResponse(
            llm_event_generator(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    else:
        # ── MODO DINÁMICO: respuesta basada en contenido REAL de ChromaDB ────────────
        # Tarjetas CDN: siempre desde ChromaDB (contenido real indexado)
        cdn_cards = await _search_cdn(req.query)

        # Generar overview DINÁMICO basado en resultados reales (NO plantillas)
        overview_text = _generate_overview_from_results(req.query, cdn_cards)
        lines = overview_text.split("\n")

        # Nivel basado en si hay resultados
        level = "L2" if cdn_cards else "L4"

        # Sugerencias simples basadas en la query (no hardcodeadas)
        suggestions = [
            f"{req.query} tutorial",
            f"{req.query} ejemplos",
            f"cómo funciona {req.query}",
        ] if cdn_cards else []

        async def dynamic_event_generator():
            yield f"data: {json.dumps({'type': 'cdn_results', 'data': cdn_cards})}\n\n"
            await asyncio.sleep(0.1)
            for line in lines:
                yield f"data: {json.dumps({'type': 'token', 'text': line + chr(10)})}\n\n"
                await asyncio.sleep(0.02)
            yield f"data: {json.dumps({'type': 'done', 'level': level, 'grounding': {'coverage_score': 0.9 if cdn_cards else 0.0}, 'suggestions': suggestions, 'spell_suggestion': spell})}\n\n"

        return StreamingResponse(
            dynamic_event_generator(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )


@app.post("/api/voice-search")
async def voice_search():
    """Endpoint placeholder para búsqueda por voz (no implementado)."""
    return {
        "query_transcribed": "¿Qué es la Transformada de Fourier?",
        "cdn_results": [],
        "ai_overview": {"text": "Búsqueda por voz no implementada aún.", "level": "L0"},
    }


@app.post("/api/ingest")
async def ingest(body: dict = {}):
    content_id = body.get("content_id", "")
    if not content_id:
        return {"status": "error", "error": "content_id requerido"}

    # Usar el pipeline de ingesta real (extrae texto, genera chunks, indexa en ChromaDB)
    async def _run():
        try:
            from ai_engine.services.ingestion.pipeline import ingest_content
            result = await ingest_content(content_id)
            logger.info("[INGEST] content_id=%s completado: %s chunks", content_id, result.get("chunks_added", 0))
        except Exception as exc:
            logger.error("[INGEST] content_id=%s falló: %s", content_id, exc)

    asyncio.create_task(_run())
    return {"status": "queued", "content_id": content_id}
