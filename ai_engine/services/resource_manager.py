"""
services/resource_manager.py — Semáforo de exclusión ingesta / inferencia.
GTR-PUCP CDN Educativa Offline

Garantiza que Whisper Small (ingesta batch) y el LLM (inferencia en tiempo real)
no compitan por la memoria unificada de la Jetson al mismo tiempo.

Ver docs/ai-search-engine-plan.md §7 para el análisis del presupuesto de memoria.

Uso:
    from ai_engine.services.resource_manager import resource_manager

    # En el handler de búsqueda:
    async with resource_manager.inference_context():
        result = await run_search_pipeline(payload)

    # En el worker de ingesta (background):
    async with resource_manager.ingestion_context():
        await run_ingestion_pipeline(content_id)
"""
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Semáforo de exclusión mutua entre inferencia LLM e ingesta batch.

    Reglas:
    - Múltiples búsquedas concurrentes: permitido (el LLM ya está cargado, no hay riesgo OOM)
    - Ingesta durante búsqueda: BLOQUEADA (Whisper Small toma ~0.9 GB del buffer de seguridad)
    - Búsqueda durante ingesta: BLOQUEADA (misma razón)
    - Múltiples ingestas concurrentes: BLOQUEADAS (una a la vez para evitar picos de RAM)
    """

    def __init__(self) -> None:
        # Lock de inferencia: permite concurrent reads (múltiples búsquedas) pero
        # bloquea ante cualquier ingesta activa.
        self._inference_semaphore = asyncio.Semaphore(8)   # hasta 8 búsquedas paralelas
        self._ingestion_lock      = asyncio.Lock()          # solo 1 ingesta a la vez
        self._ingestion_active    = False

    # ------------------------------------------------------------------
    # Context managers (forma recomendada de uso)
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def inference_context(self):
        """
        Adquiere el contexto de inferencia.
        Espera si hay una ingesta activa (Whisper Small en RAM).
        """
        # Esperar a que no haya ingesta activa antes de ocupar el semáforo
        while self._ingestion_active:
            logger.debug("ResourceManager: inferencia esperando fin de ingesta...")
            await asyncio.sleep(0.2)

        async with self._inference_semaphore:
            logger.debug("ResourceManager: inferencia iniciada")
            try:
                yield
            finally:
                logger.debug("ResourceManager: inferencia terminada")

    @asynccontextmanager
    async def ingestion_context(self):
        """
        Adquiere el contexto de ingesta.
        Espera a que no haya búsquedas activas, luego bloquea nuevas búsquedas.

        Nota: en la práctica espera a que el semáforo de inferencia esté libre,
        adquiriéndolo COMPLETO (todos los slots) para garantizar exclusión total.
        """
        async with self._ingestion_lock:
            # Esperar a que el semáforo de inferencia vuelva a tener todos sus slots
            # (es decir, que no haya búsquedas en curso)
            acquired = []
            try:
                self._ingestion_active = True
                logger.info("ResourceManager: ingesta iniciada — bloqueando nuevas inferencias")

                # Adquirir todos los slots del semáforo para exclusión total
                for i in range(self._inference_semaphore._value + len(acquired)):  # type: ignore[attr-defined]
                    try:
                        # Timeout generoso para no bloquear indefinidamente
                        await asyncio.wait_for(self._inference_semaphore.acquire(), timeout=30.0)
                        acquired.append(True)
                    except asyncio.TimeoutError:
                        logger.warning("ResourceManager: timeout esperando fin de inferencias activas")
                        break

                yield

            finally:
                # Liberar todos los slots adquiridos
                for _ in acquired:
                    self._inference_semaphore.release()
                self._ingestion_active = False
                logger.info("ResourceManager: ingesta terminada — inferencias desbloqueadas")

    # ------------------------------------------------------------------
    # API de bajo nivel (backward compat con código antiguo si fuera necesario)
    # ------------------------------------------------------------------

    async def acquire_inference(self) -> None:
        """Adquiere permiso para iniciar inferencia. Llama release_inference() al terminar."""
        while self._ingestion_active:
            await asyncio.sleep(0.2)
        await self._inference_semaphore.acquire()

    def release_inference(self) -> None:
        """Libera el slot de inferencia."""
        self._inference_semaphore.release()

    async def acquire_ingestion(self) -> None:
        """Adquiere permiso exclusivo para ingesta. Llama release_ingestion() al terminar."""
        await self._ingestion_lock.acquire()
        self._ingestion_active = True

    def release_ingestion(self) -> None:
        """Libera el lock de ingesta."""
        self._ingestion_active = False
        self._ingestion_lock.release()

    @property
    def ingestion_active(self) -> bool:
        return self._ingestion_active


# Singleton — importar desde aquí en el resto del código
resource_manager = ResourceManager()
