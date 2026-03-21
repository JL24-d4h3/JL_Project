import asyncio
import sys
import logging
from pathlib import Path
import time
import os

sys.path.insert(0, str(Path(__file__).parent))

from ai_engine.services.hybrid_retriever import retriever
from ai_engine.services.ingestion.pipeline import ingest_content

logging.basicConfig(level=logging.INFO, format="%(message)s")

with open('all_ids.txt', 'r') as f:
    IDS = [line.strip() for line in f if line.strip()]

async def sync():
    await retriever.init()
    print(f"Borrando chunks viejos (actual = {retriever._collection.count()})")
    
    # Do not wipe the whole directory to avoid file lock issues, just re-ingest over them
    # ingest_content already clears old chunks before ingesting a new content_id
    
    for cid in IDS:
        print(f"\n[+] Ingesting: {cid}")
        t0 = time.time()
        try:
            res = await ingest_content(cid)
            print(f"Resultado: {res['status']}, {res['chunks_added']} chunks en {time.time()-t0:.2f}s")
        except Exception as e:
            print(f"Error {cid}: {e}")
            
    print(f"\nFinal chunks in ChromaDB: {retriever._collection.count()}")

if __name__ == "__main__":
    asyncio.run(sync())
