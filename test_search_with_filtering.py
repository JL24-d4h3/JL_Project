#!/usr/bin/env python3
"""
Test de Búsqueda con Clasificación: Demuestra el efecto del filtrado por dominio.

Comparación:
- SIN filtrado: búsqueda vectorial en TODO el contenido (puede ser ruidosa)
- CON filtrado: búsqueda vectorial solo en contenido del dominio correcto

Esto demuestra que "SIMULADOR DE PETICIONES" (NET/networking) 
no aparecerá en búsquedas de "visión artificial" (AI/computer_vision).
"""
import asyncio
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "ai_engine"))

from config import settings
from services.hybrid_retriever import retriever
from services.classifier import classify_query


async def test_search_filtering():
    """
    Prueba que el filtrado por dominio funciona correctamente.
    """
    logger.info("=" * 70)
    logger.info("TEST: Búsqueda con Filtrado por Clasificación")
    logger.info("=" * 70)

    # Inicializar retriever
    await retriever.init()
    
    if not retriever.is_ready:
        logger.error("Retriever no inicializado — ChromaDB no disponible")
        return False

    # Queries de prueba
    queries = [
        {
            "text": "visión artificial",
            "expected_domain": "AI",
            "should_exclude": "SIMULADOR",  # El archivo MQTT no debería aparecer
        },
        {
            "text": "TCP socket MQTT",
            "expected_domain": "NET",
            "should_exclude": "YOLO",  # Los archivos de visión no deberían aparecer
        },
    ]

    all_passed = True

    for query_data in queries:
        query_text = query_data["text"]
        logger.info(f"\n{'-' * 70}")
        logger.info(f"Query: '{query_text}'")
        logger.info("-" * 70)

        # Clasificar la query
        query_class = classify_query(query_text)
        logger.info(
            f"Clasificación: domain={query_class['domain']}, "
            f"area={query_class['area']}, confidence={query_class['confidence']:.2%}"
        )

        # Buscar
        try:
            results = await retriever.search(query=query_text, top_k=10)
            logger.info(f"Resultados: {len(results)} chunks encontrados\n")

            for i, result in enumerate(results[:5], 1):
                title = result.get("title", "N/A")
                content_type = result.get("content_type", "N/A")
                score = result.get("score", 0.0)
                auto_domain = result.get("auto_domain", "N/A")
                
                logger.info(
                    f"  {i}. [{auto_domain}] {title} "
                    f"(type={content_type}, score={score:.3f})"
                )

            # Verificar que no contiene excluded_term
            excluded = query_data["should_exclude"]
            found_excluded = any(
                excluded.lower() in (r.get("title", "") or "").lower()
                for r in results
            )

            if found_excluded:
                logger.warning(f"  ✗ FALHA: '{excluded}' aparece en resultados")
                all_passed = False
            else:
                logger.info(f"  ✓ Correcto: '{excluded}' está correctamente filtrado")

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            all_passed = False

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("✓ TODOS LOS TESTS PASARON")
    else:
        logger.info("✗ ALGUNOS TESTS FALLARON")
    logger.info("=" * 70)

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(test_search_filtering())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
