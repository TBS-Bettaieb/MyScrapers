# 🚀 Quick Start - Service d'Unification

## 🎯 Qu'est-ce que c'est ?

Un service qui **normalise automatiquement** les sports et types de paris provenant de différentes sources :

- **"calcio"**, **"soccer"**, **"fútbol"** → **"football"**
- **"1X2: 1"**, **"résultat: domicile"** → **"home_win"**
- **"BTTS"**, **"Both teams to score"** → **"both_teams_score"**

**100% local, gratuit, et sans cloud** grâce à Ollama + ChromaDB.

---

## ⚡ Démarrage en 3 minutes

### Windows

```cmd
# 1. Installer Ollama
winget install Ollama.Ollama

# 2. Démarrer le service
cd unification_service
start.bat
```

### Linux/Mac

```bash
# 1. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Démarrer le service
cd unification_service
chmod +x start.sh
./start.sh
```

### Docker (recommandé pour production)

```bash
cd unification_service
docker-compose up -d

# Attendre 30s puis initialiser
python init_mappings.py
```

---

## 🧪 Tester que ça marche

```bash
# Test simple
curl http://localhost:8002/health

# Test d'unification
curl -X POST http://localhost:8002/unify \
  -H "Content-Type: application/json" \
  -d '{"text": "calcio", "type": "sport"}'

# Résultat attendu :
# {
#   "original": "calcio",
#   "unified": "football",
#   "confidence": 0.95,
#   "needs_review": false
# }
```

Ou utilisez le script de test complet :

```bash
python test_service.py
```

---

## 🔧 Intégrer avec N8N

### Configuration rapide

1. **Créer un HTTP Request Node**
   - URL : `http://localhost:8002/unify/bulk`
   - Method : POST
   - Body :
     ```json
     {
       "items": {{ $json.pronostics }},
       "threshold": 0.7
     }
     ```

2. **Utiliser les données unifiées**
   ```javascript
   // Dans un Code Node
   const items = $json.items;

   items.forEach(item => {
     console.log(`Sport: ${item.sport_unified}`);
     console.log(`Tip: ${item.tipText_unified}`);
     console.log(`Confidence: ${item.sport_confidence}`);
   });
   ```

3. **Router selon confidence**
   ```javascript
   // Switch Node
   if (item.needs_review) {
     // Envoyer vers Airtable pour validation
   } else {
     // Sauvegarder directement en base
   }
   ```

Voir **[N8N_WORKFLOW.md](./N8N_WORKFLOW.md)** pour la configuration complète.

---

## 📚 Documentation API

Une fois le service démarré, accédez à :

**http://localhost:8002/docs**

Vous aurez une interface Swagger interactive pour tester tous les endpoints.

### Endpoints principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Vérifier le statut |
| `/unify` | POST | Unifier un élément |
| `/unify/bulk` | POST | Unifier en batch (pour N8N) |
| `/mapping/add` | POST | Ajouter un mapping |
| `/mappings/{type}` | GET | Voir tous les mappings |

---

## 📊 Alimenter la base

### Méthode 1 : Via l'API

```python
import requests

requests.post("http://localhost:8002/mapping/add", json={
    "original": "fútbol",
    "unified": "football",
    "type": "sport"
})
```

### Méthode 2 : Via fichier JSON

Créez `my_mappings.json` :
```json
[
  {"original": "foot", "unified": "football", "type": "sport"},
  {"original": "basket-ball", "unified": "basketball", "type": "sport"}
]
```

Puis :
```python
import requests
import json

with open("my_mappings.json") as f:
    mappings = json.load(f)

requests.post("http://localhost:8002/mapping/bulk-add", json=mappings)
```

### Méthode 3 : Auto-apprentissage via N8N

Configurez un workflow de validation :
```
Airtable (validation manuelle)
    → N8N Webhook
    → POST /mapping/add
    → Mapping ajouté automatiquement
```

---

## 🎯 Exemple complet

### Cas d'usage réel

Vous scrappez 3 sources différentes :

**AssoPoker (Italien)** :
```json
{"sport": "Calcio", "tipText": "Risultato: 1"}
```

**FootyStats (Anglais)** :
```json
{"sport": "Soccer", "tipText": "Match Result: Home"}
```

**Pronosoft (Français)** :
```json
{"sport": "Football", "tipText": "Résultat: Domicile"}
```

### Après unification

```bash
curl -X POST http://localhost:8002/unify/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"sport": "Calcio", "tipText": "Risultato: 1"},
      {"sport": "Soccer", "tipText": "Match Result: Home"},
      {"sport": "Football", "tipText": "Résultat: Domicile"}
    ]
  }'
```

### Résultat

```json
{
  "items": [
    {
      "sport": "Calcio",
      "sport_unified": "football",
      "tipText": "Risultato: 1",
      "tipText_unified": "home_win"
    },
    {
      "sport": "Soccer",
      "sport_unified": "football",
      "tipText": "Match Result: Home",
      "tipText_unified": "home_win"
    },
    {
      "sport": "Football",
      "sport_unified": "football",
      "tipText": "Résultat: Domicile",
      "tipText_unified": "home_win"
    }
  ]
}
```

**🎉 Toutes les 3 sources retournent maintenant les mêmes valeurs normalisées !**

---

## 🔥 Troubleshooting

### Le service ne démarre pas

```bash
# Vérifier Ollama
ollama list

# Télécharger le modèle
ollama pull nomic-embed-text

# Vérifier Python
python --version  # Doit être 3.11+
```

### Erreur "Connection refused"

```bash
# Vérifier que le service tourne
curl http://localhost:8002/health

# Vérifier les logs
docker-compose logs -f  # Si Docker
```

### Base ChromaDB vide

```bash
# Re-initialiser
python init_mappings.py

# Vérifier
curl http://localhost:8002/mappings/sport
```

---

## 📖 Ressources

- **[README.md](./README.md)** - Documentation complète
- **[N8N_WORKFLOW.md](./N8N_WORKFLOW.md)** - Configuration N8N détaillée
- **[API Docs](http://localhost:8002/docs)** - Documentation interactive Swagger

---

## 🆘 Support

Si vous avez des questions ou problèmes :

1. Consultez le README complet
2. Vérifiez les logs : `docker-compose logs -f`
3. Testez avec : `python test_service.py`
4. Vérifiez Ollama : `ollama list`

---

**Prêt à unifier vos données ! 🚀**
