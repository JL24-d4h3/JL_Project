import asyncio
import sys
import os

from ai_engine.services.ingestion.pipeline import ingest_content, _fetch_content_metadata

async def main():
    import httpx
    # Let's get "Clases de SDN" content_id
    url = f"http://localhost:5173/api/content"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            data = res.json()
            content = data.get("content", data)
            target_id = None
            for item in content:
                if "SDN" in item.get("title", ""):
                    target_id = item.get("id") or item.get("content_id")
                    break
                    
            if target_id:
                print(f"Reingesting {target_id}")
                meta = await _fetch_content_metadata(target_id)
                print(f"Metadata: {meta}")
                res = await ingest_content(target_id)
                print("Result:", res)
            else:
                print("Not found")
    except Exception as e:
        print("Error:", e)
        
if __name__ == "__main__":
    asyncio.run(main())
