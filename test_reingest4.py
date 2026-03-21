import asyncio
import sys
from ai_engine.services.ingestion.pipeline import ingest_content

async def main():
    import httpx
    url = f"http://localhost:3000/api/content?limit=500"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
        content = data.get("data", [])
        for item in content:
            target_id = item.get("id") or item.get("content_id")
            title = item.get("title", "")
            if "Clases" in title or "SDN" in title:
                print(f"Ingesting {title} (ID: {target_id})")
                try:
                    await ingest_content(str(target_id))
                    print("Done!")
                except Exception as e:
                    print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
