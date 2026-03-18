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
        logger.warning("Retriever no disponible, usando solo MOCK_DB: %s", exc)


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


MOCK_DB: list[dict] = [
    {
        "keywords": ["fourier", "transformada", "señal", "frecuencia", "espectro", "fft", "dft"],
        "level": "L1",
        "results": [
            {
                "content_id": "uuid-f01", "content_type": "video",
                "title": "Cálculo Avanzado — Transformada de Fourier (Teoría completa)",
                "snippet": "Derivación rigurosa: condiciones de existencia, interpretación espectral y propiedades principales con demostraciones.",
                "thumbnail_url": "", "viewer_url": "/files/videos/test-video.mp4",
                "upload_date": "2026-01-20T10:00:00Z", "requires_auth": False, "relevance_score": 0.96,
            },
            {
                "content_id": "uuid-f02", "content_type": "pdf",
                "title": "Guía de ejercicios resueltos — Series y Transformadas de Fourier",
                "snippet": "40 ejercicios con solución: series de Fourier, coeficientes aₙ y bₙ, aplicación a la ecuación del calor.",
                "thumbnail_url": "", "viewer_url": "/viewer/document/uuid-f02?page=12",
                "upload_date": "2026-02-01T08:00:00Z", "requires_auth": False, "relevance_score": 0.91,
            },
            {
                "content_id": "uuid-f03", "content_type": "video",
                "title": "DFT y FFT — Implementación eficiente en Python con NumPy",
                "snippet": "Algoritmo FFT de Cooley-Tukey O(n log n), numpy.fft, análisis de audio digital y ventaneo.",
                "thumbnail_url": "", "viewer_url": "/viewer/video/uuid-f03?t=90",
                "upload_date": "2026-01-28T14:00:00Z", "requires_auth": False, "relevance_score": 0.85,
            },
        ],
        "ai_text": """## Transformada de Fourier

La **Transformada de Fourier** convierte una señal del dominio temporal al dominio de la frecuencia, revelando qué componentes espectrales la constituyen.

### Definición continua

Para $f(t)$ absolutamente integrable en $\\mathbb{R}$:

$$\\mathcal{F}\\{f\\}(\\omega) = F(\\omega) = \\int_{-\\infty}^{\\infty} f(t)\\, e^{-i\\omega t}\\, dt$$

La transformada inversa recupera la señal:

$$f(t) = \\frac{1}{2\\pi} \\int_{-\\infty}^{\\infty} F(\\omega)\\, e^{i\\omega t}\\, d\\omega$$

### Propiedades fundamentales

| Propiedad | Enunciado |
|-----------|-----------|
| Linealidad | $\\mathcal{F}\\{af + bg\\} = aF + bG$ |
| Desplazamiento temporal | $\\mathcal{F}\\{f(t-t_0)\\} = e^{-i\\omega t_0} F(\\omega)$ |
| Convolución | $\\mathcal{F}\\{f * g\\} = F(\\omega) \\cdot G(\\omega)$ |
| Derivación | $\\mathcal{F}\\{f'(t)\\} = i\\omega\\, F(\\omega)$ |
| Parseval | $\\int |f|^2\\,dt = \\frac{1}{2\\pi}\\int |F|^2\\,d\\omega$ |

### Pares de Fourier comunes

- **Rect** $\\Pi(t/T)$ → $T\\,\\text{sinc}(\\omega T/2)$
- **Gaussiana** $e^{-at^2}$ → $\\sqrt{\\pi/a}\\,e^{-\\omega^2/(4a)}$
- **Delta** $\\delta(t)$ → $1$ (espectro plano)

### Transformada Discreta (DFT) y FFT

Para $N$ muestras discretas $x_n$:

$$X_k = \\sum_{n=0}^{N-1} x_n\\, e^{-i 2\\pi k n / N}, \\quad k = 0,\\ldots,N-1$$

El algoritmo **FFT de Cooley-Tukey** reduce la complejidad de $O(N^2)$ a $O(N \\log N)$ dividiendo recursivamente en sub-DFTs de tamaño $N/2$.

### Recursos en el CDN

El CDN tiene **3 recursos curados**: un video con derivaciones completas, una guía de 40 ejercicios resueltos (series + transformadas), y un video de implementación FFT en Python con `numpy.fft`.""",
        "suggestions": ["Series de Fourier", "Transformada de Laplace", "FFT con NumPy", "Señales LTI"],
    },
    {
        "keywords": ["red", "redes", "tcp", "ip", "lan", "wan", "protocolo", "cisco", "ethernet", "router", "socket", "subnet"],
        "level": "L1",
        "results": [
            {
                "content_id": "uuid-net01", "content_type": "video",
                "title": "Redes de Computadoras — Módulo 5: Protocolo TCP/IP",
                "snippet": "Three-way handshake, control de flujo con ventana deslizante, retransmisiones y estados de cierre TCP.",
                "thumbnail_url": "", "viewer_url": "/viewer/video/uuid-net01?t=142",
                "upload_date": "2026-01-15T09:00:00Z", "requires_auth": False, "relevance_score": 0.94,
            },
            {
                "content_id": "uuid-net02", "content_type": "pdf",
                "title": "Manual de Redes — CISCO Academy Nivel 1 (Español)",
                "snippet": "Desde topologías básicas hasta configuración de routers, subnetting, VLSM y troubleshooting con Packet Tracer.",
                "thumbnail_url": "", "viewer_url": "/viewer/document/uuid-net02?page=3",
                "upload_date": "2026-01-10T14:00:00Z", "requires_auth": False, "relevance_score": 0.88,
            },
            {
                "content_id": "uuid-net03", "content_type": "document",
                "title": "Guía de Subnetting IPv4 — CIDR y cálculo de redes",
                "snippet": "Tablas de máscaras /8 a /30, división de redes, broadcast, hosts útiles por subred y VLSM.",
                "thumbnail_url": "", "viewer_url": "/viewer/document/uuid-net03",
                "upload_date": "2026-02-05T10:00:00Z", "requires_auth": False, "relevance_score": 0.82,
            },
        ],
        "ai_text": """## Redes de Computadoras y Protocolo TCP/IP

Una **red de computadoras** permite intercambiar datos entre dispositivos. Las arquitecturas de referencia son **OSI** (7 capas) y **TCP/IP** (4 capas).

### Modelo TCP/IP

| Capa TCP/IP | Capas OSI equivalentes | Protocolos |
|-------------|----------------------|------------|
| Aplicación | Aplicación + Presentación + Sesión | HTTP, FTP, DNS, SSH |
| Transporte | Transporte | **TCP**, **UDP** |
| Internet | Red | IP, ICMP, ARP |
| Acceso a red | Enlace + Físico | Ethernet, Wi-Fi |

### TCP vs UDP

**TCP** — orientado a conexión:
- *Three-way handshake*: SYN → SYN-ACK → ACK
- Garantiza entrega ordenada y sin pérdidas (retransmisión con ACKs)
- Control de flujo (ventana deslizante) y congestión (AIMD)
- Casos de uso: HTTP/S, SSH, FTP, bases de datos

**UDP** — sin conexión:
- Sin handshake, sin acuses de recibo
- Muy baja latencia → VoIP, streaming, DNS, videojuegos

### Direccionamiento IPv4 y Subnetting

Dirección IPv4: 32 bits. Con notación CIDR `/n`, los primeros $n$ bits identifican la red:

$$\\text{Hosts útiles} = 2^{32-n} - 2$$

**Ejemplo**: `192.168.1.0/26`
- $2^6 - 2 = 62$ hosts útiles
- Broadcast: `192.168.1.63`
- Rango: `192.168.1.1` – `192.168.1.62`

### Recursos en el CDN

Hay **3 recursos**: video TCP/IP en profundidad, manual CISCO con configuración práctica, y guía de subnetting con tablas VLSM.""",
        "suggestions": ["TCP vs UDP diferencia", "¿Cómo funciona DNS?", "Subnetting ejercicios", "Modelo OSI"],
    },
    {
        "keywords": ["derivada", "integral", "cálculo", "límite", "diferencial", "integración", "taylor"],
        "level": "L1",
        "results": [
            {
                "content_id": "uuid-calc01", "content_type": "video",
                "title": "Cálculo Diferencial — Regla de la Cadena y Derivadas de orden superior",
                "snippet": "Regla de la cadena, derivadas implícitas, derivadas de orden superior y Serie de Taylor.",
                "thumbnail_url": "", "viewer_url": "/viewer/video/uuid-calc01?t=312",
                "upload_date": "2026-01-22T11:00:00Z", "requires_auth": False, "relevance_score": 0.93,
            },
            {
                "content_id": "uuid-calc02", "content_type": "pdf",
                "title": "Ejercicios de Cálculo Integral — Técnicas de integración",
                "snippet": "Integración por partes, sustitución trigonométrica, fracciones parciales, longitud de arco y volúmenes de revolución.",
                "thumbnail_url": "", "viewer_url": "/viewer/document/uuid-calc02",
                "upload_date": "2026-01-25T09:00:00Z", "requires_auth": False, "relevance_score": 0.87,
            },
        ],
        "ai_text": """## Cálculo Diferencial e Integral

El cálculo estudia el cambio continuo: la **derivada** mide tasas de cambio instantáneas; la **integral** acumula cantidades.

### Definición de derivada

$$f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}$$

### Reglas de diferenciación

| Regla | Fórmula |
|-------|---------|
| Potencia | $\\dfrac{d}{dx}[x^n] = nx^{n-1}$ |
| Producto | $(fg)' = f'g + fg'$ |
| Cociente | $\\left(\\dfrac{f}{g}\\right)' = \\dfrac{f'g - fg'}{g^2}$ |
| Cadena | $\\dfrac{d}{dx}[f(g(x))] = f'(g(x))\\cdot g'(x)$ |
| Exponencial | $\\dfrac{d}{dx}[e^x] = e^x$ |

### Serie de Taylor

$$f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n$$

Ejemplos: $e^x = 1 + x + \\frac{x^2}{2!} + \\frac{x^3}{3!} + \\cdots$ y $\\sin x = x - \\frac{x^3}{6} + \\frac{x^5}{120} - \\cdots$

### Teorema Fundamental del Cálculo

Si $F'(x) = f(x)$:

$$\\int_a^b f(x)\\,dx = F(b) - F(a)$$

### Recursos en el CDN

Hay **2 recursos**: video de cálculo diferencial (cadena, implícitas, Taylor) y PDF con técnicas de integración y aplicaciones geométricas.""",
        "suggestions": ["L'Hôpital y límites", "Integrales impropias", "Cálculo multivariable", "EDOs"],
    },
]

GENERAL_KNOWLEDGE: list[dict] = [
    {
        "keywords": ["deep learning", "deeplearning", "aprendizaje profundo", "red neuronal", "cnn", "lstm", "transformer", "backpropagation"],
        "ai_text": """## Deep Learning

El **Deep Learning** usa redes neuronales con múltiples capas ocultas para aprender representaciones jerárquicas de los datos, sin necesidad de ingeniería manual de características.

### Cómo aprende una red neuronal

1. **Forward pass**: $\\mathbf{h}^{(l)} = \\sigma(W^{(l)}\\mathbf{h}^{(l-1)} + \\mathbf{b}^{(l)})$
2. **Función de pérdida** (entropía cruzada para clasificación): $\\mathcal{L} = -\\sum_i y_i \\log \\hat{y}_i$
3. **Backpropagation**: regla de la cadena para $\\frac{\\partial \\mathcal{L}}{\\partial W^{(l)}}$
4. **Actualización** (Adam optimizer): $W \\leftarrow W - \\eta\\,\\hat{m}/(\\sqrt{\\hat{v}}+\\varepsilon)$

### Funciones de activación

| Función | Fórmula | Uso |
|---------|---------|-----|
| ReLU | $\\max(0, x)$ | Capas ocultas (estándar) |
| Sigmoid | $1/(1+e^{-x})$ | Salida binaria |
| Softmax | $e^{x_i}/\\sum_j e^{x_j}$ | Clasificación multiclase |
| GELU | $x\\cdot\\Phi(x)$ | Transformers |

### Arquitecturas principales

- **CNN**: detecta bordes → texturas → objetos; usa convoluciones $O(k^2\\cdot C_{in}\\cdot C_{out}\\cdot HW)$
- **LSTM**: compuertas de olvido, entrada y salida para memoria a largo plazo
- **Transformer**: self-attention $\\text{Attn}(Q,K,V) = \\text{softmax}\\!\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$
- **GAN**: min-max $\\min_G \\max_D \\mathbb{E}[\\log D(x)] + \\mathbb{E}[\\log(1-D(G(z)))]$

### Regularización y problemas comunes

- **Overfitting**: Dropout (desactiva neuronas aleatoriamente), L2 weight decay, data augmentation
- **Gradiente que desaparece**: ReLU + inicialización He + Batch Normalization
- **Velocidad**: Adam en lugar de SGD puro, learning rate warm-up + cosine decay""",
        "suggestions": ["Transformers y atención", "CNNs visión computacional", "Overfitting y regularización", "PyTorch vs TensorFlow"],
    },
    {
        "keywords": ["machine learning", "ml", "aprendizaje automático", "clasificación", "regresión", "clustering", "sklearn", "overfitting", "random forest", "svm"],
        "ai_text": """## Machine Learning

El **Machine Learning** permite a los sistemas aprender patrones de datos sin ser programados explícitamente.

### Tipos de aprendizaje

| Tipo | Datos | Algoritmos representativos |
|------|-------|--------------------------|
| Supervisado | $(x_i, y_i)$ con etiqueta | Regresión lineal, SVM, Random Forest, XGBoost |
| No supervisado | Solo $x_i$ | K-Means, DBSCAN, PCA, Autoencoders |
| Semi-supervisado | Mezcla | Self-training, Label Propagation |
| Por refuerzo | Agente + recompensa | Q-Learning, PPO, AlphaGo |

### Bias-Variance Tradeoff

$$\\text{Error} = \\text{Bias}^2 + \\text{Varianza} + \\text{Ruido irreducible}$$

- **Alto Bias** (underfitting): modelo demasiado simple → aumentar complejidad
- **Alta Varianza** (overfitting): el modelo memoriza → regularizar, más datos, ensemble

### Métricas de evaluación

$$\\text{Precisión} = \\frac{TP}{TP+FP}, \\quad \\text{Recall} = \\frac{TP}{TP+FN}, \\quad F_1 = 2\\cdot\\frac{P\\cdot R}{P+R}$$

Para regresión: $\\text{RMSE} = \\sqrt{\\frac{1}{n}\\sum(y_i - \\hat{y}_i)^2}$

### Pipeline en Python (scikit-learn)

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', RandomForestClassifier(n_estimators=200, random_state=42)),
])
scores = cross_val_score(pipe, X, y, cv=5, scoring='f1_weighted')
print(f'F1: {scores.mean():.3f} ± {scores.std():.3f}')
```""",
        "suggestions": ["Deep Learning", "Random Forest vs XGBoost", "PCA y reducción dimensional", "Validación cruzada"],
    },
    {
        "keywords": ["linux", "kali", "ubuntu", "debian", "instalar", "sistema operativo", "terminal", "bash", "shell", "apt", "sudo", "pentest", "ciberseguridad", "hacking"],
        "ai_text": """## Linux — Instalación y uso

**Linux** es un núcleo de código abierto. Las distribuciones (*distros*) empaquetan el kernel con gestores de paquetes, herramientas y entornos gráficos.

### Distribuciones principales

| Distro | Base | Uso principal |
|--------|------|---------------|
| **Ubuntu** | Debian | Escritorio/servidores, amigable para principiantes |
| **Kali Linux** | Debian | Pentesting y ciberseguridad |
| **Debian** | — | Servidores, muy estable |
| **Arch Linux** | — | Usuarios avanzados, personalización total |
| **Fedora** | RPM | Escritorio moderno, tecnología cutting-edge |

### Instalar Kali Linux

**Opción A — Máquina virtual (recomendado)**

1. Descargar VirtualBox en [virtualbox.org](https://virtualbox.org)
2. Descargar imagen `.ova` en [kali.org/get-kali](https://kali.org/get-kali/) → *Virtual Machines*
3. Importar: *File → Import Appliance*
4. Asignar ≥ 4 GB RAM y ≥ 2 núcleos CPU
5. Usuario/contraseña por defecto: `kali` / `kali`

**Opción B — Dual boot (bare-metal)**

```bash
# Grabar ISO en USB (Linux/macOS)
sudo dd if=kali-linux-2024.3-amd64.iso of=/dev/sdX bs=4M status=progress sync

# Post-instalación: actualizar todo
sudo apt update && sudo apt full-upgrade -y

# Instalar herramientas extra
sudo apt install -y kali-tools-top10
```

### Comandos esenciales

```bash
ls -lah          # listar con tamaños legibles
find / -name '*.conf' 2>/dev/null   # buscar archivos
grep -rn 'texto' /etc/              # buscar dentro de archivos
chmod +x script.sh                  # hacer ejecutable
sudo !!          # repetir último cmd con sudo
man nmap         # manual de cualquier comando
```

### Herramientas Kali más usadas

- **nmap** — escaneo de puertos: `nmap -sV -O -T4 192.168.1.0/24`
- **Metasploit** — explotación: `msfconsole`
- **Burp Suite** — proxy HTTP/HTTPS para pentest web
- **Wireshark** — captura y análisis de tráfico
- **Aircrack-ng** — auditoría de redes Wi-Fi

> **Aviso legal**: Usa estas herramientas *solo* en redes propias o con autorización escrita. El acceso no autorizado es delito (Ley Peruana 30096).""",
        "suggestions": ["Comandos básicos Linux", "Nmap tutorial", "¿Cómo funciona Metasploit?", "Ubuntu vs Kali Linux"],
    },
    {
        "keywords": ["python", "programación", "algoritmo", "complejidad", "recursion", "poo", "oop", "decorador"],
        "ai_text": """## Python — Conceptos fundamentales

**Python** es un lenguaje interpretado, multiparadigma y de alto nivel. Su filosofía: legibilidad (*Zen of Python*).

### Complejidad de estructuras de datos

| Estructura | Acceso | Búsqueda | Inserción | Eliminación |
|------------|--------|----------|-----------|-------------|
| `list` | $O(1)$ | $O(n)$ | $O(1)^*$ final | $O(n)$ |
| `dict` | $O(1)$ prom. | $O(1)$ prom. | $O(1)$ prom. | $O(1)$ prom. |
| `set` | — | $O(1)$ prom. | $O(1)$ prom. | $O(1)$ prom. |
| `deque` | $O(n)$ | $O(n)$ | $O(1)$ ambos | $O(1)$ ambos |

### Orientación a objetos

```python
class Animal:
    def __init__(self, nombre: str, sonido: str) -> None:
        self.nombre = nombre
        self._sonido = sonido

    def hablar(self) -> str:
        return f'{self.nombre}: {self._sonido}'

class Perro(Animal):
    def hablar(self) -> str:
        return super().hablar() + ' 🐾'
```

### Decoradores

```python
import time, functools

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        print(f'{func.__name__}: {time.perf_counter()-t0:.4f}s')
        return result
    return wrapper

@timer
def buscar_primos(n: int) -> list[int]:
    return [x for x in range(2, n) if all(x % i for i in range(2, x))]
```

### GIL y concurrencia

El **GIL** impide que múltiples threads ejecuten bytecode simultáneamente en CPython:
- Para CPU-bound: usa `multiprocessing` (procesos separados)
- Para I/O-bound: usa `asyncio` (corrutinas no-bloqueantes)
- Para código numérico: NumPy libera el GIL en operaciones C""",
        "suggestions": ["Async/await Python", "NumPy y Pandas", "Type hints y mypy", "Iteradores y generadores"],
    },
    {
        "keywords": ["álgebra", "algebra", "matriz", "matrices", "vector", "lineal", "eigenvalor", "autovalor", "determinante", "svd", "pca"],
        "ai_text": """## Álgebra Lineal

Estudia vectores, matrices y transformaciones lineales. Es la base matemática del ML, gráficos 3D y mecánica cuántica.

### Producto matricial

Para $A \\in \\mathbb{R}^{m\\times n}$, $B \\in \\mathbb{R}^{n\\times p}$:

$$(AB)_{ij} = \\sum_{k=1}^{n} A_{ik}\\, B_{kj}$$

**No conmutativo**: $AB \\neq BA$ en general.

### Determinante e inversa ($2\\times 2$)

$$\\det\\begin{pmatrix}a & b \\\\ c & d\\end{pmatrix} = ad - bc$$

$$A^{-1} = \\frac{1}{\\det A}\\begin{pmatrix}d & -b \\\\ -c & a\\end{pmatrix} \\quad (\\text{si } \\det A \\neq 0)$$

### Eigenvalores y eigenvectores

$$A\\mathbf{v} = \\lambda\\mathbf{v} \\iff \\det(A - \\lambda I) = 0$$

Las raíces del polinomio característico son los eigenvalores. Aplicaciones:
- Resolver $\\mathbf{x}' = A\\mathbf{x}$: solución $\\mathbf{x}(t) = \\sum_k c_k e^{\\lambda_k t}\\mathbf{v}_k$
- **PCA**: eigenvectores de la matriz de covarianza = componentes principales

### SVD (Descomposición en Valores Singulares)

$$A = U\\Sigma V^T$$

$U, V$ ortogonales; $\\Sigma$ diagonal con $\\sigma_i \\geq 0$. Usos:
- Compresión de imágenes (mantener top-$k$ valores singulares)
- Sistemas de recomendación (factorización de matrices)
- Pseudoinversa: $A^+ = V\\Sigma^+ U^T$

```python
import numpy as np
A = np.array([[4, 2], [1, 3]])
eigenvalues, eigenvectors = np.linalg.eig(A)
U, sigma, Vt = np.linalg.svd(A)
```""",
        "suggestions": ["SVD y PCA en Python", "Transformaciones lineales", "Sistemas de ecuaciones", "Álgebra lineal en ML"],
    },
    # ── DEPORTES ─────────────────────────────────────────────────────────────
    {
        "keywords": ["messi", "lionel", "fútbol", "futbol", "football", "soccer",
                     "balón de oro", "inter miami", "barcelona fc", "argentina campeón",
                     "mundial 2022", "deportista", "jugador"],
        "ai_text": """## Lionel Messi

**Lionel Andrés Messi** (Rosario, 24 de junio de 1987) es considerado por muchos el mejor futbolista de la historia. Criado en las Ligas Juveniles del **FC Barcelona**, debutó en el primer equipo en 2004 y marcó una era de 17 años en el club catalán antes de pasar al **Paris Saint-Germain** (2021–2023) y luego al **Inter Miami** (MLS, 2023–presente).

### Palmarés destacado

| Título | Cantidad |
|---|---|
| Balón de Oro (FIFA/France Football) | **8** (récord mundial) |
| Ligas españolas (La Liga) | 10 |
| Champions League | 4 |
| Copa del Mundo FIFA **Qatar 2022** | 1 🇦🇷 |
| Copa América | 1 (2021) |
| Copa del Rey | 7 |

### Récords individuales

- **Goles con el FC Barcelona**: 672 (récord histórico del club)
- **Goles para Argentina**: más de 109 (máximo goleador histórico de la Selección)
- Único jugador en ganar **6 Balones de Oro** antes de sumar su 7.º y 8.º
- Máximo asistidor en la historia de La Liga

### El Mundial de Qatar 2022

Fue su quinta Copa del Mundo. Argentina venció a Francia en la final (3–3 en tiempo reglamentario, 4–2 en penales), consagrando a Messi con el único trofeo que le faltaba. Ganó el **Balón de Oro** del torneo y estableció el récord de más partidos jugados en Mundiales (26).

### Estilo de juego

Mediapunta / extremo izquierdo con características únicas:
- **Regate corto y explosivo** — bajo centro de gravedad
- **Visión de juego** excepcional y pase filtrado
- **Disparo con pie izquierdo** de precisión quirúrgica
- Capacidad de crear **desequilibrio individual** ante cualquier defensor

> *"El fútbol no es solo un deporte; es el idioma universal que Messi habla mejor que nadie."*
""",
        "suggestions": ["Maradona vs Messi", "Copa del Mundo 2022", "Historia del FC Barcelona", "Fútbol peruano"],
    },
    {
        "keywords": ["neymar", "cristiano ronaldo", "real madrid", "premier league",
                     "champions league", "copa del mundo", "mundial", "olimpiadas", "atletismo",
                     "natación", "mbappé", "deporte", "baloncesto", "tenis", "voleibol"],
        "ai_text": """## Deportes en el Mundo

El deporte es una manifestación cultural universal que combina competencia, disciplina y trabajo en equipo.

### Fútbol — El deporte rey

El fútbol es el deporte más popular del planeta con más de **4 mil millones de seguidores**.

| Competición | Campeones recientes |
|---|---|
| FIFA Copa del Mundo | Argentina (2022), Francia (2018) |
| UEFA Champions League | Real Madrid (2024), Man City (2023) |
| Copa América | Argentina (2021, 2024) |
| Liga Sudamericana | LDU Quito (2023) |

### Deportes Olímpicos

Los **Juegos Olímpicos** (JJ.OO.) se celebran cada 4 años. Categorías principales:
- **Atletismo**: 100m, maratón, salto de longitud
- **Natación**: estilos libre, espalda, mariposa, combinado
- **Gimnasia**: artística, rítmica, trampolín
- **Deportes de equipo**: básquetbol, voleibol, handball

### Perú en los deportes

- **Fútbol**: La Selección Peruana clasificó a Mundiales en 1970 y 2018
- **Voley**: La selección femenina fue subcampeona mundial en 1982
- **Surf**: Perú es potencia mundial; Lima tiene olas de clase mundial en Punta Hermosa
- **Atletismo**: Gladys Tejeda, maratonista internacional
""",
        "suggestions": ["Fútbol peruano historia", "Juegos Olímpicos Lima 2019", "Messi vs Maradona", "Voleibol femenino Perú"],
    },
    # ── HISTORIA ─────────────────────────────────────────────────────────────
    {
        "keywords": ["inca", "incas", "machu picchu", "tahuantinsuyo", "cusco", "pizarro",
                     "conquista", "virreinato", "independencia perú", "historia perú",
                     "tupac amaru", "atahualpa", "pachacutec"],
        "ai_text": """## Historia del Perú

### El Imperio Inca — Tahuantinsuyo

El **Tahuantinsuyo** (quechua: «los cuatro suyos») fue el mayor imperio precolombino de América, con capital en **Cusco**. En su apogeo (siglos XV–XVI) abarcó desde el sur de Colombia hasta el norte de Argentina y Chile.

| Incas destacados | Logro principal |
|---|---|
| **Pachacútec** (1438–1471) | Expansión del imperio; posiblemente constructor de Machu Picchu |
| **Túpac Yupanqui** (1471–1493) | Expansión al sur (Chile, Argentina) |
| **Huayna Cápac** (1493–1527) | Mayor extensión territorial |
| **Atahualpa** (1532–1533) | Último Sapa Inca; capturado por Pizarro |

### Machu Picchu

Ciudadela inca del siglo XV ubicada a 2430 msnm en la cordillera de los Andes. Es **Patrimonio de la Humanidad UNESCO** (1983) y una de las **7 Maravillas del Mundo Moderno** (2007). Su función exacta es debatida: ¿residencia real, centro religioso, o observatorio astronómico?

### Conquista y Virreinato (1532–1821)

- **1532**: Francisco Pizarro captura a Atahualpa en Cajamarca
- **1535**: Fundación de Lima («Ciudad de los Reyes»)
- **1542**: Creación del Virreinato del Perú, el más poderoso de Sudamérica
- **1780–1781**: Rebelión de Túpac Amaru II

### Independencia (1821)

- **28 de julio de 1821**: José de San Martín proclama la Independencia del Perú en Lima
- **1824**: Batalla de Ayacucho — fin definitivo del dominio español en Sudamérica
""",
        "suggestions": ["Machu Picchu turismo", "Cultura Mochica", "Independencia del Perú", "Virreinato del Perú"],
    },
    {
        "keywords": ["historia", "segunda guerra mundial", "guerra fría", "revolución francesa",
                     "edad media", "roma antigua", "grecia antigua", "renacimiento", "revolución industrial",
                     "nazismo", "hitler", "urss", "guerra mundial"],
        "ai_text": """## Historia Universal — Hitos Clave

### Edad Antigua

| Civilización | Período | Aporte |
|---|---|---|
| Mesopotamia | 3500–500 a.C. | Escritura cuneiforme, Código de Hammurabi |
| Egipto | 3100–30 a.C. | Pirámides, papiro, hieroglíficos |
| Grecia | 800–146 a.C. | Democracia, filosofía, olimpiadas |
| Roma | 753 a.C.–476 d.C. | Derecho romano, infraestructura, latín |

### Edad Moderna y Contemporánea

- **1789 — Revolución Francesa**: «Liberté, Égalité, Fraternité»; fin del Antiguo Régimen
- **1804 — Napoleón**: Imperio francés; Código Napoleónico
- **1848 — Primavera de los Pueblos**: revoluciones en Europa central
- **1914–1918 — Primera Guerra Mundial**: 20 millones de muertos
- **1939–1945 — Segunda Guerra Mundial**: mayor conflicto de la historia; 70–85 millones de víctimas
- **1945–1991 — Guerra Fría**: EE.UU. vs. URSS; carrera nuclear y espacial
- **1969**: Neil Armstrong pisa la Luna
- **1991**: Disolución de la URSS; fin de la bipolaridad
""",
        "suggestions": ["Revolución Francesa causas", "Segunda Guerra Mundial resumen", "Civilizaciones precolombinas", "Historia del Perú"],
    },
    # ── LITERATURA Y ARTE ─────────────────────────────────────────────────────
    {
        "keywords": ["literatura", "novela", "poesía", "poema", "escritor", "autor", "libro",
                     "gabriel garcía márquez", "vargas llosa", "cesar vallejo", "pablo neruda",
                     "realismo mágico", "boom latinoamericano", "cien años de soledad"],
        "ai_text": """## Literatura Latinoamericana

### El Boom Latinoamericano (1960–1970)

Movimiento literario que dio proyección mundial a narrativas de América Latina.

| Autor | País | Obra maestra |
|---|---|---|
| **Gabriel García Márquez** | Colombia | *Cien años de soledad* (1967) — Nobel 1982 |
| **Mario Vargas Llosa** | Perú | *La ciudad y los perros* (1963) — Nobel 2010 |
| **Julio Cortázar** | Argentina | *Rayuela* (1963) |
| **Carlos Fuentes** | México | *La región más transparente* (1958) |

### César Vallejo — Voz del Perú

**César Abraham Vallejo** (Santiago de Chuco, 1892 – París, 1938) es el poeta peruano más universal.

Obras clave:
- *Los heraldos negros* (1919) — poesía modernista con angustia existencial
- *Trilce* (1922) — vanguardismo radical, lenguaje fragmentado
- *Poemas humanos* (1939, póstumo) — compromiso social y dolor colectivo

> *"Hay golpes en la vida, tan fuertes... ¡Yo no sé!"* — César Vallejo

### Realismo Mágico

Técnica literaria que integra elementos mágicos en un contexto realista. García Márquez la popularizó en *Cien años de soledad*, pero sus raíces están en Borges, Rulfo y Asturias.
""",
        "suggestions": ["Mario Vargas Llosa obras", "César Vallejo poemas", "Nobel de Literatura latinoamericanos", "Cien años de soledad resumen"],
    },
    {
        "keywords": ["arte", "pintura", "música", "escultura", "arquitectura", "beethoven",
                     "mozart", "bach", "picasso", "van gogh", "da vinci", "renacimiento artístico",
                     "barroco", "impresionismo", "museo"],
        "ai_text": """## Arte y Música en la Historia

### Grandes Pintores

| Artista | Movimiento | Obra icónica |
|---|---|---|
| Leonardo da Vinci | Renacimiento | *La Mona Lisa*, *La Última Cena* |
| Miguel Ángel | Renacimiento | Techo de la Capilla Sixtina, *El David* |
| Rembrandt | Barroco | *La ronda de noche* |
| Claude Monet | Impresionismo | *Nenúfares* |
| Pablo Picasso | Cubismo | *El Guernica* |
| Frida Kahlo | Surrealismo/Folk | *Las dos Fridas* |

### Música Clásica — Los Grandes

- **J.S. Bach** (1685–1750): Barroco; contrapunto y fuga (*Clave bien temperado*)
- **W.A. Mozart** (1756–1791): Clasicismo; *Sinfonía n.º 40*, *Don Giovanni*
- **L. van Beethoven** (1770–1827): Clásico-Romántico; *9.ª Sinfonía* (compuesta siendo sordo)
- **F. Chopin** (1810–1849): Romanticismo; *Nocturnos* para piano

### Arte Peruano

- **Indigenismo**: Escuela Cusqueña (siglos XVII–XVIII), fusión hispano-andina
- **José Sabogal** (1888–1956): padre del indigenismo peruano moderno
- **Música tradicional**: huayno, marinera norteña (danza nacional del Perú), festejo
""",
        "suggestions": ["Música peruana tradicional", "Renacimiento italiano", "Arte precolombino", "Arquitectura inca"],
    },
    # ── CIENCIAS NATURALES ────────────────────────────────────────────────────
    {
        "keywords": ["biología", "célula", "adn", "dna", "genética", "gen", "evolución",
                     "darwin", "organismo", "especie", "ecosistema", "fotosíntesis",
                     "mitosis", "meiosis", "proteína", "virus", "bacteria"],
        "ai_text": """## Biología — Fundamentos

### La Célula — Unidad de Vida

Toda vida conocida está compuesta por células:

| Tipo | Características | Ejemplos |
|---|---|---|
| **Procariota** | Sin núcleo definido, sin orgánulos membranosos | Bacterias, Arqueas |
| **Eucariota animal** | Núcleo, mitocondrias, sin pared celular | Humanos, animales |
| **Eucariota vegetal** | Núcleo, cloroplastos, pared celular | Plantas, algas |

### ADN y Genética

El **ADN** (ácido desoxirribonucleico) es la molécula que almacena la información hereditaria:

$$\\text{ADN} \\xrightarrow{\\text{transcripción}} \\text{ARNm} \\xrightarrow{\\text{traducción}} \\text{Proteína}$$

- Estructura: doble hélice de nucleótidos (A–T, C–G)
- El genoma humano ≈ 3.2 mil millones de pares de bases, ~20,000 genes
- **CRISPR-Cas9**: herramienta de edición genómica (Nobel Química 2020)

### Teoría de la Evolución (Darwin, 1859)

Los seres vivos cambian a través del tiempo por **selección natural**:
1. Variación genética en la población
2. Los individuos mejor adaptados sobreviven y se reproducen más
3. Los rasgos ventajosos se transmiten a la descendencia
""",
        "suggestions": ["Genética mendeliana", "Evolución humana", "Ecosistemas del Perú", "Bioquímica celular"],
    },
    # ── GEOGRAFÍA ─────────────────────────────────────────────────────────────
    {
        "keywords": ["geografía", "perú", "lima", "amazonas", "andes", "continente",
                     "océano", "capital", "país", "africa", "asia", "europa", "america",
                     "clima", "relieve", "población", "biodiversidad"],
        "ai_text": """## Geografía — El Perú y el Mundo

### Perú — Datos Clave

| Dato | Valor |
|---|---|
| Capital | Lima (11.5 millones hab.) |
| Superficie | 1'285,216 km² (20.º del mundo) |
| Población | ≈ 33 millones (2024) |
| Idiomas oficiales | Español, Quechua, Aimara |
| Moneda | Sol (PEN) |
| Regiones naturales | Costa, Sierra, Selva |

### Las 3 Regiones Naturales

**Costa** — Franja desértica árida (10% del territorio, 60% de la población)
- Incluye Lima, Trujillo, Arequipa
- Influencia de la Corriente de Humboldt (frío)

**Sierra** — Cordillera de los Andes (28% del territorio)
- Nevado Huascarán: 6768 msnm (cima más alta del Perú)
- Lago Titicaca: el lago navegable más alto del mundo (3812 msnm)

**Selva / Amazonía** — 62% del territorio, gran biodiversidad
- El río Amazonas nace en Perú (Nevado Mismi)
- Perú es el 9.º país más biodiverso del mundo

### Continentes y Océanos

| Continente | Superficie | Población |
|---|---|---|
| Asia | 44.6 M km² | 4,700 M |
| África | 30.4 M km² | 1,460 M |
| América (total) | 42.5 M km² | 1,020 M |
| Europa | 10.5 M km² | 748 M |
| Oceanía | 9.0 M km² | 44 M |
""",
        "suggestions": ["Regiones naturales del Perú", "Cuenca del Amazonas", "Biodiversidad peruana", "Ciudades del Perú"],
    },
]


def _match(query: str) -> dict:
    q_lower = query.lower()

    # 1. Buscar en CDN (L1)
    best_cdn: dict | None = None
    best_hits = 0
    for entry in MOCK_DB:
        hits = sum(1 for kw in entry["keywords"] if kw in q_lower)
        if hits > best_hits:
            best_hits = hits
            best_cdn = entry
    if best_cdn and best_hits > 0:
        return best_cdn

    # 2. Buscar en conocimiento general (L3 pre-escrito)
    for entry in GENERAL_KNOWLEDGE:
        for kw in entry["keywords"]:
            if kw in q_lower:
                return {"results": [], "level": "L3", "ai_text": entry["ai_text"], "suggestions": entry["suggestions"]}

    # 3. Fallback dinámico (plantilla o LLM)
    return _dynamic_response(query)


def _is_dynamic_query(query: str) -> bool:
    """Retorna True si la query no tiene match en MOCK_DB ni GENERAL_KNOWLEDGE.
    En ese caso el stream debe usar el LLM real si está disponible."""
    q_lower = query.lower()
    for entry in MOCK_DB:
        if sum(1 for kw in entry["keywords"] if kw in q_lower) > 0:
            return False
    for entry in GENERAL_KNOWLEDGE:
        for kw in entry["keywords"]:
            if kw in q_lower:
                return False
    return True


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


async def _search_cdn(query: str) -> list[dict]:
    """Busca contenido real indexado en ChromaDB. Retorna [] si no hay resultados."""
    try:
        # Acceder directamente al singleton retriever (más robusto que usar _retriever global)
        from ai_engine.services.hybrid_retriever import retriever

        # Lazy initialization: si no está listo, inicializarlo ahora
        if not retriever.is_ready:
            logger.info("Retriever no inicializado, inicializando ahora...")
            await retriever.init()
            logger.info("Retriever inicializado: %d chunks", await retriever.chunk_count())

        chunks = await retriever.search(query, top_k=15)
        if not chunks:
            logger.debug("ChromaDB: 0 resultados para '%s'", query[:50])
            return []

        # Convertir chunks del retriever al formato de tarjetas CDN
        seen: dict[str, dict] = {}
        for chunk in chunks:
            cid = chunk.get("content_id", "")
            score = chunk.get("score", 0)
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

        # Filtrar resultados irrelevantes usando múltiples criterios:
        # 1. Umbral mínimo absoluto: 0.75 (nada por debajo se muestra)
        # 2. Detección de "salto" en scores: si hay un gap > 0.04 entre items, cortar ahí
        # 3. Límite máximo: 5 items (evitar spam de resultados)
        if cards:
            filtered = []
            prev_score = None
            for c in cards:
                score = c["relevance_score"]
                # Criterio 1: umbral absoluto
                if score < 0.75:
                    logger.info("  %s: %.4f ✗ (por debajo de umbral 0.75)", c["title"], score)
                    continue
                # Criterio 2: detección de salto
                if prev_score is not None and (prev_score - score) > 0.04:
                    logger.info("  %s: %.4f ✗ (salto de %.4f desde anterior)",
                               c["title"], score, prev_score - score)
                    break  # Cortar aquí, no añadir más
                # Criterio 3: límite de items
                if len(filtered) >= 5:
                    logger.info("  %s: %.4f ✗ (límite de 5 items)", c["title"], score)
                    break
                # Pasa todos los criterios
                logger.info("  %s: %.4f ✓", c["title"], score)
                filtered.append(c)
                prev_score = score
            cards = filtered

        logger.info("ChromaDB search: %d chunks → %d cards para '%s'", len(chunks), len(cards), query[:50])
        return cards
    except Exception as exc:
        logger.warning("ChromaDB search falló: %s", exc)
        return []


# ── LENGUAJES / TECNOLOGÍAS detectables ──────────────────────────────────────
_LANG_NAMES = {
    "rust": "Rust", "python": "Python", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "c++": "C++", "c#": "C#", "go": "Go", "kotlin": "Kotlin",
    "swift": "Swift", "ruby": "Ruby", "php": "PHP", "sql": "SQL", "html": "HTML",
    "css": "CSS", "r": "R", "matlab": "MATLAB", "scala": "Scala", "dart": "Dart",
    "flutter": "Flutter", "react": "React", "vue": "Vue.js", "angular": "Angular",
    "node": "Node.js", "django": "Django", "fastapi": "FastAPI", "spring": "Spring Boot",
}

_CODE_TEMPLATES: dict[str, dict] = {
    "neurona": {
        "rust": ('## Neurona Artificial en Rust\n\nUna **neurona artificial** es la unidad básica de una red neuronal. Recibe entradas, aplica pesos y una función de activación, y produce una salida.\n\n### Implementación en Rust\n\n```rust\n/// Neurona artificial simple con función de activación sigmoide\npub struct Neuron {\n    pub weights: Vec<f64>,\n    pub bias: f64,\n}\n\nimpl Neuron {\n    pub fn new(n_inputs: usize) -> Self {\n        // Inicialización aleatoria básica (en producción usa rand::)\n        Neuron {\n            weights: (0..n_inputs).map(|i| (i as f64 * 0.1) - 0.2).collect(),\n            bias: 0.1,\n        }\n    }\n\n    /// Función de activación sigmoide: σ(x) = 1 / (1 + e^(-x))\n    fn sigmoid(x: f64) -> f64 {\n        1.0 / (1.0 + (-x).exp())\n    }\n\n    /// Propagación hacia adelante (forward pass)\n    pub fn forward(&self, inputs: &[f64]) -> f64 {\n        assert_eq!(inputs.len(), self.weights.len(), "Dimensiones incompatibles");\n        let weighted_sum: f64 = self.weights\n            .iter()\n            .zip(inputs.iter())\n            .map(|(w, x)| w * x)\n            .sum::<f64>() + self.bias;\n        Self::sigmoid(weighted_sum)\n    }\n\n    /// Actualización de pesos (descenso de gradiente)\n    pub fn update_weights(&mut self, inputs: &[f64], error: f64, lr: f64) {\n        for (w, x) in self.weights.iter_mut().zip(inputs.iter()) {\n            *w += lr * error * x;\n        }\n        self.bias += lr * error;\n    }\n}\n\nfn main() {\n    let mut neuron = Neuron::new(3);\n    let inputs = vec![1.0, 0.5, -1.0];\n    let output = neuron.forward(&inputs);\n    println!("Salida de la neurona: {:.4}", output);\n\n    // Entrenamiento con una iteración\n    let target = 1.0;\n    let error = target - output;\n    neuron.update_weights(&inputs, error, 0.01);\n    println!("Después de ajuste: {:.4}", neuron.forward(&inputs));\n}\n```\n\n### Conceptos clave\n\n| Concepto | Descripción |\n|---|---|\n| **Pesos** (`weights`) | Importancia de cada entrada; se ajustan durante el entrenamiento |\n| **Sesgo** (`bias`) | Desplazamiento del umbral de activación |\n| **Sigmoide** | $\\sigma(x) = \\frac{1}{1+e^{-x}}$ — mapea cualquier valor a $(0, 1)$ |\n| **Forward pass** | Cálculo de salida dado un input |\n| **Backprop** | Ajuste de pesos usando el error (gradiente) |\n\n> **Rust y ML**: Para redes neuronales reales en Rust usa los crates [`tch-rs`](https://crates.io/crates/tch) (bindings a PyTorch) o [`burn`](https://crates.io/crates/burn) (framework nativo en Rust).',
         ["Redes neuronales en Python", "Backpropagation paso a paso", "Deep Learning fundamentos", "Rust para sistemas embebidos"]),
        "python": ('## Neurona Artificial en Python\n\n```python\nimport numpy as np\n\nclass Neuron:\n    def __init__(self, n_inputs: int):\n        self.weights = np.random.randn(n_inputs) * 0.1\n        self.bias = 0.0\n\n    def sigmoid(self, x: float) -> float:\n        return 1 / (1 + np.exp(-x))\n\n    def forward(self, inputs: np.ndarray) -> float:\n        return self.sigmoid(np.dot(self.weights, inputs) + self.bias)\n\n    def train(self, inputs, target, lr=0.01):\n        output = self.forward(inputs)\n        error = target - output\n        self.weights += lr * error * inputs\n        self.bias += lr * error\n        return output\n\n# Uso\nneuron = Neuron(3)\nx = np.array([1.0, 0.5, -1.0])\nprint(f"Salida: {neuron.forward(x):.4f}")\n```', ["Redes neuronales PyTorch", "NumPy básico", "Deep Learning", "Backpropagation"]),
    },
    "ransomware": {
        "general": ('## Ransomware — Qué es y cómo defenderse\n\nEl **ransomware** es un tipo de malware que **cifra los archivos** de la víctima y exige un rescate (habitualmente en criptomonedas) a cambio de la clave de descifrado.\n\n### ¿Cómo funciona?\n\n```\n[Víctima] ←── email phishing / exploit ──→ [Infección]\n     ↓\n[Ransomware cifra archivos con AES-256 + RSA-2048]\n     ↓\n[Nota de rescate: "Paga X BTC en 72h o se borra la clave"]\n```\n\n### Cadena de ataque (Kill Chain)\n\n| Fase | Descripción |\n|---|---|\n| **Entrega** | Email phishing, USB infectado, exploit de vulnerabilidad |\n| **Ejecución** | Se ejecuta el dropper que descarga el payload |\n| **Cifrado** | Cifra documentos, fotos, DB con clave efímera |\n| **Extorsión** | Muestra nota de rescate con dirección de pago |\n| **C2** | Comunica al servidor de mando (Command & Control) |\n\n### Ejemplos históricos\n\n- **WannaCry (2017)**: explotó `EternalBlue` (NSA leak); afectó 200,000 equipos en 150 países\n- **NotPetya (2017)**: disfrazado de ransomware, realmente un wiper destructivo\n- **REvil / Sodinokibi (2021)**: atacó Kaseya VSA, afectando 1,500 empresas\n- **LockBit 3.0**: uno de los grupos más activos actualmente (RaaS — Ransomware-as-a-Service)\n\n### Defensa y prevención\n\n1. **Backups 3-2-1**: 3 copias, 2 medios distintos, 1 offsite (sin conexión a la red infectada)\n2. **Parchear** sistemas operativos y software regularmente\n3. **Segmentar** la red — limitar movimiento lateral\n4. **EDR/XDR** — detección conductual (no solo firmas)\n5. **Principio de mínimo privilegio** — los usuarios no deben ser administradores\n6. **Concienciación** — el phishing es el vector de entrada #1\n\n> ⚠️ **¿Pagar el rescate?** No se recomienda: solo el ~65% recupera los datos, y financia a los atacantes.',
         ["Tipos de malware", "Ciberseguridad básica", "Ingeniería social y phishing", "Cifrado AES y RSA"]),
    },
    "cifrado": {
        "general": ('## Cifrado / Criptografía\n\nEl **cifrado** es el proceso de transformar información legible (**plaintext**) en un formato ilegible (**ciphertext**) usando un algoritmo y una clave.\n\n### Tipos de cifrado\n\n| Tipo | Algoritmos | Uso típico |\n|---|---|---|\n| **Simétrico** | AES, ChaCha20, 3DES | Cifrar archivos, disco completo |\n| **Asimétrico** | RSA, ECDSA, Diffie-Hellman | TLS/HTTPS, firmas digitales |\n| **Hash** | SHA-256, SHA-3, bcrypt | Contraseñas, integridad de archivos |\n\n### AES (Advanced Encryption Standard)\n\n$$C = E_K(P) \\quad \\text{donde } K \\in \\{128, 192, 256\\} \\text{ bits}$$\n\n```python\nfrom Crypto.Cipher import AES\nimport os\n\nkey = os.urandom(32)   # 256 bits\nnonce = os.urandom(16)\ncipher = AES.new(key, AES.MODE_GCM, nonce=nonce)\nciphertext, tag = cipher.encrypt_and_digest(b"Mensaje secreto")\nprint("Cifrado:", ciphertext.hex())\n```\n\n### TLS — Cómo funciona HTTPS\n\n1. Cliente envía `ClientHello` con versiones TLS soportadas\n2. Servidor responde con certificado X.509 (clave pública RSA/EC)\n3. Se negocia clave de sesión via Diffie-Hellman\n4. Todo el tráfico posterior se cifra con AES-GCM',
         ["RSA paso a paso", "Ransomware y cifrado malicioso", "HTTPS y certificados SSL", "Criptografía cuántica"]),
    },
}


def _extract_lang(q: str) -> str:
    """Devuelve el nombre canónico del lenguaje detectado en la consulta."""
    for key, name in _LANG_NAMES.items():
        if key in q:
            return name
    return "general"


def _is_code_request(q: str) -> bool:
    code_kws = ["código", "codigo", "programa", "implementa", "implementar", "escribe",
                "crea ", "crear ", "ejemplo de", "snippet", "función", "funcion",
                "clase ", "class ", "algoritmo", "script", "cómo se hace", "como se hace"]
    return any(kw in q for kw in code_kws)


def _is_definition(q: str) -> bool:
    def_kws = ["qué es", "que es", "qué son", "que son", "define ", "definición",
               "concepto de", "explica ", "explicar ", "qué significa", "que significa",
               "cómo funciona", "como funciona", "para qué sirve", "para que sirve"]
    return any(kw in q for kw in def_kws)


def _is_comparison(q: str) -> bool:
    cmp_kws = ["diferencia entre", "vs ", "versus", "mejor que", "cuál es mejor",
               "comparar", "comparación", "cuáles son las ventajas"]
    return any(kw in q for kw in cmp_kws)


def _detect_topic_key(q: str) -> str | None:
    """Busca si la consulta contiene una clave de _CODE_TEMPLATES."""
    for key in _CODE_TEMPLATES:
        if key in q:
            return key
    return None


def _dynamic_response(query: str) -> dict:
    """Genera una respuesta dinámica basada en el tipo de consulta."""
    q = query.lower()
    topic_raw = re.sub(r"[¿?¡!]", "", query.strip()).strip()
    lang_name = _extract_lang(q)
    lang_key = lang_name.lower().replace(".js", "").replace("+", "p")

    # ── ¿Hay una plantilla específica para este tema? ──
    tkey = _detect_topic_key(q)
    if tkey:
        variants = _CODE_TEMPLATES[tkey]
        # buscar variante por lenguaje, luego "general", luego la primera
        entry = variants.get(lang_key) or variants.get("general") or next(iter(variants.values()))
        ai_text, suggestions = entry
        return {"results": [], "level": "L3", "ai_text": ai_text, "suggestions": suggestions}

    # ── Solicitud de código genérica ──────────────────────────────────────────
    if _is_code_request(q):
        lang_display = lang_name if lang_name != "general" else "Python"
        lang_md = lang_display.lower().replace(" ", "").replace(".", "")
        # Extraer objeto de la solicitud (palabras clave relevantes)
        topic_clean = re.sub(
            r"\b(código|codigo|programa|implementa|implementar|escribe|crea|crear|ejemplo de|"
            r"en python|en java|en rust|en javascript|en typescript|en c\+\+|dame|hazme|muéstrame)\b",
            "", q, flags=re.IGNORECASE
        ).strip(" ,.")
        return {
            "results": [], "level": "L3",
            "ai_text": (
                f"## {topic_raw.capitalize()}\n\n"
                f"A continuación un ejemplo en **{lang_display}** sobre: *{topic_clean.strip()}*\n\n"
                f"```{lang_md}\n"
                f"# Implementación: {topic_clean.strip()}\n"
                f"# Este es un esqueleto base — adáptalo a tu necesidad\n\n"
                f"def main():\n"
                f"    # TODO: implementar {topic_clean.strip()}\n"
                f"    pass\n\n"
                f"if __name__ == '__main__':\n"
                f"    main()\n"
                f"```\n\n"
                f"### ¿Necesitas más detalle?\n\n"
                f"Para obtener una implementación completa de **{topic_clean.strip()}** en **{lang_display}**, "
                f"intenta ser más específico. Por ejemplo:\n\n"
                f"- *\"Código de [concepto] en {lang_display} paso a paso\"*\n"
                f"- *\"Ejemplo completo de [algoritmo] con explicación\"*\n\n"
                f"> 💡 Cuando el CDN esté conectado a un modelo de lenguaje local (ej. LLaMA 3 vía Ollama), "
                f"generará código completo y funcional para cualquier solicitud."
            ),
            "suggestions": [
                f"{lang_display} ejemplos básicos",
                f"Algoritmos en {lang_display}",
                "Python fundamentos",
                "Programación orientada a objetos",
            ],
        }

    # ── Consulta de definición/explicación ───────────────────────────────────
    if _is_definition(q):
        subject = re.sub(
            r"\b(qué es|que es|qué son|que son|define|definición|explica|explíca|"
            r"cómo funciona|como funciona|para qué sirve|para que sirve|qué significa)\b",
            "", q, flags=re.IGNORECASE
        ).strip(" ,.")
        subject_cap = subject.capitalize() if subject else topic_raw
        return {
            "results": [], "level": "L3",
            "ai_text": (
                f"## {subject_cap}\n\n"
                f"**{subject_cap}** es un concepto que puede abordarse desde múltiples áreas del conocimiento.\n\n"
                f"### Definición general\n\n"
                f"> El término **\"{subject}\"** hace referencia a [definición]. "
                f"Se utiliza principalmente en el contexto de [área de aplicación].\n\n"
                f"### Aspectos clave\n\n"
                f"- **Origen**: [área o disciplina de origen]\n"
                f"- **Aplicación**: [usos prácticos]\n"
                f"- **Relación con**: [conceptos relacionados]\n\n"
                f"### ¿Cómo funciona?\n\n"
                f"[Descripción del funcionamiento o proceso]\n\n"
                f"> 💡 **Nota**: Esta es una respuesta de referencia del CDN en modo demo. "
                f"Con un LLM local conectado (Ollama + LLaMA 3), el sistema generaría una "
                f"explicación detallada y precisa sobre **{subject_cap}** en tiempo real."
            ),
            "suggestions": [
                f"Historia de {subject_cap}",
                f"{subject_cap} aplicaciones",
                f"Cómo usar {subject_cap}",
                f"{subject_cap} ejemplos",
            ],
        }

    # ── Comparación ───────────────────────────────────────────────────────────
    if _is_comparison(q):
        return {
            "results": [], "level": "L3",
            "ai_text": (
                f"## Comparación: {topic_raw}\n\n"
                f"### Tabla comparativa\n\n"
                f"| Criterio | Opción A | Opción B |\n"
                f"|---|---|---|\n"
                f"| **Rendimiento** | — | — |\n"
                f"| **Facilidad de uso** | — | — |\n"
                f"| **Casos de uso** | — | — |\n"
                f"| **Ecosistema** | — | — |\n\n"
                f"> 💡 Con un LLM local conectado, esta tabla se completaría automáticamente "
                f"con datos precisos sobre: *{topic_raw}*"
            ),
            "suggestions": [f"Ventajas de {topic_raw}", "Programación comparativa", "Tecnologías 2025"],
        }

    # ── Respuesta genérica educativa ──────────────────────────────────────────
    topic_cap = topic_raw.capitalize()
    return {
        "results": [],
        "level": "L3",
        "ai_text": (
            f"## {topic_cap}\n\n"
            f"Has buscado: **{topic_raw}**\n\n"
            f"El CDN GTR-PUCP funciona en modo offline con un conjunto de contenido local. "
            f"Para búsquedas como ésta, el sistema de IA generaría una respuesta completa "
            f"al conectarse a un modelo de lenguaje local.\n\n"
            f"### Recursos de referencia\n\n"
            f"- **Wikipedia en español** — [es.wikipedia.org](https://es.wikipedia.org/wiki/{topic_cap.replace(' ', '_')})\n"
            f"- **Khan Academy** — lecciones gratuitas en video\n"
            f"- **Britannica** — enciclopedia académica\n\n"
            f"### Temas disponibles en este CDN\n\n"
            f"**Matemáticas** · **Física** · **Redes TCP/IP** · **Programación Python** · "
            f"**Álgebra Lineal** · **Machine Learning** · **Linux** · "
            f"**Historia del Perú** · **Literatura** · **Biología** · **Geografía** · **Deportes**\n\n"
            f"> *El sistema de IA completo usa un modelo LLaMA 3 local vía Ollama "
            f"para responder cualquier consulta sin conexión a internet.*"
        ),
        "suggestions": [
            f"{topic_cap} explicación",
            f"Código de ejemplo {topic_cap}",
            f"{topic_cap} tutorial",
            "Contenido disponible en CDN",
        ],
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok", "platform": "mock_laptop",
        "components": {"llm_engine": "mock", "retriever": "mock", "stt": "mock", "thermal": "nominal", "chroma_chunks": 42},
    }


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
    m = _match(req.query)
    spell = _spell_check(req.query)
    return {
        "query": req.query,
        "spell_suggestion": spell,
        "cdn_results": cdn_cards,
        "ai_overview": {
            "text": m["ai_text"], "level": m["level"],
            "grounding": {"coverage_score": 0.9 if cdn_cards else 0.0, "is_grounded": bool(cdn_cards)},
            "language_detected": "es",
        },
        "ui_hints": {"suggested_queries": m["suggestions"]},
    }


@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    spell = _spell_check(req.query)
    use_llm = _llm is not None and _llm.is_ready

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
                # Si el LLM falla en medio del stream, continuar con plantilla
                fallback = _dynamic_response(req.query)
                for line in fallback["ai_text"].split("\n"):
                    yield f"data: {json.dumps({'type': 'token', 'text': line + chr(10)})}\n\n"
                    await asyncio.sleep(0.04)
            suggestions = await _llm_suggestions(req.query)
            yield f"data: {json.dumps({'type': 'done', 'level': 'L3', 'grounding': {'coverage_score': 0.0}, 'suggestions': suggestions, 'spell_suggestion': spell})}\n\n"

        return StreamingResponse(
            llm_event_generator(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    else:
        # ── MODO PLANTILLA: respuesta pre-escrita (rápida, sin modelo) ────────────
        # Tarjetas CDN: siempre desde ChromaDB (contenido real indexado)
        cdn_cards = await _search_cdn(req.query)
        # Texto AI: desde plantillas mock (hasta que haya LLM)
        m = _match(req.query)
        lines = m["ai_text"].split("\n")

        async def template_event_generator():
            yield f"data: {json.dumps({'type': 'cdn_results', 'data': cdn_cards})}\n\n"
            await asyncio.sleep(0.15)
            for line in lines:
                yield f"data: {json.dumps({'type': 'token', 'text': line + chr(10)})}\n\n"
                await asyncio.sleep(0.04)
            yield f"data: {json.dumps({'type': 'done', 'level': m['level'], 'grounding': {'coverage_score': 0.9 if cdn_cards else 0.0}, 'suggestions': m['suggestions'], 'spell_suggestion': spell})}\n\n"

        return StreamingResponse(
            template_event_generator(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )


@app.post("/api/voice-search")
async def voice_search():
    return {
        "query_transcribed": "¿Qué es la Transformada de Fourier?",
        "cdn_results": MOCK_DB[0]["results"],
        "ai_overview": {"text": MOCK_DB[0]["ai_text"], "level": "L1"},
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
