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
import re
import unicodedata
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


def _normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _title_relevance_boost(query: str, title: str) -> float:
    q = _normalize_text(query)
    t = _normalize_text(title)
    if not q or not t:
        return 0.0

    if q == t:
        return 0.95
    if len(q) <= 5:
        title_tokens = re.findall(r"[a-z0-9]+", t)
        if q in title_tokens:
            return 0.95
    if q in t:
        return 0.60

    q_tokens = [tok for tok in q.split() if len(tok) >= 3]
    if not q_tokens:
        return 0.0

    overlap = sum(1 for tok in q_tokens if tok in t)
    ratio = overlap / len(q_tokens)
    if ratio >= 0.8:
        return 0.18
    if ratio >= 0.5:
        return 0.10
    return 0.0


def _has_query_overlap(query: str, title: str, text: str) -> bool:
    q = _normalize_text(query)
    if not q:
        return False
    stop = {
        "de", "la", "el", "los", "las", "en", "y", "a", "para", "por", "con", "sin", "que",
        "del", "al", "un", "una", "como", "se", "su", "sus", "es", "son", "the", "and", "for",
        "from", "with", "this", "that", "are", "is",
    }
    tokens = [tok for tok in re.findall(r"[a-z0-9]+", q) if len(tok) >= 4 and tok not in stop]
    if not tokens:
        return False
    combined = f"{_normalize_text(title)} {_normalize_text(text)}"
    return any(tok in combined for tok in tokens)


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
        self._bm25_metadata: list[dict] = []  # metadata aligned with _bm25_corpus

    # ── Inicialización ────────────────────────────────────────────────────────

    async def init(self) -> None:
        """
        Carga ChromaDB, el modelo de embeddings multilingual-e5-small y
        (si está habilitado) el cross-encoder de reranking.
        Llamado una sola vez en el lifespan de main.py.
        Idempotente: puede ser llamado múltiples veces sin problemas.
        """
        if self.is_ready:
            logger.debug("Retriever ya inicializado, saltando init()")
            return
            
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
            # Incluir tanto documentos como metadatos para el mapeo
            result = self._collection.get(include=["documents", "metadatas"])
            docs   = result.get("documents") or []
            metas  = result.get("metadatas") or []
            if docs:
                self._bm25_corpus = docs
                # Mantener mapeo índice -> metadata para filtrado posterior
                self._bm25_metadata = metas if len(metas) == len(docs) else [{} for _ in docs]
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

        # ── 0. Corrección de typos y limpieza ──────────────────────────
        query_class = classify_query(query)
        effective_query = query_class.get("query_corrected") or query
        
        # Filtro restrictivo si de verdad es muy claro el dominio y hay buena confianza
        domain_val = query_class.get("domain")
        confidence = float(query_class.get("confidence", 0.0))
        where_filter = None
        if domain_val and confidence > 0.60:
            where_filter = {"auto_domain": domain_val}
            
        primary_results = self._search_with_filter(
            effective_query,
            k_fetch=k_fetch * 2,  
            k_final=k_final,
            where_filter=where_filter,
        )
        
        # Si fallamos en encontrar, intentamos SIN filtro para recuperar recall
        if not primary_results and where_filter is not None:
             primary_results = self._search_with_filter(
                 effective_query,
                 k_fetch=k_fetch * 2,
                 k_final=k_final,
                 where_filter=None,
             )
        
        # ── Omitimos filtrado de Overlap para búsquedas puramente semánticas ──
        return primary_results[:k_final]

    def _search_with_filter(
        self,
        query: str,
        k_fetch: int,
        k_final: int,
        where_filter: Optional[dict],
    ) -> list[dict]:
        """Ejecuta búsqueda completa con un filtro opcional de dominio."""

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
        # IMPORTANTE: Aplicar el mismo filtro por dominio que en ChromaDB
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
                    # Obtener metadata del corpus (ya está alineada por índice)
                    corpus_meta = self._bm25_metadata[idx] if idx < len(self._bm25_metadata) else {}
                    
                    # Filtrar alucinaciones de dominio y BM25 scores débiles
                    if where_filter and corpus_meta:
                        # Si hay un filtro de dominio, verificar que coincida
                        meta_domain = corpus_meta.get("auto_domain")
                        filter_domain = where_filter.get("auto_domain")
                        if meta_domain != filter_domain:
                            continue  # Saltar este resultado, no coincide con el filtro
                    
                    # BM25 score normalizado al rango [0, 1] 
                    # IMPORTANTE: Forzar un denominador mínimo (10.0) para que 
                    # matches débiles (ej. stopwords) no se inflen a 1.0!
                    max_score = bm25_scores[top_bm25_idx[0]] if top_bm25_idx else 1.0
                    effective_max = max(max_score, 10.0)  
                    norm_score = bm25_scores[idx] / effective_max
                    bm25_items.append({
                        "text":  self._bm25_corpus[idx],
                        "score": norm_score,
                        "rank":  rank,
                        "meta":  corpus_meta,  # Usar metadata del corpus
                    })

        # ── 4. RRF (Reciprocal Rank Fusion) ───────────────────────────────────
        # Construir ranking unificado: RRF_score = Σ 1/(k + rank_i), k=60
        rrf_k    = 60
        all_texts: dict[str, dict] = {}

        for rank, item in enumerate(chroma_items):
            key = item["text"][:200]
            if key not in all_texts:
                all_texts[key] = {"item": dict(item), "rrf": 0.0, "max_score": item.get("score", 0.0)}
            else:
                all_texts[key]["max_score"] = max(all_texts[key]["max_score"], item.get("score", 0.0))
            all_texts[key]["rrf"] += 1.0 / (rrf_k + rank)

        for rank, item in enumerate(bm25_items):
            key = item["text"][:200]
            if key not in all_texts:
                # Ya tenemos metadata del filtrado anterior (en item["meta"])
                all_texts[key] = {
                    "item": {"text": item["text"], "meta": item.get("meta", {}), "score": item["score"]},
                    "rrf": 0.0,
                    "max_score": item["score"]
                }
            else:
                all_texts[key]["max_score"] = max(all_texts[key]["max_score"], item["score"])
            all_texts[key]["rrf"] += 1.0 / (rrf_k + rank)

        # Ordenar por RRF descendente
        ranked = sorted(all_texts.values(), key=lambda x: x["rrf"], reverse=True)
        
        # Restaurar score real máximo (en lugar del infimo rrf) para que el threshold posterior funcione
        for c in ranked:
            c["item"]["score"] = c["max_score"]

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
                # Metadatos de clasificación automática
                "auto_domain":      meta.get("auto_domain", ""),
                "auto_area":        meta.get("auto_area", ""),
                "auto_confidence":  meta.get("auto_confidence", 0.0),
            }
            boost = _title_relevance_boost(query, entry["title"])
            if boost > 0:
                entry["score"] = round(min(1.0, float(entry["score"]) + boost), 4)
            if "timestamp_start" in meta:
                entry["timestamp_start"] = meta["timestamp_start"]
                entry["timestamp_end"]   = meta.get("timestamp_end", meta["timestamp_start"])
            results.append(entry)

        results.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
        return self._diversify_by_content(results, k_final)

    def _diversify_by_content(self, results: list[dict], k_final: int) -> list[dict]:
        """Reduce dominancia de un solo content_id en top-k para mejorar cobertura de fuentes."""
        per_content_limit = 2
        picked: list[dict] = []
        counter: dict[str, int] = {}

        for item in results:
            content_id = item.get("content_id", "") or "__unknown__"
            used = counter.get(content_id, 0)
            if used >= per_content_limit:
                continue
            picked.append(item)
            counter[content_id] = used + 1
            if len(picked) >= k_final:
                break

        if len(picked) < k_final:
            seen_keys = {(x.get("content_id", ""), x.get("text", "")[:120]) for x in picked}
            for item in results:
                key = (item.get("content_id", ""), item.get("text", "")[:120])
                if key in seen_keys:
                    continue
                picked.append(item)
                seen_keys.add(key)
                if len(picked) >= k_final:
                    break

        return picked[:k_final]

    def _merge_results(
        self,
        filtered_results: list[dict],
        fallback_results: list[dict],
        k_final: int,
    ) -> list[dict]:
        """Mezcla resultados priorizando filtrados y completando con fallback sin duplicar."""
        merged: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for item in filtered_results:
            key = (item.get("content_id", ""), item.get("text", "")[:120])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

        for item in fallback_results:
            key = (item.get("content_id", ""), item.get("text", "")[:120])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= k_final:
                break

        return merged[:k_final]

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
            # Rebuild completo para mantener alineación corpus <-> metadata
            self._rebuild_bm25_from_chroma()
            logger.debug(
                "update_bm25: reconstruido desde ChromaDB (corpus=%d, metadata=%d)",
                len(self._bm25_corpus),
                len(self._bm25_metadata),
            )
        except ImportError:
            pass   # rank_bm25 no instalado — BM25 deshabilitado silenciosamente
        except Exception as exc:
            logger.warning("update_bm25 error: %s", exc)


retriever = HybridRetriever()

