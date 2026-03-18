#!/usr/bin/env python
"""
Test de clasificación automática de contenido.
Verifica que el clasificador funciona correctamente con diferentes tipos de contenido.
"""
from ai_engine.services.classifier import classify_content, classify_query

def test_computer_vision():
    """Test de clasificación de contenido de visión artificial."""
    print("\n=== Test: Computer Vision ===")

    code = """
import cv2
import torch
from ultralytics import YOLO

def detect_objects(image_path):
    model = YOLO('yolov8n.pt')
    results = model.predict(image_path)
    return results
"""

    text = """
    Este material cubre detección de objetos usando YOLO v8.
    Aprenderás a usar redes neuronales convolucionales (CNN) para
    segmentación de imágenes y reconocimiento de patrones visuales.
    """

    result = classify_content(
        text=text,
        code=code,
        title="Tutorial de YOLO v8 para Detección de Objetos",
        description="Implementación práctica de detección en tiempo real"
    )

    print(f"Dominio:      {result['domain']} ({result['domain_label']})")
    print(f"Área:         {result['area']} ({result['area_label']})")
    print(f"Confianza:    {result['confidence']:.2%}")
    print(f"Tags:         {', '.join(result['tags'][:5])}")
    print(f"Señales:      {len(result['signals_found'])} encontradas")

    assert result['domain'] == 'AI', f"Expected AI, got {result['domain']}"
    assert result['area'] == 'computer_vision', f"Expected computer_vision, got {result['area']}"
    assert result['confidence'] > 0.7, f"Low confidence: {result['confidence']}"
    print("✓ Test pasado")


def test_networking():
    """Test de clasificación de contenido de redes."""
    print("\n=== Test: Networking ===")

    code = """
import socket

def create_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(5)

    while True:
        client, address = server_socket.accept()
        data = client.recv(1024)
        client.send(b"HTTP/1.1 200 OK\\r\\n\\r\\nHello")
        client.close()
"""

    text = """
    Simulador de peticiones TCP/IP. Aprende a crear servidores
    usando sockets y manejar conexiones de clientes.
    """

    result = classify_content(
        text=text,
        code=code,
        title="SIMULADOR DE PETICIONES TCP",
        description="Servidor básico con sockets"
    )

    print(f"Dominio:      {result['domain']} ({result['domain_label']})")
    print(f"Área:         {result['area']} ({result['area_label']})")
    print(f"Confianza:    {result['confidence']:.2%}")
    print(f"Tags:         {', '.join(result['tags'][:5])}")

    assert result['domain'] == 'NET', f"Expected NET, got {result['domain']}"
    assert result['area'] == 'networking', f"Expected networking, got {result['area']}"
    print("✓ Test pasado")


def test_query_classification():
    """Test de clasificación de queries."""
    print("\n=== Test: Query Classification ===")

    test_cases = [
        ("visión artificial yolo", "AI", "computer_vision"),
        ("detección de objetos con CNN", "AI", "computer_vision"),
        ("servidor TCP socket python", "NET", "networking"),
        ("base de datos SQL postgresql", "DB", "sql"),
        ("deep learning pytorch", "AI", "deep_learning"),
        ("algoritmos de ordenamiento", None, None),  # Sin clasificación clara
    ]

    for query, expected_domain, expected_area in test_cases:
        result = classify_query(query)
        print(f"\nQuery: '{query}'")
        print(f"  → Dominio: {result['domain']} (conf={result['confidence']:.2f})")
        print(f"  → Área:    {result['area']}")

        if expected_domain:
            assert result['domain'] == expected_domain, \
                f"Expected {expected_domain}, got {result['domain']}"
            if result['confidence'] >= 0.5:  # Solo verificar área si hay confianza suficiente
                assert result['area'] == expected_area, \
                    f"Expected {expected_area}, got {result['area']}"
        else:
            # Debe tener baja confianza
            assert result['confidence'] < 0.5, \
                f"Expected low confidence, got {result['confidence']}"

    print("\n✓ Todos los tests de queries pasados")


def test_data_science():
    """Test de clasificación de ciencia de datos."""
    print("\n=== Test: Data Science ===")

    code = """
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv('data.csv')
X_train, X_test, y_train, y_test = train_test_split(df.drop('target', axis=1), df['target'])
model = RandomForestClassifier()
model.fit(X_train, y_train)
"""

    text = "Análisis de datos y clasificación con Random Forest"

    result = classify_content(
        text=text,
        code=code,
        title="Machine Learning con Scikit-Learn",
        description="Tutorial de clasificación supervisada"
    )

    print(f"Dominio:      {result['domain']} ({result['domain_label']})")
    print(f"Área:         {result['area']} ({result['area_label']})")
    print(f"Confianza:    {result['confidence']:.2%}")

    assert result['domain'] == 'AI', f"Expected AI, got {result['domain']}"
    assert result['area'] in ['ml_general', 'data_science'], \
        f"Expected ML area, got {result['area']}"
    print("✓ Test pasado")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE CLASIFICACIÓN AUTOMÁTICA")
    print("=" * 60)

    try:
        test_computer_vision()
        test_networking()
        test_data_science()
        test_query_classification()

        print("\n" + "=" * 60)
        print("✓ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test falló: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
