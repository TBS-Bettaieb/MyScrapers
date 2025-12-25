"""
Utility functions for pronostic scrapers
"""
import re
from typing import Dict, List, Any


def generate_pronostic_id(source: str, home_team: str, away_team: str, date_time: str, tip_text: str) -> str:
    """
    Generate a unique ID for a pronostic by concatenating fields and replacing whitespace with underscores.

    Args:
        source: Source scraper name (e.g., 'footyaccumulators', 'freesupertips', 'assopoker')
        home_team: Home team name
        away_team: Away team name
        date_time: DateTime in ISO format
        tip_text: Tip text/selection

    Returns:
        Unique ID string with format: source_hometeam_awayteam_date_tiptext
    """
    # Handle None values
    home = str(home_team or '').strip()
    away = str(away_team or '').strip()
    date = str(date_time or '').strip()
    tip = str(tip_text or '').strip()

    # Concatenate fields
    id_parts = [source, home, away, date, tip]

    # Join with underscore and replace all whitespace with underscore
    id_string = '_'.join(id_parts)

    # Replace all whitespace (spaces, tabs, newlines) with single underscore
    id_string = re.sub(r'\s+', '_', id_string)

    # Remove special characters that might cause issues
    id_string = re.sub(r'[^\w\-_.]', '_', id_string)

    # Replace multiple consecutive underscores with single underscore
    id_string = re.sub(r'_+', '_', id_string)

    # Remove leading/trailing underscores
    id_string = id_string.strip('_')

    return id_string


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
