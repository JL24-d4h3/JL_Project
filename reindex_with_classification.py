#!/usr/bin/env python3
"""
Script de Re-indexación: Actualiza todos los chunks existentes
con la nueva clasificación automática (BART-MNLI).

Uso:
    python3 reindex_with_classification.py

Este script:
1. Obtiene todos los content_id único desde ChromaDB
2. Para cada uno, llama a ingest_content() que:
   - Re-descarga el contenido del CDN
   - Extrae texto y código
   - CLASIFICA con BART-MNLI
   - Re-indexa en ChromaDB con metadatos actualizados
3. Los filtros de búsqueda (auto_domain) ahora funcionarán correctamente
"""
import asyncio
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Agregar ai_engine al path
sys.path.insert(0, str(Path(__file__).parent / "ai_engine"))

from config import settings
from services.ingestion.pipeline import ingest_content


async def reindex_all_content():
    """
    Re-indexa todo el contenido existente con la nueva clasificación BART-MNLI.
    """
    logger.info("=" * 70)
    logger.info("INICIANDO RE-INDEXACIÓN CON BART-MNLI")
    logger.info("=" * 70)

    # Cargar ChromaDB para obtener lista de content_id únicos
    try:
        import chromadb
        chroma = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
        collection = chroma.get_or_create_collection(name="cdn_chunks")
        
        # Obtener todos los metadatos sin documentos (más eficiente)
        all_data = collection.get(include=[])
        metadatas = all_data.get("metadatas", [])
        
        # Extraer content_id únicos
        content_ids = set()
        for meta in metadatas:
            if "content_id" in meta:
                content_ids.add(meta["content_id"])
        
        content_ids = sorted(list(content_ids))
        total = len(content_ids)
        
        logger.info(f"Encontrados {total} content_id únicos para re-indexar")
        
    except Exception as e:
        logger.error(f"Error accediendo a ChromaDB: {e}")
        return False

    if not content_ids:
        logger.info("No hay content_id para re-indexar")
        return True

    # Re-procesar cada content_id
    success_count = 0
    failure_count = 0
    
    for idx, content_id in enumerate(content_ids, 1):
        try:
            logger.info(f"\n[{idx}/{total}] Re-indexando: {content_id}")
            
            # ingest_content() manejará:
            # 1. Obtener metadata del CDN backend
            # 2. Descargar el archivo
            # 3. Extraer texto y código
            # 4. CLASIFICAR CON BART-MNLI ← NUEVO
            # 5. Re-indexar con metadatos actualizados
            chunks_added = await ingest_content(content_id)
            
            logger.info(f"  ✓ Re-indexados {chunks_added} chunks")
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Error para {content_id}: {e}")
            failure_count += 1
            # Continuar con el siguiente

    # Resumen
    logger.info("\n" + "=" * 70)
    logger.info(f"RE-INDEXACIÓN COMPLETADA")
    logger.info(f"  Exitosos: {success_count}/{total}")
    logger.info(f"  Fallidos:  {failure_count}/{total}")
    logger.info("=" * 70)
    logger.info("\nLos filtros de búsqueda por dominio (auto_domain) ahora deberían")
    logger.info("funcionar correctamente (ej: 'SIMULADOR DE PETICIONES' no aparece")
    logger.info("en búsquedas de 'visión artificial')")
    logger.info("=" * 70)

    return failure_count == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(reindex_all_content())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nRe-indexación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nError fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
