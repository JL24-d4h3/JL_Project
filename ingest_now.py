#!/usr/bin/env python3
import sys
sys.path.append('.')
import asyncio
import logging
from ai_engine.services.ingestion.pipeline import ingest_content

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    # IDs obtenidos de: PGPASSWORD=cdn_pass psql -h localhost -U cdn_user cdn_dev -t -c "SELECT id::text FROM content ORDER BY created_at DESC;"
    content_ids = [
        "fe2ebb1d-c4e6-4690-b66c-495f0322c1e7",  # Sílabo de GTICS
        "1fe46b19-240b-4601-89a7-79957a4f1e41",  # Algoritmo de Dijkstra
        "8f016226-7d5b-4193-92d7-da301c8732bd",  # Lista de colegios
        "a78c9779-72c0-4591-9f9e-26ffe6b3acbf",  # Clases de SDN
        "0cd86337-8d95-44f2-9162-e8d1aff1764b",  # Laboratorios de GTICS
        "7b46eec1-e3a5-48ee-be62-efd2a2e27816",  # Data Augmentation
        "9abc232a-f16f-467f-9d0a-4f0596e27e1d",  # YOLO ← Importante!
        "18273bea-be20-4a55-b92a-736c57ba7403",  # U-net ← Importante!
        "28666028-de82-4dc9-8508-fb3edff4fb62",  # Simulador de peticiones
    ]
    
    print("=== INGESTANDO 9 ARCHIVOS ===\n")
    
    total_chunks = 0
    for content_id in content_ids:
        try:
            result = await ingest_content(content_id)
            chunks = result.get('chunks_added', 0)
            title = result.get('title', 'Unknown')
            total_chunks += chunks
            status = "✓" if chunks > 0 else "⚠"
            print(f"{status} {title:30} +{chunks:4} chunks")
        except Exception as e:
            print(f"✗ {content_id}: {str(e)[:60]}")
    
    print(f"\n=== TOTAL: {total_chunks} chunks ingestados ===")

if __name__ == "__main__":
    asyncio.run(main())
