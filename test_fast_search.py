import asyncio
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.init()
    results = await retriever.search("Dijkstra", top_k=5)
    for r in results:
        print(f"{r['title']} - score: {r.get('score', 0)}")
        
    print("\n---\n")
    results = await retriever.search("SDN", top_k=5)
    for r in results:
        print(f"{r['title']} - score: {r.get('score', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
