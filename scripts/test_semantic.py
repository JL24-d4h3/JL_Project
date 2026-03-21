import sys
import os
sys.path.append('.')
from pydantic import BaseModel

import asyncio
from ai_engine.services.hybrid_retriever import retriever

async def main():
    await retriever.initialize()
    print("Ready.")
    res = await retriever.search("visión artificial")
    for r in res:
        print(f"[{r.get('score')}] {r.get('title')}: {r.get('text')[:60]}")

asyncio.run(main())
