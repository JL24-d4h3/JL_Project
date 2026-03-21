import sys
sys.path.append('.')
import asyncio
import logging
from ai_engine.services.ingestion.pipeline import ingest_content
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    # Obtener content_ids de las carpetas storage
    import subprocess
    result = subprocess.run(['psql', 'cdn_dev', '-t', '-c', 
                            'SELECT id::text, title FROM content ORDER BY created_at DESC LIMIT 20;'],
                           capture_output=True, text=True)
    
    print("=== INGESTANDO ARCHIVOS ===\n")
    
    lines = result.stdout.strip().split('\n')
    for line in lines:
        if '|' not in line or not line.strip():
            continue
        cid, title = line.split('|')
        cid = cid.strip()
        title = title.strip()
        
        if not cid:
            continue
        
        print(f"→ {title}")
        try:
            result = await ingest_content(cid)
            chunks = result.get('chunks_added', 0)
            print(f"  ✓ +{chunks} chunks en ChromaDB\n")
        except Exception as e:
            print(f"  ✗ {e}\n")

asyncio.run(main())
