# 🎯 Service d'Unification - Sports & Tip Types

Service d'unification utilisant **Ollama + ChromaDB** pour normaliser les sports et types de paris provenant de différentes sources.

## 🚀 Quick Start

### Prérequis
- Python 3.11+
- Ollama installé ([ollama.com](https://ollama.com))
- Docker (optionnel, pour déploiement facile)

---

## 📦 Installation

### Option 1 : Local (sans Docker)

```bash
# 1. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Télécharger le modèle d'embeddings
ollama pull nomic-embed-text

# 3. Installer les dépendances Python
cd unification_service
pip install -r requirements.txt

# 4. Lancer le service
python main.py

# 5. Initialiser les mappings (dans un autre terminal)
python init_mappings.py
```

Le service sera disponible sur : **http://localhost:8002**

---

### Option 2 : Docker (recommandé)

```bash
# 1. Construire et lancer
cd unification_service
docker-compose up -d

# 2. Attendre 30s que Ollama télécharge le modèle
docker-compose logs -f

# 3. Initialiser les mappings
python init_mappings.py
```

---

## 🎯 API Endpoints

### 1. Health Check
```bash
GET http://localhost:8002/health
```

**Réponse :**
```json
{
  "status": "healthy",
  "ollama": "ok",
  "chromadb": "ok",
  "stats": {
    "sports_mappings": 15,
    "tip_types_mappings": 45
  }
}
```

---

### 2. Unifier un élément
```bash
POST http://localhost:8002/unify
Content-Type: application/json

{
  "text": "calcio",
  "type": "sport",
  "threshold": 0.7
}
```

**Réponse :**
```json
{
  "original": "calcio",
  "unified": "football",
  "confidence": 0.95,
  "needs_review": false
}
```

---

### 3. Unifier en batch (pour N8N)
```bash
POST http://localhost:8002/unify/bulk
Content-Type: application/json

{
  "items": [
    {"sport": "calcio", "tipText": "1X2: 1"},
    {"sport": "soccer", "tipText": "BTTS"}
  ],
  "threshold": 0.7
}
```

**Réponse :**
```json
{
  "success": true,
  "total": 2,
  "items": [
    {
      "sport": "calcio",
      "tipText": "1X2: 1",
      "sport_unified": "football",
      "sport_confidence": 0.95,
      "sport_needs_review": false,
      "tipText_unified": "home_win",
      "tipText_confidence": 0.92,
      "tipText_needs_review": false
    },
    {
      "sport": "soccer",
      "tipText": "BTTS",
      "sport_unified": "football",
      "sport_confidence": 0.98,
      "sport_needs_review": false,
      "tipText_unified": "both_teams_score",
      "tipText_confidence": 0.91,
      "tipText_needs_review": false
    }
  ]
}
```

---

### 4. Ajouter un mapping
```bash
POST http://localhost:8002/mapping/add
Content-Type: application/json

{
  "original": "fútbol",
  "unified": "football",
  "type": "sport"
}
```

---

### 5. Récupérer tous les mappings
```bash
GET http://localhost:8002/mappings/sport
GET http://localhost:8002/mappings/tip_type
```

---

## 🔧 Intégration N8N

### Workflow N8N complet

```
1. Webhook Trigger (recevoir les pronostics)
    ↓
2. HTTP Request → Unification Service (POST /unify/bulk)
    ↓
3. Code Node (filtrer needs_review = true)
    ↓
4. Switch Node
    ├─ needs_review = false → Continuer le workflow
    └─ needs_review = true → Envoyer vers Airtable pour validation
    ↓
5. Postgres (sauvegarder les pronostics unifiés)
```

### Configuration HTTP Request Node dans N8N

**URL :** `http://localhost:8002/unify/bulk`
**Method :** POST
**Body :**
```json
{
  "items": {{ $json.pronostics }},
  "threshold": 0.7
}
```

**Authentication :** None

---

## 📊 Alimenter la base progressivement

### Méthode 1 : Via l'API

```python
import requests

# Ajouter un nouveau mapping
requests.post("http://localhost:8002/mapping/add", json={
    "original": "basket-ball",
    "unified": "basketball",
    "type": "sport"
})
```

### Méthode 2 : Via fichier JSON

Créer `new_mappings.json` :
```json
[
  {"original": "hockey sur glace", "unified": "hockey", "type": "sport"},
  {"original": "hand", "unified": "handball", "type": "sport"}
]
```

Script Python :
```python
import requests
import json

with open("new_mappings.json") as f:
    mappings = json.load(f)

requests.post("http://localhost:8002/mapping/bulk-add", json=mappings)
```

### Méthode 3 : Workflow de validation N8N

```
Items avec needs_review = true
    ↓
Airtable (table de validation)
    ↓
Humain valide et corrige
    ↓
N8N Webhook (trigger sur update Airtable)
    ↓
HTTP Request → POST /mapping/add
    ↓
Mapping ajouté automatiquement
```

---

## 🧪 Tests

### Test simple
```bash
# Tester l'unification
curl -X POST http://localhost:8002/unify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "calcio",
    "type": "sport"
  }'
```

### Test batch
```bash
curl -X POST http://localhost:8002/unify/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"sport": "calcio", "tipText": "1X2: 1"},
      {"sport": "basket", "tipText": "over 2.5"}
    ]
  }'
```

---

## 📈 Monitoring

### Vérifier les stats
```bash
curl http://localhost:8002/health
```

### Voir tous les mappings sports
```bash
curl http://localhost:8002/mappings/sport
```

### Voir tous les mappings tip types
```bash
curl http://localhost:8002/mappings/tip_type
```

---

## 🔥 Troubleshooting

### Le service ne démarre pas
```bash
# Vérifier Ollama
ollama list

# Télécharger le modèle si absent
ollama pull nomic-embed-text

# Vérifier les logs Docker
docker-compose logs -f
```

### Erreur "model not found"
```bash
# Entrer dans le container
docker exec -it unification-service bash

# Télécharger le modèle
ollama pull nomic-embed-text
```

### ChromaDB vide après restart
- Vérifier que le volume est bien monté : `./chroma_db:/app/chroma_db`
- Re-lancer `init_mappings.py`

---

## 📝 Changelog

### v1.0.0
- ✅ Unification sport et tip_type
- ✅ API REST complète
- ✅ Support batch
- ✅ ChromaDB persistant
- ✅ Docker ready
- ✅ Init script avec mappings de base

---

## 🎯 Prochaines étapes

- [ ] Interface web pour gérer les mappings
- [ ] Authentification API
- [ ] Métriques et analytics
- [ ] Support des compétitions
- [ ] Auto-learning avec feedback
