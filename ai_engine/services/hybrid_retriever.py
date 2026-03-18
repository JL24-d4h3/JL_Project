"""
services/hybrid_retriever.py — Retrieval híbrido: BM25 + ChromaDB + Cross-Encoder + Pre-filtrado por Clasificación.
GTR-PUCP CDN Educativa Offline

Pipeline de búsqueda (read):
  classify_query(query) → determinar dominio → filtro WHERE en ChromaDB
  → embed(query) + HyDE → ChromaDB coseno → BM25 → RRF → Cross-Encoder → top-K final

Pipeline de escritura (ingesta):
  add_chunks()            → embed + upsert en ChromaDB con metadatos de clasificación
  delete_by_content_id()  → borrar chunks anteriores antes de reindexar
  update_bm25()           → reconstruir índice BM25 en memoria

Ver docs/ai-search-engine-plan.md §10 y docs/auto-classification-proposal.md para el diseño completo.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional

# Pre-importar transformers para evitar problemas de lazy loading en async context
try:
    from transformers import AutoConfig
except ImportError:
    pass

from ai_engine.config import settings
from ai_engine.services.classifier import classify_query

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "cdn_chunks"


class HybridRetriever:
    """
    Pipeline: classify_query → filtro WHERE → embed(query) + HyDE → ChromaDB + BM25 → RRF → Cross-Encoder → top-K final

    El clasificador de queries permite pre-filtrar por dominio (AI, DB, NET, etc.) antes de la búsqueda vectorial,
    eliminando contenido irrelevante y mejorando la precisión sin cambiar el modelo de embeddings.
    """

    def __init__(self):
        self.is_ready:    bool = False
        self._chroma             = None   # chromadb.PersistentClient
        self._collection         = None   # chromadb.Collection
        self._embedder           = None   # SentenceTransformer
        self._reranker           = None   # CrossEncoder
        self._bm25               = None   # rank_bm25.BM25Okapi
        self._bm25_corpus: list[str] = []   # textos en el mismo orden que _bm25

    # ── Inicialización ────────────────────────────────────────────────────────

    async def init(self) -> None:
        """
        Carga ChromaDB, el modelo de embeddings multilingual-e5-small y
        (si está habilitado) el cross-encoder de reranking.
        Llamado una sola vez en el lifespan de main.py.
        """
        logger.info(
            "Inicializando retriever — ChromaDB: %s | embedder device: %s",
            settings.CHROMADB_PATH,
            settings.EMBEDDING_DEVICE,
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_sync)

    def _init_sync(self) -> None:
        """Carga síncrona de los modelos (ejecutada en executor para no bloquear)."""
        try:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
            self._collection = self._chroma.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB cargado — %d chunks en colección", self._collection.count())
        except Exception as exc:
            logger.error("Error cargando ChromaDB: %s", exc)
            self._chroma = None
            self._collection = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(
                settings.EMBED_MODEL_NAME,
                cache_folder=settings.EMBED_MODEL_DIR,
                device=settings.EMBEDDING_DEVICE,
            )
            logger.info("Embedder '%s' cargado en %s", settings.EMBED_MODEL_NAME, settings.EMBEDDING_DEVICE)
        except Exception as exc:
            import traceback
            logger.error("Error cargando embedder: %s", exc)
            logger.error("Traceback completo:\n%s", traceback.format_exc())
            self._embedder = None

        if settings.CROSS_ENCODER_ENABLED:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(settings.CROSS_ENCODER_MODEL, max_length=512)
                logger.info("Cross-encoder '%s' cargado", settings.CROSS_ENCODER_MODEL)
            except Exception as exc:
                logger.warning("Cross-encoder no disponible: %s", exc)
                self._reranker = None

        # Inicializar BM25 con los textos ya indexados en ChromaDB
        if self._collection is not None:
            try:
                self._rebuild_bm25_from_chroma()
            except Exception as exc:
                logger.warning("No se pudo inicializar BM25: %s", exc)

        self.is_ready = True
        logger.info("Retriever listo ✓")

    def _rebuild_bm25_from_chroma(self) -> None:
        """Carga todos los documentos de ChromaDB y reconstruye el índice BM25."""
        try:
            from rank_bm25 import BM25Okapi
            result = self._collection.get(include=["documents"])
            docs   = result.get("documents") or []
            if docs:
                self._bm25_corpus = docs
                self._bm25 = BM25Okapi([d.lower().split() for d in docs])
                logger.info("BM25 construido con %d documentos", len(docs))
        except ImportError:
            logger.warning("rank_bm25 no disponible — búsqueda BM25 deshabilitada")

    # ── Búsqueda (read) ───────────────────────────────────────────────────────

    async def chunk_count(self) -> int:
        """Retorna el número de chunks indexados en ChromaDB."""
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    async def search(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """
        Pipeline completo: embed → ChromaDB → BM25 → RRF → Cross-Encoder → top-K final.

        Args:
            query: Texto de la consulta del usuario.
            top_k: Número de resultados finales (default: settings.TOP_K_FINAL).

        Returns:
            Lista de dicts con: text, content_id, title, content_type,
            chunk_type, score, timestamp_start?, timestamp_end?
        """
        if not self.is_ready:
            raise RuntimeError("Retriever no inicializado — llamar a init() primero")

        k_final = top_k or settings.TOP_K_FINAL
        k_fetch = settings.TOP_K_RETRIEVAL   # cuántos fetching antes del reranking

        # Si no hay colección disponible, retornar vacío con un warning
        if self._collection is None or self._embedder is None:
            logger.warning("search: ChromaDB o embedder no disponible — retornando vacío")
            return []

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, k_fetch, k_final)

    def _search_sync(self, query: str, k_fetch: int, k_final: int) -> list[dict]:
        """Pipeline síncrono de búsqueda ejecutado en un executor."""

        # ── 0. Clasificar la query para pre-filtrado ──────────────────────────
        query_class = classify_query(query)
        where_filter = None

        # Aplicar filtro solo si la confianza es >= 0.6
        if query_class["confidence"] >= 0.6 and query_class["domain"]:
            where_filter = {"auto_domain": query_class["domain"]}
            logger.debug(
                "[SEARCH] Pre-filtrado por clasificación: domain=%s (conf=%.2f)",
                query_class["domain"],
                query_class["confidence"],
            )

        # ── 1. Embedding de la query ──────────────────────────────────────────
        # multilingual-e5 requiere prefijo "query: " para consultas
        query_emb = self._embedder.encode(
            f"query: {query}",
            normalize_embeddings=True,
        ).tolist()

        # ── 2. Búsqueda vectorial en ChromaDB CON FILTRO ──────────────────────
        chroma_results = self._collection.query(
            query_embeddings=[query_emb],
            n_results=min(k_fetch, max(self._collection.count(), 1)),
            where=where_filter,  # ← NUEVO: pre-filtrado por dominio
            include=["documents", "metadatas", "distances"],
        )
        chroma_docs  = (chroma_results.get("documents")  or [[]])[0]
        chroma_meta  = (chroma_results.get("metadatas")  or [[]])[0]
        chroma_dists = (chroma_results.get("distances")  or [[]])[0]

        # Convertir distancia coseno a score: score = 1 - distance (ChromaDB usa distancia)
        chroma_items = []
        for doc, meta, dist in zip(chroma_docs, chroma_meta, chroma_dists):
            score = max(0.0, 1.0 - float(dist))
            chroma_items.append({"text": doc, "meta": meta, "score": score})

        # ── 3. Búsqueda BM25 ──────────────────────────────────────────────────
        bm25_items: list[dict] = []
        if self._bm25 is not None and self._bm25_corpus:
            tokenized_query = query.lower().split()
            bm25_scores = self._bm25.get_scores(tokenized_query)
            # Tomar los top-k índices
            top_bm25_idx = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True,
            )[:k_fetch]

            for rank, idx in enumerate(top_bm25_idx):
                if idx < len(self._bm25_corpus) and bm25_scores[idx] > 0:
                    # BM25 score normalizado al rango [0, 1] respecto al máximo
                    max_score = bm25_scores[top_bm25_idx[0]] if top_bm25_idx else 1.0
                    norm_score = bm25_scores[idx] / max(max_score, 1e-9)
                    bm25_items.append({
                        "text":  self._bm25_corpus[idx],
                        "score": norm_score,
                        "rank":  rank,
                    })

        # ── 4. RRF (Reciprocal Rank Fusion) ───────────────────────────────────
        # Construir ranking unificado: RRF_score = Σ 1/(k + rank_i), k=60
        rrf_k    = 60
        all_texts: dict[str, dict] = {}

        for rank, item in enumerate(chroma_items):
            key = item["text"][:200]
            if key not in all_texts:
                all_texts[key] = {"item": item, "rrf": 0.0}
            all_texts[key]["rrf"] += 1.0 / (rrf_k + rank)

        for rank, item in enumerate(bm25_items):
            key = item["text"][:200]
            if key not in all_texts:
                # El texto viene solo del corpus, necesitamos buscar su metadata en chroma
                chroma_meta_match = self._find_metadata_for_text(item["text"])
                all_texts[key] = {
                    "item": {"text": item["text"], "meta": chroma_meta_match or {}, "score": item["score"]},
                    "rrf": 0.0,
                }
            all_texts[key]["rrf"] += 1.0 / (rrf_k + rank)

        # Ordenar por RRF descendente
        ranked = sorted(all_texts.values(), key=lambda x: x["rrf"], reverse=True)
        top_candidates = ranked[:k_fetch]

        # ── 5. Cross-Encoder reranking ────────────────────────────────────────
        if self._reranker is not None and top_candidates:
            pairs  = [(query, c["item"]["text"]) for c in top_candidates]
            scores = self._reranker.predict(pairs, show_progress_bar=False)
            # Normalizar cross-encoder scores a [0, 1] con sigmoid
            import math
            sigmoid = lambda x: 1.0 / (1.0 + math.exp(-x))
            for c, s in zip(top_candidates, scores):
                c["item"]["score"] = round(sigmoid(float(s)), 4)
            top_candidates.sort(key=lambda x: x["item"]["score"], reverse=True)

        # ── 6. Formatear resultados finales ───────────────────────────────────
        results: list[dict] = []
        for c in top_candidates[:k_final]:
            item = c["item"]
            meta = item.get("meta", {})
            entry: dict = {
                "text":         item["text"],
                "content_id":   meta.get("content_id", ""),
                "title":        meta.get("title", ""),
                "content_type": meta.get("content_type", meta.get("type", "document")),
                "chunk_type":   meta.get("chunk_type", "section"),
                "score":        item.get("score", c.get("rrf", 0.0)),
            }
            if "timestamp_start" in meta:
                entry["timestamp_start"] = meta["timestamp_start"]
                entry["timestamp_end"]   = meta.get("timestamp_end", meta["timestamp_start"])
            results.append(entry)

        return results

    def _find_metadata_for_text(self, text: str) -> Optional[dict]:
        """Busca la metadata de un texto en ChromaDB (para chunks que vienen solo de BM25)."""
        if self._collection is None:
            return None
        try:
            result = self._collection.get(
                where_document={"$contains": text[:100]},
                include=["metadatas"],
                limit=1,
            )
            metas = result.get("metadatas") or []
            return metas[0] if metas else None
        except Exception:
            return None

    # ── Escritura (usados por el pipeline de ingesta) ─────────────────────────

    async def add_chunks(
        self,
        ids:       list[str],
        texts:     list[str],
        metadatas: list[dict],
    ) -> int:
        """
        Genera embeddings e inserta chunks en ChromaDB.
        Usa prefijo "passage: " requerido por multilingual-e5.

        Returns:
            Número de chunks añadidos.
        """
        if not self.is_ready or self._collection is None or self._embedder is None:
            logger.error("add_chunks: retriever no disponible")
            return 0

        if not ids:
            return 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_chunks_sync, ids, texts, metadatas)

    def _add_chunks_sync(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> int:
        """Versión síncrona de add_chunks."""
        try:
            # multilingual-e5 requiere prefijo "passage: " para documentos
            prefixed = [f"passage: {t}" for t in texts]
            embeddings = self._embedder.encode(
                prefixed,
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.debug("add_chunks: %d chunks upserted en ChromaDB", len(ids))
            return len(ids)
        except Exception as exc:
            logger.error("Error en add_chunks: %s", exc)
            return 0

    async def delete_by_content_id(self, content_id: str) -> None:
        """Elimina todos los chunks de un content_id del índice ChromaDB."""
        if self._collection is None:
            return
        try:
            self._collection.delete(where={"content_id": content_id})
            logger.debug("delete_by_content_id: eliminados chunks de %s", content_id)
        except Exception as exc:
            logger.warning("delete_by_content_id error para %s: %s", content_id, exc)

    async def update_bm25(self, new_texts: list[str]) -> None:
        """
        Agrega nuevos textos al corpus BM25 y reconstruye el índice.
        En producción, para grandes volúmenes, reconstruir periódicamente desde ChromaDB.
        """
        if not new_texts:
            return
        try:
            from rank_bm25 import BM25Okapi
            self._bm25_corpus.extend(new_texts)
            self._bm25 = BM25Okapi([t.lower().split() for t in self._bm25_corpus])
            logger.debug("update_bm25: corpus ahora tiene %d textos", len(self._bm25_corpus))
        except ImportError:
            pass   # rank_bm25 no instalado — BM25 deshabilitado silenciosamente
        except Exception as exc:
            logger.warning("update_bm25 error: %s", exc)


retriever = HybridRetriever()

