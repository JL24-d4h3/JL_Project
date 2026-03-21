import asyncio
import sys
from ai_engine.config import settings

async def main():
    import httpx
    print(settings.CDN_BACKEND_URL)
    url = f"{settings.CDN_BACKEND_URL}/api/content?limit=500"
    print(url)
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        try:
            print(res.json()[:2])
        except Exception:
            pass
if __name__ == "__main__":
    asyncio.run(main())
