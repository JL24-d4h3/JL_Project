#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from collections import defaultdict

sys.path.insert(0, "ai_engine")

import httpx
from ai_engine.config import settings
from ai_engine.services.classifier import classify_content
from ai_engine.services.hybrid_retriever import retriever


def _build_reclassification_text(title: str, description: str, docs: list[str]) -> str:
    # Priorizar título/descripcion, luego contexto de chunks
    chunks_text = "\n".join(docs[:3])
    return f"{title}\n{description}\n{chunks_text}"[:9000]


async def _fetch_description(content_id: str) -> str:
    url = f"{settings.CDN_BACKEND_URL}/api/content/{content_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return ""
        body = resp.json()
        data = body.get("data", body)
        return (data.get("description") or "").strip()
    except Exception:
        return ""


async def main() -> None:
    await retriever.init()
    if retriever._collection is None:
        print("ERROR: ChromaDB collection no disponible")
        return

    rows = retriever._collection.get(include=["documents", "metadatas"])
    ids = rows.get("ids") or []
    docs = rows.get("documents") or []
    metas = rows.get("metadatas") or []

    grouped: dict[str, dict] = defaultdict(lambda: {"rows": []})
    for idx, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
        content_id = meta.get("content_id") or f"content_{idx}"
        grouped[content_id]["rows"].append((doc_id, doc, meta))

    total_changed = 0
    print(f"Content items detectados: {len(grouped)}")

    for content_id, payload in grouped.items():
        row_docs = [r[1] for r in payload["rows"]]
        first_meta = payload["rows"][0][2]
        title = (first_meta.get("title") or "").strip()
        description = await _fetch_description(content_id)
        text_for_classification = _build_reclassification_text(title, description, row_docs)

        result = classify_content(
            text=text_for_classification,
            code="\n".join(row_docs[:2]),
            title=title,
            description=description,
            use_bart=True,
        )

        new_domain = result.get("domain", "OTHER")
        new_area = result.get("area", "unknown")
        new_conf = float(result.get("confidence", 0.0))
        new_tags = ",".join(result.get("tags", [])[:10])
        new_semantic_terms = ",".join(result.get("semantic_terms", [])[:20])

        chunk_updates = 0
        for doc_id, doc, meta in payload["rows"]:
            old_domain = meta.get("auto_domain", "")
            old_area = meta.get("auto_area", "")
            old_semantic_terms = meta.get("auto_semantic_terms", "")
            if old_domain == new_domain and old_area == new_area and old_semantic_terms == new_semantic_terms:
                continue

            meta["auto_domain"] = new_domain
            meta["auto_area"] = new_area
            meta["auto_confidence"] = new_conf
            meta["auto_tags"] = new_tags
            meta["auto_semantic_terms"] = new_semantic_terms

            retriever._collection.upsert(
                ids=[doc_id],
                documents=[doc],
                metadatas=[meta],
            )
            chunk_updates += 1

        if chunk_updates:
            total_changed += chunk_updates
            print(
                f"- {title[:45]} [{content_id}]: {chunk_updates} chunks -> {new_domain}/{new_area} (conf={new_conf:.2f})"
            )

    await retriever.update_bm25(["__rebuild__"])
    print(f"\nReindex quality terminado. Chunks actualizados: {total_changed}")


if __name__ == "__main__":
    asyncio.run(main())
