#!/usr/bin/env python3
"""
Script de Reclasificación Directa: Actualiza chunks existentes en ChromaDB
sin intentar descargar desde CDN backend.

Usa ChromaDB directamente:
1. Lee los textos de los chunks existentes
2. Los clasifica con BART-MNLI
3. Actualiza los metadatos en ChromaDB
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
from services.classifier import classify_content
import chromadb


async def reclassify_chunks_in_db():
    """
    Reclasificación directa de chunks en ChromaDB.
    """
    logger.info("=" * 70)
    logger.info("RECLASIFICACIÓN DIRECTA CON BART-MNLI")
    logger.info("=" * 70)

    # Conectar a ChromaDB
    try:
        chroma = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
        collection = chroma.get_collection(name="cdn_chunks")
        
        # Obtener TODOS los datos INCLUYENDO EMBEDDINGS
        all_data = collection.get(include=["documents", "metadatas", "embeddings"])
        
        ids = all_data.get("ids", [])
        docs = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])
        embeddings = all_data.get("embeddings", [])
        
        total = len(ids)
        logger.info(f"Encontrados {total} chunks en ChromaDB")
        
        if total == 0:
            logger.info("No hay chunks para reclasificar")
            return True
        
    except Exception as e:
        logger.error(f"Error accediendo a ChromaDB: {e}")
        return False

    # Reclasificar
    logger.info("\nClasificando chunks...")
    logger.info("-" * 70)
    
    updated_metadatas = []
    success_count = 0
    
    for idx, (chunk_id, doc_text, meta) in enumerate(zip(ids, docs, metadatas), 1):
        try:
            logger.info(f"[{idx}/{total}] {meta.get('title', 'N/A')}")
            
            # Clasificar el contenido
            classification = classify_content(
                text=doc_text[:2000],  # Limitar por performance
                code=None,
                title=meta.get("title", ""),
                description="",
                use_bart=True,  # Usar BART para mejor precisión
            )
            
            # Actualizar metadatos
            meta["auto_domain"] = classification.get("domain", "OTHER")
            meta["auto_area"] = classification.get("area", "unknown")
            meta["auto_confidence"] = classification.get("confidence", 0.0)
            meta["auto_tags"] = ",".join(classification.get("tags", [])[:10])
            meta["auto_method"] = classification.get("method", "unknown")
            
            logger.info(
                f"  → {classification['domain']}/{classification['area']} "
                f"({classification['confidence']:.1%})"
            )
            
            updated_metadatas.append(meta)
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            # Mantener metadatos originales si falla
            updated_metadatas.append(meta)

    # Actualizar ChromaDB
    logger.info("\n" + "-" * 70)
    logger.info("Actualizando ChromaDB...")
    
    try:
        # Upsert con documentos originales + embeddings originales + metadatos nuevos
        collection.upsert(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=updated_metadatas,
        )
        logger.info(f"✓ {success_count}/{total} chunks actualizados en ChromaDB")
    except Exception as e:
        logger.error(f"Error actualizando ChromaDB: {e}")
        return False

    # Verificación
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICACIÓN")
    logger.info("=" * 70)
    
    try:
        # Verificar que los metadatos fueron grabados
        sample = collection.get(limit=1, include=["metadatas"])
        sample_meta = sample["metadatas"][0] if sample["metadatas"] else {}
        
        logger.info(f"\nMetadatos de muestra:")
        logger.info(f"  auto_domain: {sample_meta.get('auto_domain', 'MISSING')}")
        logger.info(f"  auto_area: {sample_meta.get('auto_area', 'MISSING')}")
        logger.info(f"  auto_confidence: {sample_meta.get('auto_confidence', 'MISSING')}")
        
        if "auto_domain" in sample_meta:
            logger.info("\n✓ Metadatos correctamente guardados en ChromaDB")
            return True
        else:
            logger.error("\n✗ Metadatos NO fueron guardados")
            return False
            
    except Exception as e:
        logger.error(f"Error en verificación: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(reclassify_chunks_in_db())
        if success:
            logger.info("\n✓ Reclasificación completada exitosamente")
            sys.exit(0)
        else:
            logger.error("\n✗ Reclasificación falló")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n\nCancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nError fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
