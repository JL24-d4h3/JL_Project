import sys
import os
sys.path.append('.')
import asyncio
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.init()
    query = "visión artificial"
    
    query_emb = retriever._embedder.encode(f"query: {query}", normalize_embeddings=True).tolist()
    res = retriever._collection.query(query_embeddings=[query_emb], n_results=10)
    for dist, doc, meta in zip(res['distances'][0], res['documents'][0], res['metadatas'][0]):
        print(f"[{1-dist:.3f}] {meta.get('title')}: {doc[:60]}")

asyncio.run(main())
