"""
Utility functions for pronostic scrapers
"""
from typing import Dict, List, Any


def deduplicate_pronostics(pronostics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplique les pronostics en fusionnant ceux qui ont les memes caracteristiques.

    Criteres de deduplication:
    - match
    - dateTime
    - homeTeam
    - awayTeam
    - tipText

    En cas de donnees differentes:
    - Prend la plus petite cote (odds)
    - Fusionne les valeurs null avec les valeurs non-null
    """
    if not pronostics:
        return []

    # Dictionnaire pour stocker les pronostics uniques
    # Cle: tuple(match, dateTime, homeTeam, awayTeam, tipText)
    unique_pronostics = {}

    for prono in pronostics:
        # Creer une cle unique basee sur les criteres (sans tipType)
        key = (
            prono.get("match"),
            prono.get("dateTime"),
            prono.get("homeTeam"),
            prono.get("awayTeam"),
            prono.get("tipText")
        )

        if key in unique_pronostics:
            # Pronostic deja existant - fusionner les donnees
            existing = unique_pronostics[key]

            # Fusionner les champs null avec les non-null
            for field in ["match", "dateTime", "competition", "homeTeam", "awayTeam",
                         "tipTitle", "tipType", "tipText", "reasonTip", "confidence"]:
                if existing.get(field) is None and prono.get(field) is not None:
                    existing[field] = prono.get(field)

            # Pour les cotes, prendre la plus petite (meilleure cote)
            existing_odds = existing.get("odds")
            new_odds = prono.get("odds")

            if existing_odds is not None and new_odds is not None:
                existing["odds"] = min(existing_odds, new_odds)
            elif new_odds is not None:
                existing["odds"] = new_odds

        else:
            # Nouveau pronostic - l'ajouter
            unique_pronostics[key] = prono.copy()

    return list(unique_pronostics.values())
