#!/usr/bin/env python
"""
Test de integración: verifica que el pipeline completo funciona.
"""
import asyncio
import sys

async def test_pipeline_integration():
    """Test de integración del pipeline completo."""
    print("=== Test de Integración del Pipeline ===\n")

    # 1. Test de imports
    print("1. Verificando imports...")
    try:
        from ai_engine.services.classifier import classify_content, classify_query
        from ai_engine.services.ingestion.pipeline import ingest_content
        from ai_engine.services.hybrid_retriever import retriever
        print("   ✓ Todos los imports correctos\n")
    except ImportError as e:
        print(f"   ✗ Error de import: {e}")
        return False

    # 2. Test de clasificador
    print("2. Probando clasificador...")
    try:
        result = classify_content(
            text="Tutorial de YOLO v8 para detección de objetos",
            code="import cv2\nimport torch",
            title="Computer Vision con YOLO",
            description="Práctica de detección"
        )
        assert result['domain'] == 'AI'
        assert result['area'] == 'computer_vision'
        assert result['confidence'] > 0.5
        print(f"   ✓ Clasificador funciona: {result['domain']}/{result['area']} (conf={result['confidence']:.2f})\n")
    except Exception as e:
        print(f"   ✗ Error en clasificador: {e}")
        return False

    # 3. Test de clasificación de queries
    print("3. Probando clasificación de queries...")
    try:
        query_result = classify_query("visión artificial yolo")
        assert query_result['domain'] == 'AI'
        assert query_result['area'] == 'computer_vision'
        print(f"   ✓ Query classifier funciona: {query_result['domain']}/{query_result['area']} (conf={query_result['confidence']:.2f})\n")
    except Exception as e:
        print(f"   ✗ Error en query classifier: {e}")
        return False

    # 4. Test de estructura del retriever
    print("4. Verificando estructura del retriever...")
    try:
        # No inicializamos el retriever porque requiere ChromaDB,
        # solo verificamos que la clase se puede instanciar
        from ai_engine.services.hybrid_retriever import HybridRetriever
        test_retriever = HybridRetriever()
        print("   ✓ Retriever se puede instanciar correctamente\n")
    except Exception as e:
        print(f"   ✗ Error en retriever: {e}")
        return False

    print("=" * 50)
    print("✓ TODOS LOS TESTS DE INTEGRACIÓN PASARON")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_pipeline_integration())
    sys.exit(0 if success else 1)
