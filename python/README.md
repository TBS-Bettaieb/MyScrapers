# Projet Python - Scraping Web avec Crawl4AI

Ce projet permet de scraper des pages web en utilisant la bibliothèque [Crawl4AI](https://docs.crawl4ai.com/).

Il propose deux modes d'utilisation :

- **Script CLI** : Utilisation en ligne de commande
- **API REST** : Service web avec FastAPI pour intégration dans d'autres applications

## Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

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

## Utilisation

### Mode 1 : Script CLI

#### Scraper une URL spécifique

```bash
python scraper.py https://www.example.com
```

#### Utiliser l'URL par défaut

Si aucune URL n'est fournie, le script utilisera `https://www.example.com` par défaut :

```bash
python scraper.py
```

### Mode 2 : API REST

#### Démarrer le serveur API

```bash
python app.py
```

Ou avec uvicorn directement :

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Le serveur sera accessible sur `http://localhost:8000`

#### Documentation interactive

Une fois le serveur démarré, accédez à la documentation interactive :

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

#### Endpoints disponibles

**GET /** - Informations sur l'API

```bash
curl http://localhost:8000/
```

**GET /health** - Vérifier l'état de l'API

```bash
curl http://localhost:8000/health
```

**GET /scrape** - Scraper via query parameter

```bash
curl "http://localhost:8000/scrape?url=https://www.example.com"
```

**POST /scrape** - Scraper via body JSON

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.example.com"}'
```

#### Exemple de réponse

```json
{
  "success": true,
  "url": "https://www.example.com",
  "markdown": "# Example Domain\n\nThis domain is for use...",
  "content_length": 1234,
  "error_message": null
}
```

## Fonctionnalités

### Script CLI

- Scraping asynchrone de pages web
- Extraction du contenu en format Markdown
- Gestion d'erreurs basique
- Support des arguments en ligne de commande

### API REST

- API REST asynchrone avec FastAPI
- Endpoints GET et POST pour le scraping
- Documentation interactive automatique (Swagger/ReDoc)
- Validation des données avec Pydantic
- Gestion d'erreurs HTTP standardisée
- Support CORS (configurable)

## Exemple de sortie

```
Scraping de l'URL : https://www.example.com
--------------------------------------------------

=== CONTENU MARKDOWN ===

# Example Domain

This domain is for use in illustrative examples in documents...

==================================================

✓ Scraping réussi !
  - Longueur du contenu : 1234 caractères
```

## Documentation

Pour plus d'informations sur Crawl4AI, consultez la [documentation officielle](https://docs.crawl4ai.com/).
