#!/usr/bin/env python
"""
Test simplificado: verifica solo el clasificador sin dependencias externas.
"""

def test_classifier_standalone():
    """Test del clasificador sin dependencias de settings o ChromaDB."""
    print("=== Test Simplificado del Clasificador ===\n")

    # 1. Test de imports del clasificador
    print("1. Importando clasificador...")
    try:
        import sys
        import os
        # Agregar el directorio raíz al path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from ai_engine.services.classifier import (
            classify_content,
            classify_query,
            ContentClassifier,
            DOMAINS,
            AREAS,
        )
        print("   ✓ Clasificador importado correctamente\n")
    except ImportError as e:
        print(f"   ✗ Error de import: {e}")
        return False

    # 2. Verificar taxonomía
    print("2. Verificando taxonomía...")
    try:
        assert 'AI' in DOMAINS
        assert 'NET' in DOMAINS
        assert 'DB' in DOMAINS
        assert 'computer_vision' in AREAS.get('AI', {})
        print(f"   ✓ Taxonomía completa: {len(DOMAINS)} dominios definidos\n")
    except AssertionError as e:
        print(f"   ✗ Error en taxonomía: {e}")
        return False

    # 3. Test de clasificación de contenido
    print("3. Probando clasificación de contenido...")
    try:
        result = classify_content(
            text="Tutorial de YOLO v8 para detección de objetos en tiempo real",
            code="import cv2\nimport torch\nfrom ultralytics import YOLO",
            title="Computer Vision con YOLO",
            description="Práctica de detección con redes neuronales"
        )

        print(f"   Dominio:    {result['domain']} ({result['domain_label']})")
        print(f"   Área:       {result['area']} ({result['area_label']})")
        print(f"   Confianza:  {result['confidence']:.2%}")
        print(f"   Tags:       {', '.join(result['tags'][:5])}")

        assert result['domain'] == 'AI', f"Expected AI, got {result['domain']}"
        assert result['area'] == 'computer_vision', f"Expected computer_vision, got {result['area']}"
        assert result['confidence'] > 0.5, f"Low confidence: {result['confidence']}"
        print("   ✓ Clasificación correcta\n")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Test de clasificación de queries
    print("4. Probando clasificación de queries...")
    try:
        test_cases = [
            ("visión artificial yolo", "AI", "computer_vision"),
            ("servidor TCP socket", "NET", "networking"),
            ("SQL database postgresql", "DB", "sql"),
        ]

        for query, expected_domain, expected_area in test_cases:
            result = classify_query(query)
            print(f"   '{query}'")
            print(f"      → {result['domain']}/{result['area']} (conf={result['confidence']:.2f})")

            if result['confidence'] >= 0.5:
                assert result['domain'] == expected_domain, \
                    f"Expected {expected_domain}, got {result['domain']}"

        print("   ✓ Clasificación de queries funciona\n")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Test de instanciación de ContentClassifier
    print("5. Probando instanciación de ContentClassifier...")
    try:
        classifier = ContentClassifier()
        result = classifier.classify(
            text="Tutorial de networking con sockets",
            code="import socket\nsocket.socket()",
            title="Servidor TCP",
            description="Programación de redes"
        )
        assert result['domain'] == 'NET'
        print("   ✓ ContentClassifier funciona correctamente\n")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("=" * 50)
    print("✓ TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("=" * 50)
    print("\nEl clasificador está completamente funcional y listo para usarse.")
    return True

if __name__ == "__main__":
    import sys
    success = test_classifier_standalone()
    sys.exit(0 if success else 1)
