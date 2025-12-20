# Optimisation de la Pagination - Investing.com Scraper

## Problème Initial

Le système utilisait une pagination par **offset simple** (`limit_from=0, 200, 400...`) qui ne correspondait pas au mécanisme réel de l'API Investing.com.

## Solution Implémentée

### 1. Pagination par Curseur (Cursor-based Pagination)

L'API Investing.com utilise une **pagination par curseur** basée sur les IDs des événements déjà reçus:

```python
# Premier appel
limit_from=0  # Pas de pids[]

# Appels suivants
limit_from=1  # Toujours 1
pids[]=event-537228:
pids[]=event-537799:
pids[]=event-537229:
# ... tous les IDs déjà reçus
```

### 2. Format des IDs

Les IDs d'événements doivent être envoyés au format:
- `event-{id}:` (avec le préfixe "event-" et deux-points final)
- Exemple: `event-537228:`

### 3. Détection et Filtrage des Doublons

L'API retourne souvent des événements en double. Le système implémente maintenant:

- **Suivi des IDs uniques** : Liste `all_event_ids` pour tracker tous les IDs déjà récupérés
- **Filtrage des doublons** : Vérification avant d'ajouter chaque événement
- **Arrêt intelligent** : Si une page ne contient que des doublons (0 nouveaux événements), la pagination s'arrête

### 4. Amélioration de l'Extraction des IDs

Tous les types d'événements ont maintenant un `event_id`:
- **Événements économiques** : ID extrait de l'attribut `id` du `<tr>`
- **Jours fériés (holidays)** : ID également extrait de `eventRowId_xxx`

## Résultats

### Avant l'optimisation
- ❌ Boucles infinies détectées après 3-5 pages identiques
- ❌ 1658 événements collectés (avec beaucoup de doublons)
- ❌ Pagination inefficace et lente

### Après l'optimisation
- ✅ Arrêt automatique à la page 3 (plus de nouveaux événements)
- ✅ 416 événements uniques collectés
- ✅ Filtrage automatique de 767 doublons (30 + 262 + 475)
- ✅ Performance améliorée (3 pages au lieu de 5+)

## Statistiques Détaillées

```
Page 1: 233 événements bruts → 203 uniques (30 doublons filtrés)
Page 2: 475 événements bruts → 213 nouveaux (262 doublons filtrés)
Page 3: 475 événements bruts → 0 nouveaux (475 doublons filtrés) → STOP
----------------------------------------
Total:  1183 événements bruts → 416 uniques
Taux de déduplication: 64.8%
```

## Code Clé

### Ajout des IDs dans les paramètres POST

```python
# Ajouter les IDs des événements précédents (pagination par curseur)
if previous_event_ids:
    for event_id in previous_event_ids:
        # Format: "event-537228:" (avec deux points à la fin)
        if not event_id.startswith("event-"):
            event_id = f"event-{event_id}"
        if not event_id.endswith(":"):
            event_id = f"{event_id}:"
        params.append(("pids[]", event_id))
```

### Déduplication Intelligente

```python
for event in page_events:
    event_id = event.get("event_id", "")

    # Vérifier si cet événement existe déjà (par ID)
    is_duplicate = event_id in all_event_ids if event_id else False

    if not is_duplicate:
        all_events.append(event)
        if event_id:
            all_event_ids.append(event_id)

# Arrêter si aucun nouvel événement
if new_events_count == 0:
    has_more_data = False
```

## Avantages de l'Optimisation

1. ✅ **Performance** : 40% moins de requêtes (3 pages au lieu de 5+)
2. ✅ **Précision** : Élimination des doublons (416 vs 1658 événements)
3. ✅ **Fiabilité** : Arrêt automatique sans détection de boucle
4. ✅ **Conformité** : Utilise le même mécanisme que le navigateur
5. ✅ **Efficacité réseau** : Moins de données transférées

## Notes Importantes

- Le paramètre `limit_from` doit être `0` pour la première page et `1` pour toutes les pages suivantes
- L'API peut retourner jusqu'à ~475 événements par page (variable selon les filtres)
- Certains événements économiques partagent le même ID (ex: CPI MoM/YoY)
- Les jours fériés ont également des IDs uniques
