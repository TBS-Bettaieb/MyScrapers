FROM python:3.11-slim

WORKDIR /app

# Installer Ollama (version Linux)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Créer le dossier pour ChromaDB
RUN mkdir -p /app/chroma_db

# Exposer le port
EXPOSE 8002

# Script de démarrage
CMD ["sh", "-c", "ollama serve & sleep 5 && ollama pull nomic-embed-text && python main.py"]
