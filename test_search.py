import asyncio
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.init()
    res = await retriever.search('colegios')
    for c in res:
        print(f"{c.get('title', '')[:40]}... Score: {c.get('score', 0):.3f} Type: {c.get('type')} ID: {c.get('content_id')}")

if __name__ == '__main__':
    asyncio.run(main())
