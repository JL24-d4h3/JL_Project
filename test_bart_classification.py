#!/usr/bin/env python3
"""
Test: Clasificación con BART-MNLI
Prueba la clasificación de los archivos en storage/code/
"""
import sys
from pathlib import Path

# Agregar ai_engine al path
sys.path.insert(0, str(Path(__file__).parent / "ai_engine"))

from services.classifier import classify_content

# Mapeo de archivos con títulos descriptivos
TEST_FILES = {
    "storage/code/1195bab7c80f139944612f43b1486b4660a2154590a511365836465a9c8961da.py": {
        "title": "Data Augmentation con Albumentations",
        "description": "Testing de funciones de augmentación de datos para visión artificial",
        "expected_domain": "AI",
        "expected_area": "computer_vision",
    },
    "storage/code/8a2814a052653e79bc09ec33c8f750ec26d32ab85263bd8b2793b09fc5da8c9b.py": {
        "title": "MQTT WiFi Controller",
        "description": "Simulador de peticiones para control remoto de red mediante MQTT",
        "expected_domain": "NET",
        "expected_area": "networking",
    },
    "storage/code/ca1dc016a16779af9bc88da70976db9d2114111c606165f9380a757b999199b8.py": {
        "title": "U-Net Mask Extraction",
        "description": "Extracción de máscaras para entrenamiento de redes U-Net",
        "expected_domain": "AI",
        "expected_area": "computer_vision",
    },
    "storage/code/f9291a7c49d59c3a497c025d2d2b5860192cc62c6c38409a01b07e9f6a44289d.py": {
        "title": "YOLO Dataset Explorer",
        "description": "Explorador de bounding boxes para datasets YOLO v8",
        "expected_domain": "AI",
        "expected_area": "computer_vision",
    },
}


def test_classification():
    """Clasifica todos los archivos de prueba."""
    print("=" * 70)
    print("TEST: Clasificación Automática con BART-MNLI")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for file_path, metadata in TEST_FILES.items():
        print(f"\n{'-' * 70}")
        print(f"Archivo: {Path(file_path).name}")
        print(f"Título: {metadata['title']}")
        print(f"Descripción: {metadata['description']}")
        print(f"Esperado: {metadata['expected_domain']}/{metadata['expected_area']}")
        print("-" * 70)

        try:
            # Leer el archivo
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()

            # Clasificar
            result = classify_content(
                text=code,
                code=code,
                title=metadata["title"],
                description=metadata["description"],
                use_bart=True,  # Usar BART para mejor precisión
            )

            # Mostrar resultado
            print(f"Dominio:      {result['domain']} ({result['domain_label']})")
            print(f"Área:         {result['area']} ({result['area_label']})")
            print(f"Confianza:    {result['confidence']:.1%}")
            print(f"Método:       {result.get('method', 'unknown')}")
            print(f"Señales:      {len(result.get('signals_found', []))} encontradas")

            # Verificar resultado
            domain_ok = result["domain"] == metadata["expected_domain"]
            area_ok = result["area"] == metadata["expected_area"]

            if domain_ok and area_ok:
                print("✓ TEST PASSOU")
                passed += 1
            else:
                print("✗ TEST FALHOU")
                if not domain_ok:
                    print(
                        f"  - Dominio incorrecto: {result['domain']} != {metadata['expected_domain']}"
                    )
                if not area_ok:
                    print(
                        f"  - Área incorrecta: {result['area']} != {metadata['expected_area']}"
                    )
                failed += 1

        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1

    # Resumen
    print()
    print("=" * 70)
    print(f"RESUMEN: {passed} pasaron, {failed} fallaron de {passed + failed} tests")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = test_classification()
    sys.exit(0 if success else 1)
