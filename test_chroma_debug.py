import sys
sys.path.append('.')
import asyncio
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.init()
    
    # Test 1: Ver qué hay en total en ChromaDB
    print("=== TOTAL CHUNKS EN CHROMADB ===")
    print(f"Total: {retriever._collection.count()}\n")
    
    # Test 2: Búsqueda bruta por "YOLO"
    print("=== BÚSQUEDA RAW POR 'YOLO' ===")
    results_yolo = retriever._collection.get(where_document={"$contains": "YOLO"}, limit=5)
    print(f"Chunks con 'YOLO': {len(results_yolo.get('documents', []))}")
    if results_yolo.get('documents'):
        for i, doc in enumerate(results_yolo['documents'][:2]):
            print(f"  [{i}] {doc[:100]}")
    
    # Test 3: Búsqueda bruta por "GTICS"
    print("\n=== BÚSQUEDA RAW POR 'GTICS' ===")
    results_gtics = retriever._collection.get(where_document={"$contains": "GTICS"}, limit=5)
    print(f"Chunks con 'GTICS': {len(results_gtics.get('documents', []))}")
    if results_gtics.get('documents'):
        for i, doc in enumerate(results_gtics['documents'][:2]):
            print(f"  [{i}] {doc[:100]}")

asyncio.run(main())
