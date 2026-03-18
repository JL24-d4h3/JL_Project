"""
services/classifier.py — Clasificación Automática de Contenido
GTR-PUCP CDN Educativa Offline

Clasifica contenido técnico por dominio y área usando análisis de señales
(imports, keywords, patrones). Esto elimina la dependencia de la clasificación
manual del usuario y mejora la precisión de búsqueda.

Pipeline:
  1. Extrae señales del código (imports, funciones)
  2. Analiza texto por keywords técnicos
  3. Asigna dominio + área + confianza
  4. Los metadatos se indexan en ChromaDB para pre-filtrado
"""
from __future__ import annotations
import re
import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)

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
    "visión artificial": ("AI", "computer_vision", 2.5),
    "vision artificial": ("AI", "computer_vision", 2.5),
    "visión por computadora": ("AI", "computer_vision", 2.5),
    "detección de objetos": ("AI", "computer_vision", 2.5),
    "segmentación": ("AI", "computer_vision", 2.0),
    "segmentacion": ("AI", "computer_vision", 2.0),
    "reconocimiento facial": ("AI", "computer_vision", 2.5),
    "procesamiento de imágenes": ("AI", "computer_vision", 2.0),
    "procesamiento de imagenes": ("AI", "computer_vision", 2.0),

    # Computer Vision - Inglés / Técnico
    "computer vision": ("AI", "computer_vision", 2.5),
    "object detection": ("AI", "computer_vision", 2.5),
    "image segmentation": ("AI", "computer_vision", 2.5),
    "yolo": ("AI", "computer_vision", 3.0),
    "u-net": ("AI", "computer_vision", 3.0),
    "unet": ("AI", "computer_vision", 3.0),
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
    """Clasificador de contenido técnico por señales."""

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
    ) -> dict:
        """
        Clasifica contenido técnico.

        Args:
            text: Texto extraído del documento
            code: Código fuente (si aplica)
            title: Título del contenido
            description: Descripción del contenido

        Returns:
            {
                "domain": "AI",
                "domain_label": "Inteligencia Artificial y Machine Learning",
                "area": "computer_vision",
                "area_label": "Visión Artificial",
                "confidence": 0.85,
                "tags": ["yolo", "detection", "pytorch"],
                "signals_found": [...],
            }
        """
        scores: Counter = Counter()
        signals_found: list[str] = []
        tags: set[str] = set()

        # Combinar todo el texto para análisis
        full_text = f"{title} {description} {text}".lower()
        code_text = (code or "").lower()

        # 1. Analizar imports
        self._analyze_imports(code_text, scores, signals_found, tags)

        # 2. Analizar keywords en texto
        self._analyze_keywords(full_text, scores, signals_found, tags)

        # 3. Analizar patrones de código
        self._analyze_patterns(code_text, scores, signals_found)

        # 4. Analizar título (peso extra)
        self._analyze_title(title.lower(), scores, signals_found)

        # Determinar clasificación final
        if not scores:
            return self._unknown_classification()

        # Obtener el mejor (dominio, área)
        best = scores.most_common(1)[0]
        (domain, area), total_weight = best

        # Calcular confianza (normalizada)
        max_possible = sum(w for _, w in scores.most_common(3))
        confidence = min(total_weight / max(max_possible, 1.0), 1.0)
        # Ajustar: si hay pocas señales, reducir confianza
        if len(signals_found) < 3:
            confidence *= 0.7
        elif len(signals_found) < 5:
            confidence *= 0.85

        return {
            "domain": domain,
            "domain_label": DOMAINS.get(domain, domain),
            "area": area,
            "area_label": AREAS.get(domain, {}).get(area, area),
            "confidence": round(confidence, 3),
            "tags": list(tags)[:10],  # máximo 10 tags
            "signals_found": signals_found[:20],  # máximo 20 señales
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
        }


# =============================================================================
# CLASIFICADOR DE QUERIES
# =============================================================================

def classify_query(query: str) -> dict:
    """
    Clasificación rápida de la consulta del usuario.
    Usado para pre-filtrar resultados en búsqueda.

    Returns:
        {
            "domain": "AI" | None,
            "area": "computer_vision" | None,
            "confidence": 0.0-1.0,
        }
    """
    query_lower = query.lower()
    scores: Counter = Counter()

    # Buscar keywords en la query
    for keyword, (domain, area, weight) in KEYWORD_SIGNALS.items():
        if keyword in query_lower:
            scores[(domain, area)] += weight

    if not scores:
        return {"domain": None, "area": None, "confidence": 0.0}

    best = scores.most_common(1)[0]
    (domain, area), weight = best

    # Calcular confianza basada en peso acumulado
    confidence = min(weight / 5.0, 1.0)

    return {
        "domain": domain,
        "area": area,
        "confidence": round(confidence, 3),
    }


# Instancia global del clasificador
classifier = ContentClassifier()


def classify_content(
    text: str,
    code: Optional[str] = None,
    title: str = "",
    description: str = "",
) -> dict:
    """Función de conveniencia para clasificar contenido."""
    return classifier.classify(text, code, title, description)
