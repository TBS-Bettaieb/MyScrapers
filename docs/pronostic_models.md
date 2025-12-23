# Documentation des Modèles de Données

## Vue d'ensemble

Les modèles de données dans `models.py` fournissent une structure typée et cohérente pour les objets de retour des scrapers de pronostics sportifs (FreeSupertips et FootyAccumulators).

## Classes Disponibles

### 1. `Pronostic` - Modèle d'un pronostic individuel

Représente un seul pronostic sportif avec toutes ses informations.

#### Attributs

| Attribut | Type | Description | Exemple |
|----------|------|-------------|---------|
| `match` | `Optional[str]` | Nom complet du match | `"Manchester United vs Liverpool"` |
| `dateTime` | `Optional[str]` | Date/heure du match (ISO format) | `"2025-12-23T15:00:00"` |
| `competition` | `Optional[str]` | Nom de la compétition | `"Premier League"` |
| `homeTeam` | `Optional[str]` | Équipe à domicile | `"Manchester United"` |
| `awayTeam` | `Optional[str]` | Équipe à l'extérieur | `"Liverpool"` |
| `tipTitle` | `Optional[str]` | Titre du pronostic | `"Both Teams To Score"` |
| `tipType` | `Optional[str]` | Type de pronostic (snake_case) | `"both_teams_to_score"` |
| `tipText` | `Optional[str]` | Texte descriptif du pronostic | `"Yes - Both Teams To Score"` |
| `reasonTip` | `Optional[str]` | Raison/analyse du pronostic | `"Both teams have strong..."` |
| `odds` | `Optional[float]` | Cote décimale | `1.85` |
| `confidence` | `Optional[str]` | Niveau de confiance | `"high"`, `"medium"`, `"low"` |

#### Méthodes

- **`to_dict()`**: Convertit le pronostic en dictionnaire
- **`from_dict(data)`**: Crée un pronostic depuis un dictionnaire
- **`is_valid()`**: Vérifie si le pronostic contient les informations minimales
- **`get_match_key()`**: Retourne une clé unique pour identifier le pronostic (utilisé pour la déduplication)

#### Exemples d'utilisation

```python
from models import Pronostic

# Création d'un pronostic
prono = Pronostic(
    match="Arsenal vs Chelsea",
    dateTime="2025-12-24T18:00:00",
    competition="Premier League",
    homeTeam="Arsenal",
    awayTeam="Chelsea",
    tipTitle="Match Result",
    tipType="match_result",
    tipText="Arsenal to Win",
    reasonTip="Arsenal has home advantage and is in great form",
    odds=2.10,
    confidence="medium"
)

# Conversion en dictionnaire
prono_dict = prono.to_dict()

# Création depuis un dictionnaire
prono2 = Pronostic.from_dict(prono_dict)

# Vérification de validité
if prono.is_valid():
    print("Pronostic valide")

# Obtenir la clé unique (pour déduplication)
key = prono.get_match_key()
```

### 2. `PronosticResponse` - Modèle de réponse du scraper

Représente la réponse complète d'un scraper, incluant tous les pronostics récupérés et le statut de l'opération.

#### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Indique si le scraping a réussi |
| `pronostics` | `List[Pronostic]` | Liste des pronostics récupérés |
| `total_pronostics` | `int` | Nombre total de pronostics |
| `error_message` | `Optional[str]` | Message d'erreur (si `success=False`) |
| `source` | `Optional[str]` | Source des pronostics (ex: "FreeSupertips") |

#### Méthodes

- **`to_dict()`**: Convertit la réponse en dictionnaire compatible avec l'API
- **`from_dict(data)`**: Crée une réponse depuis un dictionnaire
- **`error(error_message, source)`**: Factory method pour créer une réponse d'erreur
- **`success_response(pronostics, source)`**: Factory method pour créer une réponse de succès

#### Exemples d'utilisation

```python
from models import Pronostic, PronosticResponse

# Création d'une réponse de succès
pronostics = [
    Pronostic(match="Team A vs Team B", tipText="Prediction 1", odds=1.50),
    Pronostic(match="Team C vs Team D", tipText="Prediction 2", odds=2.00)
]

response = PronosticResponse.success_response(
    pronostics=pronostics,
    source="FreeSupertips"
)

# Création d'une réponse d'erreur
error_response = PronosticResponse.error(
    error_message="Timeout lors de la requête",
    source="FootyAccumulators"
)

# Conversion en dictionnaire (pour l'API)
response_dict = response.to_dict()

# Création depuis un dictionnaire
response2 = PronosticResponse.from_dict(response_dict)
```

## Intégration avec les Scrapers

### Exemple de modification d'un scraper

Voici comment modifier un scraper existant pour utiliser les modèles :

```python
async def scrape_freesupertips(max_tips=None, debug_mode=False) -> PronosticResponse:
    """
    Scrape les pronostics de FreeSupertips

    Returns:
        PronosticResponse: Réponse structurée avec les pronostics
    """
    try:
        # ... code de scraping ...

        # Conversion des dictionnaires en objets Pronostic
        pronostics_obj = [Pronostic.from_dict(p) for p in pronostics_dicts]

        # Retourner une réponse structurée
        return PronosticResponse.success_response(
            pronostics=pronostics_obj,
            source="FreeSupertips"
        )

    except Exception as e:
        # Retourner une réponse d'erreur
        return PronosticResponse.error(
            error_message=f"Erreur: {str(e)}",
            source="FreeSupertips"
        )
```

### Utilisation dans l'API

```python
from fastapi import APIRouter
from models import PronosticResponse

router = APIRouter()

@router.get("/scrape/freesupertips", response_model=dict)
async def get_freesupertips_tips(max_tips: int = None):
    """Endpoint pour récupérer les pronostics FreeSupertips"""
    response = await scrape_freesupertips(max_tips=max_tips)
    return response.to_dict()
```

## Avantages des Modèles

1. **Type Safety**: Les dataclasses fournissent une vérification de type au moment du développement
2. **Documentation**: Les types et les docstrings facilitent la compréhension du code
3. **Validation**: Méthodes `is_valid()` pour vérifier la cohérence des données
4. **Conversion facile**: Méthodes `to_dict()` et `from_dict()` pour la sérialisation
5. **Cohérence**: Structure identique pour tous les scrapers
6. **Maintenance**: Facile de modifier la structure une seule fois pour tous les scrapers

## Tests

Pour exécuter les tests des modèles :

```bash
python test_models.py
```

Les tests vérifient :
- Création de pronostics
- Conversion dict ↔ objet
- Validation des données
- Réponses de succès et d'erreur
- Intégration avec les scrapers réels
