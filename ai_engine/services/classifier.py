"""
services/classifier.py — Clasificación Automática de Contenido
GTR-PUCP CDN Educativa Offline

Clasifica contenido técnico por dominio y área usando:
1. Pipeline Híbrido (SEÑALES + BART-MNLI)
   - Fase 1: Análisis rápido por importes, keywords, patrones
   - Fase 2: Zero-Shot con BART-MNLI si confianza < 0.65 (fallback semántico)

El sistema elimina la dependencia de clasificación manual del usuario,
mejora la precisión de búsqueda filtrada, y evita falsos positivos
(ej: "SIMULADOR DE PETICIONES" no aparece en búsquedas de "visión artificial").

Pipeline:
  1. Extrae señales del código (imports, funciones) ← Rápido (<50ms)
  2. Analiza texto por keywords técnicos
  3. Calcula confianza inicial
  4. Si confidence < 0.65 → BART-MNLI para validación/mejora (~500ms)
  5. Retorna clasificación final + confianza
"""
from __future__ import annotations
import re
import logging
import json
import time
import unicodedata
from collections import Counter
from typing import Optional
from pathlib import Path
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Singleton para BART-MNLI (lazy loading)
_BART_CLASSIFIER = None
_BART_LOADED = False
_QUERY_EMBEDDER = None
_USER_TYPO_CACHE: dict[str, str] = {}
_USER_TYPO_MTIME: float = 0.0
_USER_TYPO_LAST_CHECK: float = 0.0

_ADAPTIVE_FEEDBACK_PATH = Path(__file__).parent.parent / "calibration" / "query_feedback.jsonl"

_COMMON_QUERY_TYPOS = {
    "algtimia": "algoritmia",
    "algortimo": "algoritmo",
    "algorimto": "algoritmo",
    "simlador": "simulador",
    "petciones": "peticiones",
    "peticione": "peticiones",
    "artifical": "artificial",
    "vison": "vision",
}

_QUERY_TECH_TERMS = {
    "tic", "tics", "gtics", "sdn", "algoritmo", "algoritmia", "dijkstra",
    "simulador", "peticiones", "redes", "software", "vision", "artificial",
    "yolo", "unet", "u-net", "tcp", "socket", "machine", "learning",
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _load_query_embedder():
    global _QUERY_EMBEDDER
    if _QUERY_EMBEDDER is not None:
        return _QUERY_EMBEDDER

    from sentence_transformers import SentenceTransformer
    try:
        _QUERY_EMBEDDER = SentenceTransformer(
            "intfloat/multilingual-e5-small",
            cache_folder=str(Path(__file__).parent.parent.parent / ".cache"),
        )
    except Exception:
        _QUERY_EMBEDDER = SentenceTransformer("intfloat/multilingual-e5-small")
    return _QUERY_EMBEDDER


def _load_user_typo_map() -> dict[str, str]:
    global _USER_TYPO_CACHE, _USER_TYPO_MTIME, _USER_TYPO_LAST_CHECK
    now = time.time()
    if now - _USER_TYPO_LAST_CHECK < 10:
        return _USER_TYPO_CACHE
    _USER_TYPO_LAST_CHECK = now

    try:
        if not _ADAPTIVE_FEEDBACK_PATH.exists():
            return _USER_TYPO_CACHE

        mtime = _ADAPTIVE_FEEDBACK_PATH.stat().st_mtime
        if mtime <= _USER_TYPO_MTIME:
            return _USER_TYPO_CACHE

        loaded: dict[str, str] = {}
        with _ADAPTIVE_FEEDBACK_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get("event_type") != "query_correction":
                    continue
                original = str(event.get("query", "")).strip().lower()
                corrected = str(event.get("corrected_query", "")).strip().lower()
                if original and corrected and original != corrected:
                    loaded[_strip_accents(original)] = _strip_accents(corrected)

        _USER_TYPO_CACHE = loaded
        _USER_TYPO_MTIME = mtime
    except Exception as exc:
        logger.debug("No se pudo cargar typo map adaptativo: %s", exc)

    return _USER_TYPO_CACHE


def preprocess_query_text(query: str) -> dict:
    raw = (query or "").strip()
    lowered = raw.lower()
    normalized = _strip_accents(lowered)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    user_typos = _load_user_typo_map()
    if normalized in user_typos:
        corrected = user_typos[normalized]
        return {
            "original": raw,
            "normalized": normalized,
            "corrected": corrected,
            "used_correction": corrected != normalized,
            "source": "adaptive_feedback",
        }

    tokens = normalized.split()
    corrected_tokens = []
    changed = False
    vocabulary = set(_QUERY_TECH_TERMS)
    vocabulary.update(_strip_accents(k) for k in KEYWORD_SIGNALS.keys())
    vocabulary.update(_strip_accents(v) for v in DOMAINS.values())

    for tok in tokens:
        if tok in _COMMON_QUERY_TYPOS:
            corrected_tokens.append(_COMMON_QUERY_TYPOS[tok])
            changed = True
            continue

        if len(tok) <= 3 or tok in vocabulary:
            corrected_tokens.append(tok)
            continue

        match = get_close_matches(tok, list(vocabulary), n=1, cutoff=0.86)
        if match and match[0] != tok:
            corrected_tokens.append(match[0])
            changed = True
        else:
            corrected_tokens.append(tok)

    corrected = " ".join(corrected_tokens).strip()
    return {
        "original": raw,
        "normalized": normalized,
        "corrected": corrected,
        "used_correction": changed and corrected != normalized,
        "source": "static_typo_map" if changed else "none",
    }

# =============================================================================
# TAXONOMÍA DE CLASIFICACIÓN
# =============================================================================

DOMAINS = {
    "AI": "Inteligencia Artificial y Machine Learning",
    "CS": "Ciencias de la Computación",
    "SE": "Ingeniería de Software",
    "DB": "Bases de Datos",
    "NET": "Redes y Comunicaciones",
    "MATH": "Matemáticas y Estadística",
    "WEB": "Desarrollo Web",
    "SYS": "Sistemas y DevOps",
    "OTHER": "Otros",
}

# Áreas por dominio
AREAS = {
    "AI": {
        "computer_vision": "Visión Artificial",
        "nlp": "Procesamiento de Lenguaje Natural",
        "deep_learning": "Aprendizaje Profundo",
        "ml_general": "Machine Learning General",
        "reinforcement": "Aprendizaje por Refuerzo",
        "data_science": "Ciencia de Datos",
    },
    "CS": {
        "algorithms": "Algoritmos y Estructuras",
        "theory": "Teoría de Computación",
        "graphics": "Gráficos por Computadora",
        "security": "Seguridad Informática",
    },
    "SE": {
        "architecture": "Arquitectura de Software",
        "testing": "Testing y QA",
        "patterns": "Patrones de Diseño",
        "devops": "DevOps y CI/CD",
    },
    "DB": {
        "sql": "SQL y Bases Relacionales",
        "nosql": "NoSQL y Bases Documentales",
        "orm": "ORMs y Mapeo",
    },
    "NET": {
        "networking": "Redes TCP/IP",
        "protocols": "Protocolos de Comunicación",
        "distributed": "Sistemas Distribuidos",
    },
    "WEB": {
        "frontend": "Frontend y UI",
        "backend": "Backend y APIs",
        "fullstack": "Full Stack",
    },
    "MATH": {
        "linear_algebra": "Álgebra Lineal",
        "calculus": "Cálculo",
        "statistics": "Estadística",
        "optimization": "Optimización",
    },
    "SYS": {
        "linux": "Linux y Unix",
        "containers": "Contenedores y Kubernetes",
        "cloud": "Cloud Computing",
    },
}

# =============================================================================
# SEÑALES DE CLASIFICACIÓN
# =============================================================================

# Imports de Python → (dominio, área, peso)
IMPORT_SIGNALS: dict[str, tuple[str, str, float]] = {
    # Computer Vision
    "cv2": ("AI", "computer_vision", 2.0),
    "opencv": ("AI", "computer_vision", 2.0),
    "PIL": ("AI", "computer_vision", 1.5),
    "pillow": ("AI", "computer_vision", 1.5),
    "skimage": ("AI", "computer_vision", 1.8),
    "torchvision": ("AI", "computer_vision", 2.0),
    "ultralytics": ("AI", "computer_vision", 2.5),
    "detectron2": ("AI", "computer_vision", 2.5),
    "albumentations": ("AI", "computer_vision", 1.8),
    "imgaug": ("AI", "computer_vision", 1.5),

    # Deep Learning
    "torch": ("AI", "deep_learning", 1.5),
    "pytorch": ("AI", "deep_learning", 1.5),
    "tensorflow": ("AI", "deep_learning", 1.5),
    "keras": ("AI", "deep_learning", 1.5),
    "transformers": ("AI", "nlp", 2.0),
    "huggingface": ("AI", "nlp", 2.0),

    # ML General
    "sklearn": ("AI", "ml_general", 1.8),
    "scikit-learn": ("AI", "ml_general", 1.8),
    "xgboost": ("AI", "ml_general", 1.5),
    "lightgbm": ("AI", "ml_general", 1.5),
    "catboost": ("AI", "ml_general", 1.5),

    # NLP
    "nltk": ("AI", "nlp", 1.8),
    "spacy": ("AI", "nlp", 2.0),
    "gensim": ("AI", "nlp", 1.5),
    "sentence_transformers": ("AI", "nlp", 2.0),

    # Data Science
    "pandas": ("AI", "data_science", 1.2),
    "numpy": ("AI", "data_science", 0.8),
    "scipy": ("MATH", "statistics", 1.0),
    "matplotlib": ("AI", "data_science", 0.5),
    "seaborn": ("AI", "data_science", 0.8),
    "plotly": ("AI", "data_science", 0.8),

    # Reinforcement Learning
    "gym": ("AI", "reinforcement", 2.0),
    "gymnasium": ("AI", "reinforcement", 2.0),
    "stable_baselines": ("AI", "reinforcement", 2.0),

    # Databases
    "sqlalchemy": ("DB", "orm", 1.8),
    "psycopg2": ("DB", "sql", 1.5),
    "pymongo": ("DB", "nosql", 1.8),
    "redis": ("DB", "nosql", 1.5),

    # Networking
    "socket": ("NET", "networking", 1.8),
    "requests": ("NET", "networking", 1.0),
    "aiohttp": ("NET", "networking", 1.2),
    "httpx": ("NET", "networking", 1.0),
    "websockets": ("NET", "networking", 1.5),
    "asyncio": ("NET", "networking", 0.5),

    # Web
    "flask": ("WEB", "backend", 1.5),
    "fastapi": ("WEB", "backend", 1.5),
    "django": ("WEB", "fullstack", 1.8),
    "express": ("WEB", "backend", 1.5),
    "react": ("WEB", "frontend", 1.8),
    "vue": ("WEB", "frontend", 1.8),

    # Systems
    "docker": ("SYS", "containers", 1.8),
    "kubernetes": ("SYS", "containers", 2.0),
    "boto3": ("SYS", "cloud", 1.5),
    "paramiko": ("SYS", "linux", 1.5),
}

# Keywords en texto/código → (dominio, área, peso)
KEYWORD_SIGNALS: dict[str, tuple[str, str, float]] = {
    # Computer Vision - Español
    "visión artificial": ("AI", "computer_vision", 3.5),  # Aumentado para query classification
    "vision artificial": ("AI", "computer_vision", 3.5),  # Aumentado para query classification
    "visión por computadora": ("AI", "computer_vision", 3.5),
    "detección de objetos": ("AI", "computer_vision", 3.5),
    "segmentación": ("AI", "computer_vision", 3.0),
    "segmentacion": ("AI", "computer_vision", 3.0),
    "reconocimiento facial": ("AI", "computer_vision", 3.5),
    "procesamiento de imágenes": ("AI", "computer_vision", 3.0),
    "procesamiento de imagenes": ("AI", "computer_vision", 3.0),

    # Computer Vision - Inglés / Técnico
    "computer vision": ("AI", "computer_vision", 3.5),  # Aumentado
    "object detection": ("AI", "computer_vision", 3.5),
    "image segmentation": ("AI", "computer_vision", 3.5),
    "yolo": ("AI", "computer_vision", 3.5),
    "u-net": ("AI", "computer_vision", 3.5),
    "unet": ("AI", "computer_vision", 3.5),
    "rcnn": ("AI", "computer_vision", 2.5),
    "faster rcnn": ("AI", "computer_vision", 2.5),
    "mask rcnn": ("AI", "computer_vision", 2.5),
    "resnet": ("AI", "computer_vision", 2.0),
    "vgg": ("AI", "computer_vision", 2.0),
    "efficientnet": ("AI", "computer_vision", 2.0),
    "cnn": ("AI", "computer_vision", 1.8),
    "convolutional": ("AI", "computer_vision", 1.8),
    "convolution": ("AI", "computer_vision", 1.5),
    "bounding box": ("AI", "computer_vision", 2.0),
    "bbox": ("AI", "computer_vision", 1.5),
    "data augmentation": ("AI", "computer_vision", 2.0),
    "augmentation": ("AI", "computer_vision", 1.5),

    # Deep Learning
    "red neuronal": ("AI", "deep_learning", 2.0),
    "redes neuronales": ("AI", "deep_learning", 2.0),
    "neural network": ("AI", "deep_learning", 2.0),
    "deep learning": ("AI", "deep_learning", 2.5),
    "aprendizaje profundo": ("AI", "deep_learning", 2.5),
    "backpropagation": ("AI", "deep_learning", 2.0),
    "gradient descent": ("AI", "deep_learning", 1.5),
    "batch normalization": ("AI", "deep_learning", 1.5),
    "dropout": ("AI", "deep_learning", 1.2),
    "activation function": ("AI", "deep_learning", 1.5),
    "relu": ("AI", "deep_learning", 1.0),
    "sigmoid": ("AI", "deep_learning", 1.0),
    "softmax": ("AI", "deep_learning", 1.2),
    "epoch": ("AI", "deep_learning", 1.0),
    "batch_size": ("AI", "deep_learning", 1.0),
    "learning_rate": ("AI", "deep_learning", 1.2),
    "optimizer": ("AI", "deep_learning", 1.0),
    "loss function": ("AI", "deep_learning", 1.2),
    "model.fit": ("AI", "deep_learning", 1.5),
    "model.train": ("AI", "deep_learning", 1.5),

    # NLP
    "nlp": ("AI", "nlp", 2.0),
    "procesamiento de lenguaje": ("AI", "nlp", 2.5),
    "natural language": ("AI", "nlp", 2.5),
    "transformers": ("AI", "nlp", 2.0),
    "bert": ("AI", "nlp", 2.5),
    "gpt": ("AI", "nlp", 2.5),
    "llm": ("AI", "nlp", 2.5),
    "tokenizer": ("AI", "nlp", 2.0),
    "embeddings": ("AI", "nlp", 1.8),
    "word2vec": ("AI", "nlp", 2.0),
    "sentiment analysis": ("AI", "nlp", 2.0),
    "text classification": ("AI", "nlp", 2.0),

    # ML General
    "machine learning": ("AI", "ml_general", 2.0),
    "aprendizaje automático": ("AI", "ml_general", 2.0),
    "clasificación": ("AI", "ml_general", 1.5),
    "classification": ("AI", "ml_general", 1.5),
    "regresión": ("AI", "ml_general", 1.5),
    "regression": ("AI", "ml_general", 1.5),
    "clustering": ("AI", "ml_general", 1.8),
    "kmeans": ("AI", "ml_general", 1.8),
    "random forest": ("AI", "ml_general", 1.8),
    "decision tree": ("AI", "ml_general", 1.5),
    "svm": ("AI", "ml_general", 1.8),
    "support vector": ("AI", "ml_general", 1.8),
    "cross validation": ("AI", "ml_general", 1.5),
    "train_test_split": ("AI", "ml_general", 1.5),
    "overfitting": ("AI", "ml_general", 1.2),
    "underfitting": ("AI", "ml_general", 1.2),
    "feature engineering": ("AI", "ml_general", 1.5),
    "hyperparameter": ("AI", "ml_general", 1.2),
    "meta-learning": ("AI", "ml_general", 2.0),
    "meta learning": ("AI", "ml_general", 2.0),
    "transfer learning": ("AI", "ml_general", 2.0),

    # Reinforcement Learning
    "reinforcement learning": ("AI", "reinforcement", 2.5),
    "aprendizaje por refuerzo": ("AI", "reinforcement", 2.5),
    "q-learning": ("AI", "reinforcement", 2.5),
    "policy gradient": ("AI", "reinforcement", 2.0),
    "reward": ("AI", "reinforcement", 1.2),
    "agent": ("AI", "reinforcement", 1.0),

    # Databases
    "select": ("DB", "sql", 0.8),
    "insert into": ("DB", "sql", 1.5),
    "create table": ("DB", "sql", 2.0),
    "join": ("DB", "sql", 1.0),
    "postgresql": ("DB", "sql", 1.8),
    "mysql": ("DB", "sql", 1.8),
    "mongodb": ("DB", "nosql", 2.0),
    "nosql": ("DB", "nosql", 2.0),

    # Networking
    "sdn": ("NET", "networking", 2.5),
    "software defined networking": ("NET", "networking", 3.0),
    "redes definidas por software": ("NET", "networking", 3.0),
    "telecomunicaciones": ("NET", "networking", 2.0),
    "networking": ("NET", "networking", 2.0),
    "tcp/ip": ("NET", "networking", 2.5),
    "tcp": ("NET", "networking", 1.5),
    "udp": ("NET", "networking", 1.5),
    "http": ("NET", "protocols", 1.2),
    "websocket": ("NET", "networking", 1.8),
    "socket": ("NET", "networking", 2.0),
    "api rest": ("NET", "protocols", 1.5),
    "rest api": ("NET", "protocols", 1.5),
    "peticiones": ("NET", "networking", 1.5),
    "servidor": ("NET", "networking", 1.0),
    "cliente": ("NET", "networking", 0.8),
    "request": ("NET", "networking", 0.8),
    "response": ("NET", "networking", 0.8),

    # Computer Science / Algorithms
    "algoritmo": ("CS", "algorithms", 2.5),
    "algoritmos": ("CS", "algorithms", 2.5),
    "algoritmia": ("CS", "algorithms", 2.8),
    "dijkstra": ("CS", "algorithms", 3.2),
    "grafos": ("CS", "algorithms", 2.2),
    "graph": ("CS", "algorithms", 2.0),
    "shortest path": ("CS", "algorithms", 2.6),
    "camino mas corto": ("CS", "algorithms", 2.6),
    "complejidad": ("CS", "algorithms", 1.5),
    "big o": ("CS", "algorithms", 1.8),

    # Math
    "álgebra lineal": ("MATH", "linear_algebra", 2.5),
    "algebra lineal": ("MATH", "linear_algebra", 2.5),
    "linear algebra": ("MATH", "linear_algebra", 2.5),
    "matriz": ("MATH", "linear_algebra", 1.5),
    "matrix": ("MATH", "linear_algebra", 1.5),
    "eigenvalue": ("MATH", "linear_algebra", 2.0),
    "eigenvector": ("MATH", "linear_algebra", 2.0),
    "derivada": ("MATH", "calculus", 1.5),
    "integral": ("MATH", "calculus", 1.5),
    "probabilidad": ("MATH", "statistics", 1.5),
    "probability": ("MATH", "statistics", 1.5),
    "estadística": ("MATH", "statistics", 1.8),
    "statistics": ("MATH", "statistics", 1.8),
    "distribución": ("MATH", "statistics", 1.2),
    "distribution": ("MATH", "statistics", 1.2),
}


def extract_semantic_terms(
    text: str,
    title: str = "",
    description: str = "",
    max_terms: int = 15,
) -> list[str]:
    """Extrae términos/frases relevantes de forma abierta (sin taxonomía fija)."""
    combined = f"{title} {description} {text}".lower()
    combined = _strip_accents(combined)
    combined = re.sub(r"[^a-z0-9\s]", " ", combined)
    combined = re.sub(r"\s+", " ", combined).strip()
    if not combined:
        return []

    stop = {
        "de", "la", "el", "los", "las", "en", "y", "a", "para", "por", "con", "sin", "que",
        "del", "al", "un", "una", "como", "se", "su", "sus", "es", "son", "this", "that",
        "from", "with", "for", "and", "the", "to", "of", "in", "on", "is", "are",
    }

    tokens = [tok for tok in combined.split() if len(tok) >= 3 and tok not in stop]
    if not tokens:
        return []

    unigram = Counter(tokens)
    bigram = Counter(" ".join(pair) for pair in zip(tokens, tokens[1:]))
    trigram = Counter(" ".join(tri) for tri in zip(tokens, tokens[1:], tokens[2:]))

    scored: list[tuple[str, float]] = []
    for term, count in unigram.items():
        scored.append((term, float(count)))
    for term, count in bigram.items():
        first, second = term.split()
        if first in stop or second in stop:
            continue
        scored.append((term, float(count) * 1.8))
    for term, count in trigram.items():
        tri_parts = term.split()
        if any(part in stop for part in tri_parts):
            continue
        scored.append((term, float(count) * 2.5))

    scored.sort(key=lambda x: x[1], reverse=True)
    selected: list[str] = []
    seen = set()
    for term, _score in scored:
        if term in seen:
            continue
        seen.add(term)
        selected.append(term)
        if len(selected) >= max_terms:
            break
    return selected

# Patrones de código (regex)
CODE_PATTERNS: list[tuple[str, str, str, float]] = [
    # Computer Vision
    (r"cv2\.\w+", "AI", "computer_vision", 2.0),
    (r"Image\.open", "AI", "computer_vision", 1.5),
    (r"transforms\.Compose", "AI", "computer_vision", 2.0),
    (r"\.cuda\(\)", "AI", "deep_learning", 1.0),
    (r"\.to\(['\"]cuda['\"]\)", "AI", "deep_learning", 1.0),

    # Deep Learning
    (r"nn\.Module", "AI", "deep_learning", 2.0),
    (r"nn\.Linear", "AI", "deep_learning", 1.8),
    (r"nn\.Conv2d", "AI", "computer_vision", 2.5),
    (r"nn\.LSTM", "AI", "nlp", 2.0),
    (r"model\.fit\(", "AI", "deep_learning", 1.8),
    (r"model\.train\(\)", "AI", "deep_learning", 1.5),
    (r"optimizer\.step\(\)", "AI", "deep_learning", 1.8),
    (r"loss\.backward\(\)", "AI", "deep_learning", 2.0),

    # SQL
    (r"SELECT\s+.+\s+FROM", "DB", "sql", 2.5),
    (r"INSERT\s+INTO", "DB", "sql", 2.0),
    (r"CREATE\s+TABLE", "DB", "sql", 2.5),
    (r"\.execute\(['\"]SELECT", "DB", "sql", 2.0),

    # Networking
    (r"socket\.socket\(", "NET", "networking", 2.5),
    (r"\.connect\(\(['\"]", "NET", "networking", 1.8),
    (r"\.listen\(\d+\)", "NET", "networking", 2.0),
    (r"\.accept\(\)", "NET", "networking", 2.0),
    (r"requests\.(get|post|put)\(", "NET", "networking", 1.5),
]


# =============================================================================
# CLASIFICADOR
# =============================================================================

class ContentClassifier:
    """
    Clasificador de contenido técnico con pipeline híbrido.
    - Fase 1: Análisis rápido por señales (imports, keywords, patrones)
    - Fase 2: BART-MNLI zero-shot si confianza < 0.65 (fallback semántico)
    """

    def __init__(self):
        # Compilar patrones regex
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), domain, area, weight)
            for pattern, domain, area, weight in CODE_PATTERNS
        ]

    def classify(
        self,
        text: str,
        code: Optional[str] = None,
        title: str = "",
        description: str = "",
        use_bart: bool = True,
    ) -> dict:
        """
        Clasifica contenido técnico con pipeline híbrido.

        Args:
            text: Texto extraído del documento
            code: Código fuente (si aplica)
            title: Título del contenido
            description: Descripción del contenido
            use_bart: Usar BART-MNLI si confianza < 0.65 (default: True)

        Returns:
            {
                "domain": "AI",
                "domain_label": "Inteligencia Artificial y Machine Learning",
                "area": "computer_vision",
                "area_label": "Visión Artificial",
                "confidence": 0.85,
                "tags": ["yolo", "detection", "pytorch"],
                "signals_found": [...],
                "method": "signals" | "bart-mnli"  # cómo se clasificó
            }
        """
        scores: Counter = Counter()
        signals_found: list[str] = []
        tags: set[str] = set()

        # Combinar todo el texto para análisis
        full_text = f"{title} {description} {text}".lower()
        code_text = (code or "").lower()
        semantic_terms = extract_semantic_terms(text=text, title=title, description=description)

        # ========== FASE 1: SEÑALES ==========
        # 1. Analizar imports
        self._analyze_imports(code_text, scores, signals_found, tags)

        # 2. Analizar keywords en texto
        self._analyze_keywords(full_text, scores, signals_found, tags)

        # 3. Analizar patrones de código
        self._analyze_patterns(code_text, scores, signals_found)

        # 4. Analizar título (peso extra)
        self._analyze_title(title.lower(), scores, signals_found)

        # Calcular clasificación por señales
        if not scores:
            # Sin señales claras → intentar BART-MNLI
            if use_bart:
                return self._classify_with_bart(
                    title, description, text, fallback_to_signals=True
                )
            return self._unknown_classification()

        # Obtener el mejor (dominio, área)
        best = scores.most_common(1)[0]
        (domain, area), total_weight = best

        # Calcular confianza (normalizada)
        max_possible = sum(w for _, w in scores.most_common(3))
        confidence = min(total_weight / max(max_possible, 1.0), 1.0)
        
        # Ajustar por número de señales
        if len(signals_found) < 3:
            confidence *= 0.7
        elif len(signals_found) < 5:
            confidence *= 0.85

        # ========== FASE 2: VALIDACIÓN CON BART SI CONFIDENCE < 0.65 ==========
        # Si confianza baja, usar BART para validar o mejorar
        if use_bart and confidence < 0.65:
            bart_result = self._classify_with_bart(
                title, description, text, fallback_to_signals=False
            )
            # Si BART está más confiado, usar su resultado
            if bart_result["confidence"] > confidence:
                bart_result["signals_found"] = signals_found[:20]
                return bart_result

        return {
            "domain": domain,
            "domain_label": DOMAINS.get(domain, domain),
            "area": area,
            "area_label": AREAS.get(domain, {}).get(area, area),
            "confidence": round(confidence, 3),
            "tags": list(tags)[:10],
            "semantic_terms": semantic_terms,
            "signals_found": signals_found[:20],
            "method": "signals",
        }

    def _analyze_imports(
        self,
        code: str,
        scores: Counter,
        signals: list,
        tags: set,
    ) -> None:
        """Extrae y analiza imports de código Python."""
        # Patrones de import
        import_patterns = [
            r"^import\s+(\w+)",
            r"^from\s+(\w+)",
            r"import\s+(\w+)\s+as",
        ]

        imports_found: set[str] = set()
        for pattern in import_patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                imports_found.add(match.group(1).lower())

        for imp in imports_found:
            if imp in IMPORT_SIGNALS:
                domain, area, weight = IMPORT_SIGNALS[imp]
                scores[(domain, area)] += weight
                signals.append(f"import:{imp}")
                tags.add(imp)

    def _analyze_keywords(
        self,
        text: str,
        scores: Counter,
        signals: list,
        tags: set,
    ) -> None:
        """Busca keywords técnicos en el texto."""
        for keyword, (domain, area, weight) in KEYWORD_SIGNALS.items():
            if keyword in text:
                scores[(domain, area)] += weight
                signals.append(f"keyword:{keyword}")
                # Agregar como tag (simplificado)
                tag = keyword.replace(" ", "_")[:20]
                tags.add(tag)

    def _analyze_patterns(
        self,
        code: str,
        scores: Counter,
        signals: list,
    ) -> None:
        """Busca patrones de código con regex."""
        for pattern, domain, area, weight in self._compiled_patterns:
            matches = pattern.findall(code)
            if matches:
                scores[(domain, area)] += weight * min(len(matches), 3)
                signals.append(f"pattern:{pattern.pattern[:30]}")

    def _analyze_title(
        self,
        title: str,
        scores: Counter,
        signals: list,
    ) -> None:
        """Analiza el título con peso extra."""
        for keyword, (domain, area, weight) in KEYWORD_SIGNALS.items():
            if keyword in title:
                # Peso doble para coincidencias en título
                scores[(domain, area)] += weight * 2
                signals.append(f"title:{keyword}")

    def _unknown_classification(self) -> dict:
        """Retorna clasificación por defecto cuando no hay señales."""
        return {
            "domain": "OTHER",
            "domain_label": DOMAINS["OTHER"],
            "area": "unknown",
            "area_label": "Sin clasificar",
            "confidence": 0.0,
            "tags": [],
            "signals_found": [],
            "method": "unknown",
        }

    def _classify_with_bart(
        self,
        title: str,
        description: str,
        text: str,
        fallback_to_signals: bool = True,
    ) -> dict:
        """
        Clasificación semántica usando BART-MNLI zero-shot.
        
        IMPORTANTE: Este método usa la API de transformers para hacer
        zero-shot classification. BART-MNLI requiere ~1.5 GB RAM pero
        el modelo se cachea automáticamente en ~/.cache/huggingface/.
        
        En CPU, tarda ~500ms por documento. Para ingesta, esto es aceptable.
        """
        try:
            # Preparar texto para BART (máximo 1024 tokens para eficiencia)
            combined = f"{title}. {description}. {text}"
            combined = combined[:2000]  # Limitar a 2000 caracteres
            
            # Cargar clasificador BART lazily
            classifier = _load_bart_classifier()
            if classifier is None:
                logger.warning("BART-MNLI no disponible, fallback a resultados por señales")
                return self._unknown_classification()
            
            # Candidatos de dominio (traducidos para mejor desempeño)
            domain_candidates = [
                "Inteligencia Artificial y Machine Learning",  # AI
                "Redes y Comunicaciones",  # NET
                "Bases de Datos",  # DB
                "Ciencias de la Computación",  # CS
                "Ingeniería de Software",  # SE
                "Desarrollo Web",  # WEB
                "Matemáticas y Estadística",  # MATH
                "Sistemas y DevOps",  # SYS
            ]
            
            # Zero-shot classification
            result = classifier(
                combined,
                domain_candidates,
                hypothesis_template="Este contenido es sobre {}.",
                multi_class=False,
            )
            
            # Mapear resultado a código de dominio
            best_domain_label = result["labels"][0]
            best_score = result["scores"][0]
            
            # Mapeo inverso: label → código de dominio
            domain_map = {v: k for k, v in DOMAINS.items()}
            domain = domain_map.get(best_domain_label, "OTHER")
            
            # Ahora clasificar área específica si es AI
            area = "general"
            if domain == "AI" and best_score > 0.4:
                ai_areas = [
                    "Visión Artificial",
                    "Procesamiento de Lenguaje Natural",
                    "Aprendizaje Profundo",
                    "Machine Learning General",
                    "Aprendizaje por Refuerzo",
                ]
                area_result = classifier(
                    combined,
                    ai_areas,
                    hypothesis_template="Este código es sobre {}.",
                    multi_class=False,
                )
                area_label = area_result["labels"][0]
                area_map = {v: k for k, v in AREAS.get("AI", {}).items()}
                area = area_map.get(area_label, "ml_general")
            
            logger.info(
                f"BART clasificó como {domain}/{area} (conf={best_score:.3f})"
            )
            
            return {
                "domain": domain,
                "domain_label": DOMAINS.get(domain, domain),
                "area": area,
                "area_label": AREAS.get(domain, {}).get(area, area),
                "confidence": round(best_score, 3),
                "tags": [],
                "semantic_terms": extract_semantic_terms(text=text, title=title, description=description),
                "signals_found": ["bart-mnli"],
                "method": "bart-mnli",
            }
            
        except Exception as e:
            logger.error(f"Error en BART classification: {e}")
            if fallback_to_signals:
                return self._unknown_classification()
            raise


# =============================================================================
# CLASIFICADOR DE QUERIES
# =============================================================================

def classify_query(query: str) -> dict:
    """
    Clasificación de query usando EMBEDDINGS SEMÁNTICOS (no hardcoded, no keywords).
    
    Estrategia:
    1. Generar embedding de la query
    2. Comparar con embeddings de domain descriptions
    3. Tomar el dominio más parecido (cosine similarity)
    4. Si no hay match claro (< 0.5 similarity), retorna None
    
    Ventajas:
    - 100% semántico, entiende el significado real
    - Funciona en cualquier idioma
    - No se afecta por cambiar un carácter
    - "radiación electromagnética" → None (no hay contenido)
    - "visión artificial" → AI/computer_vision ✓
    
    Returns:
        {
            "domain": "AI" | None,
            "area": "computer_vision" | None,
            "confidence": 0.0-1.0,  (cosine similarity)
        }
    """
    try:
        from sklearn.metrics.pairwise import cosine_similarity

        pre = preprocess_query_text(query)
        query_text = pre["corrected"] if pre.get("corrected") else pre["normalized"]
        if not query_text:
            return {"domain": None, "area": None, "confidence": 0.0}

        embedder = _load_query_embedder()
        query_emb = embedder.encode(f"query: {query_text}", normalize_embeddings=True)

        domain_profiles = {
            "AI": "query: inteligencia artificial machine learning deep learning computer vision nlp yolo unet",
            "CS": "query: ciencias de la computacion algoritmos estructuras de datos grafos dijkstra complejidad",
            "SE": "query: ingenieria de software arquitectura patrones testing calidad codigo",
            "DB": "query: bases de datos sql nosql consultas transacciones postgres",
            "NET": "query: redes comunicaciones tcp ip socket protocolos sdn enrutamiento",
            "MATH": "query: matematicas estadistica algebra lineal calculo optimizacion probabilidad",
            "WEB": "query: desarrollo web frontend backend api javascript html css",
            "SYS": "query: sistemas devops linux contenedores docker kubernetes infraestructura",
            "OTHER": "query: tema general no tecnico conversacion cotidiana agricultura astronomia geologia historia arte",
        }

        domain_codes = list(domain_profiles.keys())
        profile_texts = [domain_profiles[code] for code in domain_codes]
        profile_embs = embedder.encode(profile_texts, normalize_embeddings=True)

        sims = cosine_similarity([query_emb], profile_embs)[0]
        lexical_scores: Counter = Counter()
        for keyword, (domain, _area, weight) in KEYWORD_SIGNALS.items():
            if keyword in query_text:
                lexical_scores[domain] += weight

        if lexical_scores:
            max_lex = max(lexical_scores.values())
            for idx, code in enumerate(domain_codes):
                if code in lexical_scores:
                    sims[idx] += 0.12 * (lexical_scores[code] / max(max_lex, 1.0))

        best_idx = int(sims.argmax())
        best_domain = domain_codes[best_idx]
        best_score = max(0.0, min(float(sims[best_idx]), 1.0))

        other_idx = domain_codes.index("OTHER")
        other_score = float(sims[other_idx])
        sorted_scores = sorted((float(x), domain_codes[i]) for i, x in enumerate(sims))
        top_score, top_domain = sorted_scores[-1]
        second_score, _second_domain = sorted_scores[-2]

        # Evitar clasificaciones forzadas cuando la query es muy abierta o fuera de corpus
        if top_domain == "OTHER" or top_score < 0.70 or (top_score - second_score) < 0.03 or (top_score - other_score) < 0.05:
            return {
                "domain": None,
                "area": None,
                "confidence": 0.0,
                "query_normalized": pre["normalized"],
                "query_corrected": pre["corrected"],
                "query_corrected_used": pre["used_correction"],
                "query_correction_source": pre["source"],
            }

        best_area = "general"
        if best_domain in AREAS:
            area_codes = list(AREAS[best_domain].keys())
            area_labels = [AREAS[best_domain][code] for code in area_codes]
            area_profiles = [
                f"query: {label} {' '.join(label.lower().split())} {query_text}"
                for label in area_labels
            ]
            area_embs = embedder.encode(area_profiles, normalize_embeddings=True)
            area_sims = cosine_similarity([query_emb], area_embs)[0]
            area_idx = int(area_sims.argmax())
            best_area = area_codes[area_idx]

        return {
            "domain": best_domain,
            "area": best_area,
            "confidence": round(best_score, 3),
            "query_normalized": pre["normalized"],
            "query_corrected": pre["corrected"],
            "query_corrected_used": pre["used_correction"],
            "query_correction_source": pre["source"],
        }

    except Exception as e:
        logger.error(f"Error en classify_query con embeddings: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"domain": None, "area": None, "confidence": 0.0}


def _classify_query_keywords_fallback(query: str) -> dict:
    """
    Fallback a keywords cuando BART-MNLI no está disponible.
    SOLO para desarrollo local, en producción BART debería funcionar.
    """
    query_lower = query.lower()
    scores: Counter = Counter()
    keywords_found = 0

    for keyword, (domain, area, weight) in KEYWORD_SIGNALS.items():
        if keyword in query_lower:
            scores[(domain, area)] += weight
            keywords_found += 1

    if not scores:
        return {"domain": None, "area": None, "confidence": 0.0}

    best = scores.most_common(1)[0]
    (domain, area), weight = best

    # Confianza muy conservadora en fallback
    if weight >= 3.0:
        confidence = 0.80
    elif weight >= 2.0:
        confidence = 0.65
    else:
        confidence = 0.50

    if keywords_found > 1:
        confidence = min(confidence + 0.1, 1.0)

    return {
        "domain": domain if confidence >= 0.5 else None,
        "area": area if confidence >= 0.5 else None,
        "confidence": round(confidence, 3),
    }


# Instancia global del clasificador
classifier = ContentClassifier()


def _load_bart_classifier():
    """
    Carga BART-MNLI lazily (solo una vez).
    El modelo se cachea automáticamente en ~/.cache/huggingface/
    """
    global _BART_CLASSIFIER, _BART_LOADED
    
    if _BART_LOADED:
        return _BART_CLASSIFIER
    
    try:
        from transformers import pipeline
        
        logger.info("Cargando modelo BART-MNLI para zero-shot classification...")
        _BART_CLASSIFIER = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,  # -1 = CPU, 0+ = GPU
        )
        _BART_LOADED = True
        logger.info("BART-MNLI cargado exitosamente")
        return _BART_CLASSIFIER
        
    except ImportError:
        logger.error("transformers no está instalado")
        _BART_LOADED = True
        return None
    except Exception as e:
        logger.error(f"Error cargando BART-MNLI: {e}")
        _BART_LOADED = True
        return None


def classify_content(
    text: str,
    code: Optional[str] = None,
    title: str = "",
    description: str = "",
    use_bart: bool = True,
) -> dict:
    """
    Función de conveniencia para clasificar contenido.
    
    Pipeline híbrido:
    1. Análisis rápido por señales (imports, keywords) < 50ms
    2. Si confidence < 0.65, usar BART-MNLI para validación (~500ms)
    
    Args:
        text: Texto del documento
        code: Código fuente (opcional)
        title: Título
        description: Descripción
        use_bart: Usar BART como fallback (default: True)
        
    Returns:
        Diccionario con domain, area, confidence, tags, etc.
    """
    return classifier.classify(text, code, title, description, use_bart)
