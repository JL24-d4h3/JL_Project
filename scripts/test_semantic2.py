import sys
import os
sys.path.append('.')
import asyncio
import json
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.initialize()
    res = await retriever.search("visión artificial")
    out = []
    for r in res:
        out.append({
            "score": r.get('score'),
            "title": r.get('title'),
            "text": r.get('text')[:100]
        })
    with open('search_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

asyncio.run(main())
