import re

with open("ai_engine/services/hybrid_retriever.py", "r") as f:
    content = f.read()

# Replace _search_sync entirely until _search_with_filter
old_code = r"""    def _search_sync(self, query: str, k_fetch: int, k_final: int) -> list[dict]:
        "\""Pipeline síncrono de búsqueda ejecutado en un executor."\""

        # ── 0. Clasificar la query para pre-filtrado ──────────────────────────
        query_class = classify_query(query)
        effective_query = query_class.get("query_corrected") or query
        where_filter = None
        min_filtered_results = 3

        # Aplicar filtro solo si la confianza es >= 0.6 (confidence claro)
        # Para confianzas bajas (0.5-0.6), buscar sin filtro (retorna todo)
        if query_class\["confidence"\] >= 0.8 and query_class\["domain"\]:
            where_filter = {"auto_domain": query_class\["domain"\]}
            logger.debug(
                "\[SEARCH\] Pre-filtrado por clasificación: domain=%s (conf=%.2f)",
                query_class\["domain"\],
                query_class\["confidence"\],
            )

        primary_results = self._search_with_filter(
            effective_query,
            k_fetch=k_fetch,
            k_final=k_final,
            where_filter=where_filter,
        )

        unique_primary = len({r.get("content_id", "") for r in primary_results if r.get("content_id")})
        if not where_filter:
            if query_class.get("domain") is None and query_class.get("confidence", 0.0) <= 0.05:
                filtered_ood = \[
                    r for r in primary_results
                    if _has_query_overlap(effective_query, r.get("title", ""), r.get("text", "")\[:300\])
                \]
                return filtered_ood\[:k_final\]
            return primary_results

        # Si tenemos alta confianza y al menos 1 contenido válido, no mezclar con fallback global
        if query_class.get("confidence", 0.0) >= 0.9 and unique_primary >= 1:
            return primary_results

        if len(primary_results) >= min_filtered_results and unique_primary >= 2:
            return primary_results

        logger.info(
            "\[SEARCH\] Fallback sin filtro por baja cobertura: query='%s' filtered=%d",
            effective_query,
            len(primary_results),
        )
        fallback_results = self._search_with_filter(
            effective_query,
            k_fetch=k_fetch,
            k_final=k_final,
            where_filter=None,
        )
        return self._merge_results(primary_results, fallback_results, k_final)"""

new_code = """    def _search_sync(self, query: str, k_fetch: int, k_final: int) -> list[dict]:
        \"\"\"Pipeline síncrono de búsqueda ejecutado en un executor.\"\"\"

        # ── 0. Corrección de typos y limpieza ──────────────────────────
        query_class = classify_query(query)
        effective_query = query_class.get("query_corrected") or query
        
        # ELIMINADO EL PREFILTRADO RESTRICTIVO: Ya no se fuerza un dominio hardcodeado
        # Buscamos abiertamente basándonos enteramente en semántica y contenido.
        
        primary_results = self._search_with_filter(
            effective_query,
            k_fetch=k_fetch * 2,  # Expandimos el universo a revisar
            k_final=k_final,
            where_filter=None,
        )
        
        # Filtro muy ligero: solo prevenir alucinaciones si la query es ruido sin sentido
        if query_class.get("domain") is None and query_class.get("confidence", 0.0) <= 0.05:
            filtered_ood = [
                r for r in primary_results
                if _has_query_overlap(effective_query, r.get("title", ""), r.get("text", "")[:300]) or _has_query_overlap(effective_query, r.get("auto_semantic_terms", ""), "")
            ]
            return filtered_ood[:k_final]
            
        return primary_results[:k_final]"""

content = re.sub(old_code, new_code, content)
with open("ai_engine/services/hybrid_retriever.py", "w") as f:
    f.write(content)

