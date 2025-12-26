# 🎯 Service d'Unification - Documentation

Le service d'unification est maintenant **intégré dans l'API principale** (`app.py`) sur le port **8001**.

Il permet de normaliser les sports et types de paris provenant de différentes sources en utilisant **Ollama + ChromaDB** pour la recherche sémantique.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         MyScrapers API (Port 8001)      │
│                                         │
│  ┌──────────────┐   ┌───────────────┐  │
│  │   Scrapers   │   │ Unification   │  │
│  │   Endpoints  │   │   Endpoints   │  │
│  │              │   │   /unify/*    │  │
│  └──────────────┘   └───────┬───────┘  │
│                              │          │
└──────────────────────────────┼──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   ChromaDB          │
                    │   (Embeddings DB)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Ollama Server     │
                    │   (Embeddings AI)   │
                    └─────────────────────┘
```

---

## 🚀 Configuration

### Prérequis

1. **Serveur Ollama** avec le modèle `nomic-embed-text` :
   ```bash
   # Sur votre serveur Ollama
   ollama pull nomic-embed-text
   ollama serve
   ```

2. **Variables d'environnement** :

   Créer un fichier `.env` à la racine du projet :
   ```bash
   # URL de votre serveur Ollama privé
   OLLAMA_URL=http://votre-serveur-ollama:11434
   OLLAMA_MODEL=nomic-embed-text
   CHROMA_PATH=/app/chroma_db
   ```

   Ou bien dans `docker-compose.yml` :
   ```yaml
   environment:
     - OLLAMA_URL=http://votre-serveur-ollama:11434
   ```

---

## 📦 Installation

### Option 1 : Local (sans Docker)

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer l'URL Ollama
export OLLAMA_URL=http://votre-serveur-ollama:11434

# 3. Lancer le service
python -m uvicorn app:app --host 0.0.0.0 --port 8001
```

Le service sera disponible sur : **http://localhost:8001**

---

### Option 2 : Docker (recommandé)

```bash
# 1. Configurer l'URL Ollama dans docker-compose.yml
# Ou via variable d'environnement :
export OLLAMA_URL=http://votre-serveur-ollama:11434

# 2. Construire et lancer
docker-compose up -d

# 3. Vérifier les logs
docker-compose logs -f

# 4. Vérifier la santé du service
curl http://localhost:8001/unify/health
```

---

## 🎯 Endpoints disponibles

### 1. Health Check

```bash
GET http://localhost:8001/unify/health
```

**Réponse :**
```json
{
  "status": "healthy",
  "ollama": "ok",
  "ollama_url": "http://votre-serveur-ollama:11434",
  "ollama_model": "nomic-embed-text",
  "chromadb": "ok",
  "chromadb_path": "/app/chroma_db",
  "stats": {
    "sports_mappings": 17,
    "tip_types_mappings": 68
  }
}
```

---

### 2. Unifier un élément

```bash
POST http://localhost:8001/unify
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

**Paramètres :**
- `text` : Texte à unifier
- `type` : `"sport"` ou `"tip_type"`
- `threshold` : Seuil de confiance (0.0-1.0, défaut: 0.7)

---

### 3. Unifier en batch (pour N8N)

```bash
POST http://localhost:8001/unify/bulk
Content-Type: application/json

{
  "items": [
    {"sport": "calcio", "tipText": "1X2: 1"},
    {"sport": "basket", "tipText": "BTTS"},
    {"sport": "fútbol", "tipText": "over 2.5"}
  ],
  "threshold": 0.7
}
```

**Réponse :**
```json
{
  "success": true,
  "total": 3,
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
      "sport": "basket",
      "tipText": "BTTS",
      "sport_unified": "basketball",
      "sport_confidence": 0.88,
      "sport_needs_review": false,
      "tipText_unified": "both_teams_score",
      "tipText_confidence": 0.98,
      "tipText_needs_review": false
    },
    {
      "sport": "fútbol",
      "tipText": "over 2.5",
      "sport_unified": "football",
      "sport_confidence": 0.93,
      "sport_needs_review": false,
      "tipText_unified": "over_2_5_goals",
      "tipText_confidence": 0.96,
      "tipText_needs_review": false
    }
  ]
}
```

---

### 4. Ajouter un mapping

```bash
POST http://localhost:8001/unify/mapping/add
Content-Type: application/json

{
  "original": "fútbol",
  "unified": "football",
  "type": "sport"
}
```

**Réponse :**
```json
{
  "success": true,
  "message": "Mapping added: fútbol -> football"
}
```

---

### 5. Ajouter plusieurs mappings

```bash
POST http://localhost:8001/unify/mapping/bulk-add
Content-Type: application/json

[
  {"original": "hockey sur glace", "unified": "hockey", "type": "sport"},
  {"original": "hand", "unified": "handball", "type": "sport"}
]
```

**Réponse :**
```json
{
  "success": true,
  "added": 2,
  "errors": []
}
```

---

### 6. Récupérer tous les mappings

```bash
GET http://localhost:8001/unify/mappings/sport
GET http://localhost:8001/unify/mappings/tip_type
```

**Réponse :**
```json
{
  "type": "sport",
  "total": 17,
  "mappings": [
    {"original": "calcio", "unified": "football"},
    {"original": "soccer", "unified": "football"},
    {"original": "basket", "unified": "basketball"},
    ...
  ]
}
```

---

## 🔧 Intégration N8N

### Workflow N8N recommandé

```
1. Webhook Trigger (recevoir les pronostics bruts)
    ↓
2. HTTP Request → POST /unify/bulk
    URL: http://localhost:8001/unify/bulk
    Body: {"items": {{ $json.pronostics }}, "threshold": 0.7}
    ↓
3. Code Node (filtrer needs_review = true)
    ↓
4. Switch Node
    ├─ needs_review = false → Postgres (sauvegarder)
    └─ needs_review = true → Airtable (validation manuelle)
```

### Configuration HTTP Request Node

**URL :** `http://localhost:8001/unify/bulk`
**Method :** `POST`
**Headers :** `Content-Type: application/json`
**Body :**
```json
{
  "items": {{ $json.pronostics }},
  "threshold": 0.7
}
```

**Post-Processing (Code Node) :**
```javascript
// Extraire les items unifiés
const items = $input.first().json.items;

// Séparer les items validés et ceux à revoir
const validated = items.filter(item =>
  !item.sport_needs_review && !item.tipText_needs_review
);

const needsReview = items.filter(item =>
  item.sport_needs_review || item.tipText_needs_review
);

return [
  { json: { validated, needsReview } }
];
```

---

## 📊 Mappings de base

### Sports (17 mappings)

| Original | Unified |
|----------|---------|
| calcio, soccer, fútbol, futebol | football |
| basket, basket-ball, pallacanestro | basketball |
| tennis | tennis |
| hockey, hockey sur glace | hockey |
| rugby | rugby |
| handball, hand | handball |
| volley, volleyball | volleyball |

### Tip Types (68 mappings)

**Match Result :**
- `1X2`, `risultato`, `résultat`, `match result` → `match_result`

**Home Win :**
- `1X2: 1`, `risultato: 1`, `résultat: 1`, `match result: home` → `home_win`

**Draw :**
- `1X2: X`, `risultato: x`, `résultat: nul`, `nul` → `draw`

**Away Win :**
- `1X2: 2`, `risultato: 2`, `résultat: 2`, `match result: away` → `away_win`

**Both Teams to Score :**
- `BTTS`, `both teams to score`, `goal/goal`, `gol/gol` → `both_teams_score`
- `BTTS: yes` → `both_teams_score_yes`
- `BTTS: no` → `both_teams_score_no`

**Over/Under Goals :**
- `over 2.5`, `plus de 2.5 buts`, `più di 2.5 gol` → `over_2_5_goals`
- `under 2.5`, `moins de 2.5 buts`, `meno di 2.5 gol` → `under_2_5_goals`
- `over 1.5` → `over_1_5_goals`
- `under 1.5` → `under_1_5_goals`
- `over 3.5` → `over_3_5_goals`
- `under 3.5` → `under_3_5_goals`

**Double Chance :**
- `double chance`, `doppia chance` → `double_chance`
- `double chance: 1x` → `double_chance_1x`
- `double chance: 12` → `double_chance_12`
- `double chance: x2` → `double_chance_x2`

---

## 🧪 Tests

### Test rapide

```bash
# 1. Vérifier que le service est up
curl http://localhost:8001/unify/health

# 2. Tester l'unification d'un sport
curl -X POST http://localhost:8001/unify \
  -H "Content-Type: application/json" \
  -d '{"text": "calcio", "type": "sport"}'

# 3. Tester l'unification d'un tip type
curl -X POST http://localhost:8001/unify \
  -H "Content-Type: application/json" \
  -d '{"text": "1X2: 1", "type": "tip_type"}'

# 4. Tester le batch
curl -X POST http://localhost:8001/unify/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"sport": "calcio", "tipText": "BTTS"},
      {"sport": "basket", "tipText": "over 2.5"}
    ]
  }'
```

---

## 🔥 Troubleshooting

### Erreur "Ollama server not reachable"

**Symptôme :**
```json
{
  "detail": "Ollama server not reachable at http://localhost:11434"
}
```

**Solution :**
1. Vérifier que le serveur Ollama est démarré :
   ```bash
   curl http://votre-serveur-ollama:11434/api/version
   ```

2. Vérifier la variable `OLLAMA_URL` :
   ```bash
   echo $OLLAMA_URL
   ```

3. Mettre à jour `docker-compose.yml` ou `.env` avec la bonne URL

---

### ChromaDB vide après restart

**Symptôme :**
```json
{
  "stats": {
    "sports_mappings": 0,
    "tip_types_mappings": 0
  }
}
```

**Solution :**
1. Vérifier que le volume est bien monté :
   ```bash
   docker inspect investing-calendar-api | grep chroma_db
   ```

2. Re-démarrer le service (les mappings se chargeront automatiquement) :
   ```bash
   docker-compose restart
   ```

---

### Performance lente

**Symptôme :** Les requêtes prennent plus de 2 secondes

**Solution :**
1. Vérifier la latence réseau vers le serveur Ollama
2. Utiliser un serveur Ollama local si possible
3. Mettre en cache les embeddings fréquents

---

## 📈 Monitoring

### Vérifier les stats

```bash
curl http://localhost:8001/unify/health | jq '.stats'
```

### Voir tous les mappings sports

```bash
curl http://localhost:8001/unify/mappings/sport | jq '.mappings | length'
```

### Logs Docker

```bash
docker-compose logs -f investing-api
```

---

## 🎯 Workflow complet d'utilisation

### 1. Scraper les pronostics

```bash
curl http://localhost:8001/scrape/assopoker
```

### 2. Unifier les résultats

```bash
curl -X POST http://localhost:8001/unify/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"sport": "Calcio", "tipText": "Risultato: 1"},
      {"sport": "Basket", "tipText": "Over 2.5"}
    ]
  }'
```

### 3. Filtrer et sauvegarder

```javascript
// Dans N8N
const unified = $input.first().json.items;

// Filtrer les items validés
const validated = unified.filter(item =>
  !item.sport_needs_review && !item.tipText_needs_review
);

// Sauvegarder dans Postgres avec les valeurs unifiées
return validated.map(item => ({
  sport: item.sport_unified,
  tip_type: item.tipText_unified,
  original_sport: item.sport,
  original_tip: item.tipText,
  confidence: Math.min(item.sport_confidence, item.tipText_confidence)
}));
```

---

## 📝 Alimenter la base progressivement

### Méthode 1 : Via l'API (automatique avec N8N)

```javascript
// Dans N8N - après validation manuelle dans Airtable
const newMapping = {
  original: $json.original_text,
  unified: $json.validated_value,
  type: $json.mapping_type  // "sport" ou "tip_type"
};

// Appeler l'API
$http.post('http://localhost:8001/unify/mapping/add', newMapping);
```

### Méthode 2 : Bulk import

```bash
# Créer un fichier JSON avec les nouveaux mappings
cat > new_mappings.json << 'EOF'
[
  {"original": "voetbal", "unified": "football", "type": "sport"},
  {"original": "dobbel kans", "unified": "double_chance", "type": "tip_type"}
]
EOF

# Importer via curl
curl -X POST http://localhost:8001/unify/mapping/bulk-add \
  -H "Content-Type: application/json" \
  -d @new_mappings.json
```

---

## ✅ Checklist de déploiement

- [ ] Serveur Ollama démarré avec modèle `nomic-embed-text`
- [ ] Variable `OLLAMA_URL` configurée
- [ ] Docker Compose lancé : `docker-compose up -d`
- [ ] Health check OK : `curl http://localhost:8001/unify/health`
- [ ] Mappings chargés (stats > 0)
- [ ] Test d'unification fonctionnel
- [ ] Volume `chroma_db` persistant configuré
- [ ] N8N configuré pour appeler `/unify/bulk`
- [ ] Workflow de validation Airtable en place (optionnel)

---

## 🎉 Avantages de cette architecture

✅ **Point d'entrée unique** : Tout sur le port 8001
✅ **Auto-initialisation** : Mappings chargés automatiquement au démarrage
✅ **Serveur Ollama externe** : Réutilisable par d'autres services
✅ **Persistance ChromaDB** : Les mappings ajoutés sont conservés
✅ **Compatible N8N** : Endpoint `/unify/bulk` optimisé pour batch
✅ **Extensible** : Ajout facile de nouveaux mappings via API
✅ **Recherche sémantique** : Gère les typos et variantes linguistiques
✅ **Validation progressive** : Flag `needs_review` pour les cas incertains

---

## 📚 Ressources

- [Documentation Ollama](https://ollama.com/library/nomic-embed-text)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [N8N Workflow Automation](https://n8n.io/)

---

**Version :** 1.2.0
**Date :** 2025-12-26
**Auteur :** Generated with Claude Code
