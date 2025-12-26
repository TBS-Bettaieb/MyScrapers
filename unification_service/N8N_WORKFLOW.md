# 🔄 Workflow N8N - Configuration complète

## 📊 Architecture du workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW PRINCIPAL                          │
└─────────────────────────────────────────────────────────────────┘

1. [Webhook] Recevoir pronostics
      ↓
2. [HTTP Request] FastAPI Scrapers → Récupérer données brutes
      ↓
3. [HTTP Request] Unification Service → Unifier sport + tipText
      ↓
4. [Code] Enrichir les données
      ↓
5. [Switch] Router selon confidence
      ├─ Confidence OK → [6. Postgres] Sauvegarder
      └─ Needs review → [7. Airtable] Queue validation
```

---

## 🎯 Configuration de chaque Node

### Node 1 : Webhook Trigger

**Type :** Webhook
**Méthode :** POST
**Path :** `/webhook/scrape-pronostics`

**Exemple de payload :**
```json
{
  "sources": ["assopoker", "footystats"],
  "max_tips": 10
}
```

---

### Node 2 : HTTP Request - Appel API Scrapers

**Type :** HTTP Request
**Method :** POST
**URL :** `http://localhost:8000/scrape/all`

**Body (JSON) :**
```json
{
  "sources": {{ $json.body.sources }},
  "max_tips": {{ $json.body.max_tips }}
}
```

**Headers :**
```json
{
  "Content-Type": "application/json"
}
```

**Response Format :** JSON

---

### Node 3 : HTTP Request - Unification Service

**Type :** HTTP Request
**Method :** POST
**URL :** `http://localhost:8002/unify/bulk`

**Body (JSON) :**
```json
{
  "items": {{ $json.pronostics }},
  "threshold": 0.7
}
```

**Headers :**
```json
{
  "Content-Type": "application/json"
}
```

**Output :**
```json
{
  "success": true,
  "total": 5,
  "items": [
    {
      "id": "assopoker_monaco_real-madrid_2025-12-26_...",
      "source": "assopoker",
      "sport": "Calcio",
      "sport_unified": "football",
      "sport_confidence": 0.95,
      "sport_needs_review": false,
      "tipText": "1X2: 1",
      "tipText_unified": "home_win",
      "tipText_confidence": 0.92,
      "tipText_needs_review": false,
      "match": "Monaco - Real Madrid",
      "homeTeam": "Monaco",
      "awayTeam": "Real Madrid",
      "odds": 2.5
    }
  ]
}
```

---

### Node 4 : Code - Enrichir et nettoyer

**Type :** Code (JavaScript)

**Code :**
```javascript
// Récupérer les items unifiés
const items = $input.first().json.items;

// Enrichir chaque pronostic
const enriched = items.map(item => {
  return {
    // Données originales
    id: item.id,
    source: item.source,
    match: item.match,
    homeTeam: item.homeTeam,
    awayTeam: item.awayTeam,
    dateTime: item.dateTime,
    competition: item.competition,
    odds: item.odds,

    // Données UNIFIÉES (utilisées pour la base)
    sport_unified: item.sport_unified,
    tipText_unified: item.tipText_unified,

    // Données originales (pour référence)
    sport_original: item.sport,
    tipText_original: item.tipText,

    // Métadonnées d'unification
    sport_confidence: item.sport_confidence,
    tipText_confidence: item.tipText_confidence,
    needs_review: item.sport_needs_review || item.tipText_needs_review,

    // Timestamp
    processed_at: new Date().toISOString()
  };
});

return enriched.map(item => ({ json: item }));
```

---

### Node 5 : Switch - Router selon confidence

**Type :** Switch

**Mode :** Rules

**Règles :**

**Règle 1 - Valide (aller vers Postgres)**
- Field: `{{ $json.needs_review }}`
- Operation: `Equal to`
- Value: `false`

**Règle 2 - Besoin validation (aller vers Airtable)**
- Field: `{{ $json.needs_review }}`
- Operation: `Equal to`
- Value: `true`

---

### Node 6 : Postgres - Sauvegarder les pronostics

**Type :** Postgres
**Operation :** Insert
**Schema :** `public`
**Table :** `pronostics_unified`

**Columns Mapping :**
```javascript
{
  "id": "={{ $json.id }}",
  "source": "={{ $json.source }}",
  "match": "={{ $json.match }}",
  "home_team": "={{ $json.homeTeam }}",
  "away_team": "={{ $json.awayTeam }}",
  "date_time": "={{ $json.dateTime }}",
  "competition": "={{ $json.competition }}",
  "sport_unified": "={{ $json.sport_unified }}",
  "tip_text_unified": "={{ $json.tipText_unified }}",
  "sport_original": "={{ $json.sport_original }}",
  "tip_text_original": "={{ $json.tipText_original }}",
  "odds": "={{ $json.odds }}",
  "sport_confidence": "={{ $json.sport_confidence }}",
  "tip_text_confidence": "={{ $json.tipText_confidence }}",
  "processed_at": "={{ $json.processed_at }}"
}
```

**SQL pour créer la table :**
```sql
CREATE TABLE IF NOT EXISTS pronostics_unified (
  id VARCHAR(255) PRIMARY KEY,
  source VARCHAR(50),
  match VARCHAR(255),
  home_team VARCHAR(100),
  away_team VARCHAR(100),
  date_time TIMESTAMP,
  competition VARCHAR(100),

  -- Données unifiées
  sport_unified VARCHAR(50),
  tip_text_unified VARCHAR(100),

  -- Données originales
  sport_original VARCHAR(50),
  tip_text_original VARCHAR(255),

  -- Métadonnées
  odds DECIMAL(5,2),
  sport_confidence DECIMAL(3,2),
  tip_text_confidence DECIMAL(3,2),
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- Index
  CONSTRAINT unique_pronostic UNIQUE(id)
);

CREATE INDEX idx_sport_unified ON pronostics_unified(sport_unified);
CREATE INDEX idx_tip_text_unified ON pronostics_unified(tip_text_unified);
CREATE INDEX idx_date_time ON pronostics_unified(date_time);
CREATE INDEX idx_processed_at ON pronostics_unified(processed_at);
```

---

### Node 7 : Airtable - Queue de validation

**Type :** Airtable
**Operation :** Append
**Base ID :** Votre Airtable Base ID
**Table :** `Validation Queue`

**Fields Mapping :**
```javascript
{
  "ID": "={{ $json.id }}",
  "Source": "={{ $json.source }}",
  "Match": "={{ $json.match }}",
  "Sport Original": "={{ $json.sport_original }}",
  "Sport Suggéré": "={{ $json.sport_unified }}",
  "Sport Confidence": "={{ $json.sport_confidence }}",
  "TipText Original": "={{ $json.tipText_original }}",
  "TipText Suggéré": "={{ $json.tipText_unified }}",
  "TipText Confidence": "={{ $json.tipText_confidence }}",
  "Status": "Pending",
  "Created At": "={{ $json.processed_at }}"
}
```

**Structure Airtable suggérée :**
| Colonne | Type | Description |
|---------|------|-------------|
| ID | Single line text | ID unique du pronostic |
| Source | Single select | assopoker, footystats, etc. |
| Match | Single line text | Nom du match |
| Sport Original | Single line text | Valeur brute du scraper |
| Sport Suggéré | Single line text | Valeur unifiée suggérée |
| Sport Validé | Single line text | Valeur après validation humaine |
| Sport Confidence | Number | Score de confiance (0-1) |
| TipText Original | Long text | Valeur brute |
| TipText Suggéré | Single line text | Valeur unifiée suggérée |
| TipText Validé | Single line text | Valeur après validation |
| TipText Confidence | Number | Score de confiance |
| Status | Single select | Pending, Validated, Rejected |
| Created At | Date | Date de création |
| Validated At | Date | Date de validation |
| Validator | Collaborator | Qui a validé |

---

## 🔄 Workflow de validation (bonus)

### Workflow N8N séparé pour apprendre des validations

```
1. [Airtable Trigger] Déclenchement sur update Status = "Validated"
      ↓
2. [Function] Préparer le mapping
      ↓
3. [HTTP Request] POST /mapping/add vers Unification Service
      ↓
4. [Airtable] Marquer comme "Processed"
```

**Node 2 - Function :**
```javascript
const item = $input.first().json;

// Si sport validé différent du suggéré, créer un mapping
const mappings = [];

if (item['Sport Validé'] && item['Sport Validé'] !== item['Sport Suggéré']) {
  mappings.push({
    original: item['Sport Original'],
    unified: item['Sport Validé'],
    type: 'sport'
  });
}

if (item['TipText Validé'] && item['TipText Validé'] !== item['TipText Suggéré']) {
  mappings.push({
    original: item['TipText Original'],
    unified: item['TipText Validé'],
    type: 'tip_type'
  });
}

return mappings.map(m => ({ json: m }));
```

**Node 3 - HTTP Request :**
```
URL: http://localhost:8002/mapping/add
Method: POST
Body: {{ $json }}
```

---

## 📥 Import du workflow N8N (JSON)

Créez un fichier `workflow.json` et importez-le dans N8N :

```json
{
  "name": "Pronostics Unification Workflow",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "scrape-pronostics"
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8002/unify/bulk",
        "jsonParameters": true,
        "options": {},
        "bodyParametersJson": "={{ JSON.stringify({ items: $json.pronostics, threshold: 0.7 }) }}"
      },
      "name": "Unification Service",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Unification Service"}]]
    }
  }
}
```

---

## 🧪 Tester le workflow

### 1. Tester manuellement

**Appel webhook N8N :**
```bash
curl -X POST https://votre-n8n.com/webhook/scrape-pronostics \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["assopoker"],
    "max_tips": 5
  }'
```

### 2. Vérifier les résultats

**Postgres :**
```sql
SELECT
  match,
  sport_original,
  sport_unified,
  sport_confidence,
  tip_text_original,
  tip_text_unified,
  tip_text_confidence
FROM pronostics_unified
ORDER BY processed_at DESC
LIMIT 10;
```

**Airtable :**
Vérifier la table "Validation Queue" pour les items `needs_review = true`

---

## 📊 Dashboard N8N

Ajoutez un node final pour envoyer des stats :

```javascript
// Node Statistics
const allItems = $input.all();

const stats = {
  total: allItems.length,
  validated: allItems.filter(item => !item.json.needs_review).length,
  needs_review: allItems.filter(item => item.json.needs_review).length,
  avg_sport_confidence: allItems.reduce((sum, item) => sum + item.json.sport_confidence, 0) / allItems.length,
  avg_tip_confidence: allItems.reduce((sum, item) => sum + item.json.tipText_confidence, 0) / allItems.length
};

return [{ json: stats }];
```

Envoyez ces stats vers Slack/Discord/Email :

```
📊 Unification Report
✅ Validés : {{ $json.validated }}/{{ $json.total }}
⚠️  À valider : {{ $json.needs_review }}
🎯 Confiance moyenne Sport : {{ $json.avg_sport_confidence.toFixed(2) }}
🎯 Confiance moyenne TipText : {{ $json.avg_tip_confidence.toFixed(2) }}
```

---

## 🎯 Résultat final

Après ce workflow, vous aurez :

✅ **Données unifiées** dans Postgres
✅ **Queue de validation** dans Airtable pour cas incertains
✅ **Auto-apprentissage** via validation humaine
✅ **Métriques** de confiance pour monitoring
✅ **100% automatique** sauf validation manuelle

---

## 🔥 Tips & Best Practices

1. **Threshold de confiance** : Commencez à 0.7, ajustez selon vos besoins
2. **Batch size** : Limitez à 100 pronostics par batch pour N8N
3. **Monitoring** : Ajoutez un node Error Trigger pour capturer les erreurs
4. **Cache** : N8N peut cacher les résultats si besoin
5. **Retry** : Configurez retry sur HTTP Request nodes (3 tentatives max)

---

Vous êtes prêt ! 🚀
