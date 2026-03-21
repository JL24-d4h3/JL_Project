import re

with open("ai_engine/services/hybrid_retriever.py", "r") as f:
    text = f.read()

prefix = text[:text.find("    def _search_sync(")]
suffix = text[text.find("    def _search_with_filter("):]

new_func = """    def _search_sync(self, query: str, k_fetch: int, k_final: int) -> list[dict]:
        \"\"\"Pipeline síncrono de búsqueda ejecutado en un executor.\"\"\"

        # ── 0. Corrección de typos y limpieza ──────────────────────────
        query_class = classify_query(query)
        effective_query = query_class.get("query_corrected") or query
        
        # ELIMINADO EL PREFILTRADO RESTRICTIVO: Ya no se fuerza un dominio hardcodeado.
        
        primary_results = self._search_with_filter(
            effective_query,
            k_fetch=k_fetch * 2,  
            k_final=k_final,
            where_filter=None,
        )
        
        # Filtro estricto para ruido
        if query_class.get("domain") is None and query_class.get("confidence", 0.0) <= 0.05:
            filtered_ood = [
                r for r in primary_results
                if _has_query_overlap(effective_query, r.get("title", ""), r.get("text", "")[:300]) or _has_query_overlap(effective_query, r.get("auto_semantic_terms", ""), "")
            ]
            return filtered_ood[:k_final]
            
        return primary_results[:k_final]

"""

with open("ai_engine/services/hybrid_retriever.py", "w") as f:
    f.write(prefix + new_func + suffix)
    
print("Patched hybrid_retriever!")
