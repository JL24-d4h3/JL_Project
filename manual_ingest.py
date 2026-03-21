import sys
sys.path.append('.')
import asyncio
import logging
from ai_engine.services.ingestion.pipeline import ingest_content

logging.basicConfig(level=logging.INFO)

async def main():
    # Estos son los IDs de los archivos que subiste (según el panel)
    # Los puedes obtener de la BD: SELECT id, title FROM content WHERE type='code';
    
    files_to_ingest = [
        # Mejor obtenerlos de la BD automáticamente
    ]
    
    # Conectarse a la BD para obtener todos los content_ids
    import psycopg2
    conn = psycopg2.connect("dbname=cdn_dev user=cdn_user password=cdn_pass")
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM content ORDER BY created_at DESC LIMIT 20;")
    rows = cur.fetchall()
    
    print("=== CONTENT_IDs DISPONIBLES PARA INGESTAR ===")
    for cid, title in rows:
        print(f"  {str(cid)[:8]}... → {title}")
    
    print("\n=== INGESTANDO CONTENIDO ===")
    for cid, title in rows[:10]:  # Ingestar los últimos 10
        print(f"\n→ Ingestando: {title} ({cid})")
        try:
            result = await ingest_content(str(cid))
            print(f"  ✓ Resultado: {result}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    cur.close()
    conn.close()

asyncio.run(main())
