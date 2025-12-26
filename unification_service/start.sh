#!/bin/bash

echo "========================================"
echo "Service d'Unification - Démarrage"
echo "========================================"
echo ""

# Vérifier si Ollama est installé
if ! command -v ollama &> /dev/null; then
    echo "[ERREUR] Ollama n'est pas installé"
    echo "Installez Ollama depuis: https://ollama.com"
    exit 1
fi

echo "[1/4] Vérification d'Ollama..."
if ! ollama list | grep -q "nomic-embed-text"; then
    echo "[INFO] Téléchargement du modèle nomic-embed-text..."
    ollama pull nomic-embed-text
fi

echo "[2/4] Installation des dépendances Python..."
pip install -r requirements.txt --quiet

echo "[3/4] Démarrage du service..."
python main.py &
SERVICE_PID=$!

echo "[4/4] Attente du service (10s)..."
sleep 10

echo ""
echo "Initialisation des mappings..."
python init_mappings.py

echo ""
echo "========================================"
echo "Service démarré sur http://localhost:8002"
echo "PID: $SERVICE_PID"
echo "========================================"
echo ""
echo "Testez avec: curl http://localhost:8002/health"
echo "Documentation: http://localhost:8002/docs"
echo ""
echo "Pour arrêter: kill $SERVICE_PID"
