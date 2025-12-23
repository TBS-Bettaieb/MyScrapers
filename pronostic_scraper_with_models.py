"""
Exemple d'integration des modeles dans les scrapers
Version refactorisee avec utilisation des dataclasses
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional
import httpx

from models import Pronostic, PronosticResponse


# =============================================================================
# FONCTION DE DEDUPLICATION AVEC MODELES
# =============================================================================

def deduplicate_pronostics_typed(pronostics: list[Pronostic]) -> list[Pronostic]:
    """
    Deduplique les pronostics en fusionnant ceux qui ont les memes caracteristiques.

    Criteres de deduplication:
    - match, dateTime, homeTeam, awayTeam, tipText

    En cas de donnees differentes:
    - Prend la plus petite cote (odds)
    - Fusionne les valeurs null avec les valeurs non-null
    """
    if not pronostics:
        return []

    # Dictionnaire pour stocker les pronostics uniques
    unique_pronostics: dict[tuple, Pronostic] = {}

    for prono in pronostics:
        key = prono.get_match_key()

        if key in unique_pronostics:
            # Pronostic deja existant - fusionner les donnees
            existing = unique_pronostics[key]

            # Fusionner les champs null avec les non-null
            for field in ["match", "dateTime", "competition", "homeTeam", "awayTeam",
                         "tipTitle", "tipType", "tipText", "reasonTip", "confidence"]:
                existing_value = getattr(existing, field)
                new_value = getattr(prono, field)

                if existing_value is None and new_value is not None:
                    setattr(existing, field, new_value)

            # Pour les cotes, prendre la plus petite (meilleure cote)
            if existing.odds is not None and prono.odds is not None:
                existing.odds = min(existing.odds, prono.odds)
            elif prono.odds is not None:
                existing.odds = prono.odds

        else:
            # Nouveau pronostic - l'ajouter
            unique_pronostics[key] = prono

    return list(unique_pronostics.values())


# =============================================================================
# SCRAPER FREESUPERTIPS AVEC MODELES
# =============================================================================

async def scrape_freesupertips_typed(
    max_tips: Optional[int] = None,
    debug_mode: bool = False
) -> PronosticResponse:
    """
    Scrape les pronostics de FreeSupertips avec retour type

    Args:
        max_tips: Nombre maximum de pronostics a recuperer (None = tous)
        debug_mode: Active les logs detailles

    Returns:
        PronosticResponse: Reponse structuree avec les pronostics
    """
    try:
        url = "https://www.freesupertips.com/_next/data/HOrP8NG9BbfBQJAGCESpF/free-football-betting-tips.json?page_slug=%2Ffree-football-betting-tips%2F"

        if debug_mode:
            print(f"\n[FreeSupertips] Fetching tips from: {url}")

        headers = {
            "accept": "application/json",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        timeout = httpx.Timeout(60.0, connect=30.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        responses = data.get("pageProps", {}).get("responses", {})
        pronostics: list[Pronostic] = []

        # 1. Extraire depuis predictionsFeatured
        predictions_featured = responses.get("predictionsFeatured", [])
        for prediction in predictions_featured:
            tips_list = prediction.get("tips", [])

            for tip_raw in tips_list:
                try:
                    teams = prediction.get("teams", [])
                    home_team = next((t.get("name") for t in teams if t.get("homeAway") == "home"), None)
                    away_team = next((t.get("name") for t in teams if t.get("homeAway") == "away"), None)

                    competition_list = prediction.get("competition", [])
                    competition = competition_list[0].get("name") if competition_list else None

                    start_timestamp = prediction.get("start")
                    date_time = datetime.fromtimestamp(start_timestamp).isoformat() if start_timestamp else None

                    reasoning_data = tip_raw.get("reasoning", {})
                    reasoning_description = reasoning_data.get("description", "")
                    reason_tip = re.sub(r'<[^>]+>', '', reasoning_description).strip()

                    # Creer un objet Pronostic type
                    pronostic = Pronostic(
                        match=f"{home_team} vs {away_team}" if home_team and away_team else prediction.get("name"),
                        dateTime=date_time,
                        competition=competition,
                        homeTeam=home_team,
                        awayTeam=away_team,
                        tipTitle=tip_raw.get("title", ""),
                        tipType=tip_raw.get("title", "").lower().replace(" ", "_"),
                        tipText=tip_raw.get("textOne", ""),
                        reasonTip=reason_tip,
                        odds=tip_raw.get("odds"),
                        confidence=tip_raw.get("confidence")
                    )

                    pronostics.append(pronostic)

                    if max_tips and len(pronostics) >= max_tips:
                        break

                except Exception as e:
                    if debug_mode:
                        print(f"[FreeSupertips] Erreur parsing tip: {str(e)}")
                    continue

            if max_tips and len(pronostics) >= max_tips:
                break

        # 2. Extraire depuis tipsFootball
        if not max_tips or len(pronostics) < max_tips:
            tips_football = responses.get("tipsFootball", [])

            for tip_football in tips_football:
                try:
                    competition_list = tip_football.get("competition", [])
                    competition = competition_list[0].get("name") if competition_list else None

                    type_list = tip_football.get("type", [])
                    tip_type = type_list[0].get("slug") if type_list else None
                    tip_title = tip_football.get("title", "")

                    start_timestamp = tip_football.get("start")
                    date_time = datetime.fromtimestamp(start_timestamp).isoformat() if start_timestamp else None

                    betslip_data = tip_football.get("betslipTableData", {})
                    odds_decimal = betslip_data.get("odds")

                    reasoning_data = tip_football.get("reasoning", {})
                    reasoning_description = reasoning_data.get("description", "")
                    reason_tip = re.sub(r'<[^>]+>', '', reasoning_description).strip()

                    legs = tip_football.get("legs", [])

                    if legs:
                        for leg in legs:
                            try:
                                teams = leg.get("teams", [])
                                home_team = teams[0].get("name") if len(teams) > 0 else None
                                away_team = teams[1].get("name") if len(teams) > 1 else None

                                leg_start = leg.get("start")
                                leg_date_time = datetime.fromtimestamp(leg_start).isoformat() if leg_start else date_time

                                text_one = leg.get("textOne", tip_title)

                                pronostic = Pronostic(
                                    match=leg.get("name") or f"{home_team} vs {away_team}",
                                    dateTime=leg_date_time,
                                    competition=competition,
                                    homeTeam=home_team,
                                    awayTeam=away_team,
                                    tipTitle=tip_title,
                                    tipType=tip_type,
                                    tipText=text_one,
                                    reasonTip=reason_tip,
                                    odds=odds_decimal,
                                    confidence=None
                                )

                                pronostics.append(pronostic)

                                if max_tips and len(pronostics) >= max_tips:
                                    break

                            except Exception as e:
                                if debug_mode:
                                    print(f"[FreeSupertips] Erreur parsing leg: {str(e)}")
                                continue
                    else:
                        pronostic = Pronostic(
                            match=None,
                            dateTime=date_time,
                            competition=competition,
                            homeTeam=None,
                            awayTeam=None,
                            tipTitle=tip_title,
                            tipType=tip_type,
                            tipText=None,
                            reasonTip=reason_tip,
                            odds=odds_decimal,
                            confidence=None
                        )
                        pronostics.append(pronostic)

                    if max_tips and len(pronostics) >= max_tips:
                        break

                except Exception as e:
                    if debug_mode:
                        print(f"[FreeSupertips] Erreur parsing tip: {str(e)}")
                    continue

        if debug_mode:
            print(f"[FreeSupertips] {len(pronostics)} pronostics avant deduplication")

        # Dedupliquer
        pronostics = deduplicate_pronostics_typed(pronostics)

        if debug_mode:
            print(f"[FreeSupertips] {len(pronostics)} pronostics apres deduplication")

        # Retourner une reponse structuree
        return PronosticResponse.success_response(
            pronostics=pronostics,
            source="FreeSupertips"
        )

    except httpx.TimeoutException as e:
        return PronosticResponse.error(
            error_message=f"Timeout lors de la requete: {str(e)}",
            source="FreeSupertips"
        )
    except httpx.HTTPStatusError as e:
        return PronosticResponse.error(
            error_message=f"Erreur HTTP {e.response.status_code}: {e.response.reason_phrase}",
            source="FreeSupertips"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return PronosticResponse.error(
            error_message=f"Erreur inattendue: {str(e)}",
            source="FreeSupertips"
        )


# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

async def main():
    """Exemple d'utilisation du scraper avec modeles"""
    print("=== Test du scraper FreeSupertips avec modeles ===\n")

    # Scraper avec limite
    response = await scrape_freesupertips_typed(max_tips=5, debug_mode=True)

    print(f"\n=== Resultats ===")
    print(f"Success: {response.success}")
    print(f"Source: {response.source}")
    print(f"Total pronostics: {response.total_pronostics}")
    print(f"Error: {response.error_message}")

    if response.success and response.pronostics:
        print(f"\n=== Premier pronostic ===")
        first = response.pronostics[0]
        print(f"Type: {type(first)}")
        print(f"Match: {first.match}")
        print(f"DateTime: {first.dateTime}")
        print(f"Competition: {first.competition}")
        print(f"Tip: {first.tipText}")
        print(f"Odds: {first.odds}")
        print(f"Confidence: {first.confidence}")
        print(f"Is valid: {first.is_valid()}")

        # Conversion en dict pour l'API
        print(f"\n=== Conversion en dict pour API ===")
        api_response = response.to_dict()
        print(f"Keys: {api_response.keys()}")
        print(f"First pronostic dict: {api_response['pronostics'][0]}")


if __name__ == "__main__":
    asyncio.run(main())
