# Projet Python - API Calendrier Économique Investing.com

Ce projet fournit une API REST pour scraper le calendrier économique d'[investing.com](https://www.investing.com/economic-calendar/).

Il utilise FastAPI pour créer une API REST asynchrone qui permet de récupérer les événements économiques avec filtrage par dates, pays, catégories et importance.

## Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Chrome/Chromium (pour Selenium, utilisé uniquement pour l'initialisation des cookies)

## Installation

### 1. Créer un environnement virtuel

Il est recommandé d'utiliser un environnement virtuel pour isoler les dépendances :

```bash
python -m venv venv
```

### 2. Activer l'environnement virtuel

**Sur Windows :**

```bash
venv\Scripts\activate
```

**Sur Linux ou macOS :**

```bash
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Installer ChromeDriver

Le projet utilise Selenium avec Chrome pour initialiser les cookies. Assurez-vous que ChromeDriver est installé et accessible dans votre PATH.

## Utilisation

### Démarrer le serveur API

```bash
python app.py
```

Ou avec uvicorn directement :

```bash
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

Le serveur sera accessible sur `http://localhost:8001`

### Documentation interactive

Une fois le serveur démarré, accédez à la documentation interactive :

- **Swagger UI** : http://localhost:8001/docs
- **ReDoc** : http://localhost:8001/redoc

## Endpoints disponibles

### GET / - Informations sur l'API

Retourne les informations générales sur l'API et la liste des endpoints disponibles.

```bash
curl http://localhost:8001/
```

### GET /health - Vérifier l'état de l'API

Vérifie que l'API fonctionne correctement.

```bash
curl http://localhost:8001/health
```

### GET /scrape/investing - Scraper le calendrier économique (GET)

Récupère les événements économiques via paramètres de requête.

**Paramètres :**
- `date_from` (optionnel) : Date de début au format `YYYY-MM-DD` (défaut: aujourd'hui)
- `date_to` (optionnel) : Date de fin au format `YYYY-MM-DD` (défaut: dans 30 jours)
- `timezone` (optionnel) : ID du fuseau horaire (défaut: 58 pour GMT+1)
- `time_filter` (optionnel) : Filtre temporel (défaut: "timeOnly")

**Exemple :**

```bash
curl "http://localhost:8001/scrape/investing?date_from=2025-01-01&date_to=2025-01-31&timezone=58"
```

### POST /scrape/investing - Scraper le calendrier économique (POST)

Récupère les événements économiques via body JSON avec filtres avancés.

**Body JSON :**

```json
{
  "date_from": "2025-01-01",
  "date_to": "2025-01-31",
  "countries": [5, 6, 17],
  "categories": ["_employment", "_inflation"],
  "importance": [1, 2, 3],
  "timezone": 58,
  "time_filter": "timeOnly"
}
```

**Paramètres :**
- `date_from` (optionnel) : Date de début au format `YYYY-MM-DD`
- `date_to` (optionnel) : Date de fin au format `YYYY-MM-DD`
- `countries` (optionnel) : Liste des IDs de pays à filtrer (None = tous les pays)
- `categories` (optionnel) : Liste des catégories à filtrer (None = toutes les catégories)
- `importance` (optionnel) : Liste des niveaux d'importance [1,2,3] (None = tous)
- `timezone` (optionnel) : ID du fuseau horaire (défaut: 58)
- `time_filter` (optionnel) : Filtre temporel (défaut: "timeOnly")

**Exemple :**

```bash
curl -X POST "http://localhost:8001/scrape/investing" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-01-01",
    "date_to": "2025-01-31",
    "timezone": 58
  }'
```

## Format de réponse

La réponse contient les événements économiques et les jours fériés :

```json
{
  "success": true,
  "events": [
    {
      "time": "10:00",
      "datetime": "2025/01/15 10:00:00",
      "parsed_datetime": "2025-01-15T10:00:00",
      "day": "Wednesday, January 15, 2025",
      "country": "United States",
      "country_code": "USD",
      "event": "Consumer Price Index (MoM)",
      "event_url": "/economic-calendar/consumer-price-index-core-735",
      "actual": "0.3%",
      "forecast": "0.2%",
      "previous": "0.1%",
      "impact": "High",
      "event_id": "537228"
    }
  ],
  "holidays": [
    {
      "type": "holiday",
      "time": "00:00",
      "day": "Wednesday, January 1, 2025",
      "country": "United States",
      "event": "New Year's Day",
      "impact": "Holiday"
    }
  ],
  "date_range": {
    "from": "2025-01-01",
    "to": "2025-01-31"
  },
  "total_events": 150,
  "total_holidays": 3,
  "error_message": null
}
```

## Fonctionnalités

### API REST

- API REST asynchrone avec FastAPI
- Endpoints GET et POST pour le scraping
- Documentation interactive automatique (Swagger/ReDoc)
- Validation des données avec Pydantic
- Gestion d'erreurs HTTP standardisée
- Séparation automatique des événements économiques et jours fériés

### Scraper Investing.com

- Scraping via l'API interne d'investing.com (plus rapide que le scraping HTML)
- Gestion automatique des cookies avec cache (1 heure)
- Découpage automatique par périodes pour contourner les limites de l'API
- Détection et filtrage automatique des doublons
- Support des filtres avancés (pays, catégories, importance)

## Architecture

Le scraper utilise une stratégie de découpage par dates pour contourner les limitations de l'API investing.com :

1. La période demandée est divisée en chunks de 1 jour par défaut
2. Chaque chunk est traité séparément via l'API
3. Les résultats sont agrégés et les doublons sont filtrés
4. Les cookies sont mis en cache pendant 1 heure pour éviter les appels Selenium répétés

## Notes techniques

- Les cookies sont initialisés une seule fois avec Selenium, puis mis en cache
- Les requêtes suivantes utilisent httpx (plus rapide) avec les cookies en cache
- Le scraper gère automatiquement les limites de l'API en découpant les périodes
- Les événements sont parsés depuis le HTML retourné par l'API
