"""
FreeSupertips scraper
"""
import re
from datetime import datetime
from typing import Dict, Optional, Any
import httpx

from .utils import deduplicate_pronostics


async def scrape_freesupertips(
    max_tips: Optional[int] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Scrape les pronostics de FreeSupertips de maniere simplifiee

    Args:
        max_tips: Nombre maximum de pronostics a recuperer (None = tous)
        debug_mode: Active les logs detailles

    Returns:
        Dictionnaire contenant:
        - success: bool
        - pronostics: Liste des pronostics
        - total_pronostics: int
        - error_message: Optional[str]
    """
    try:
        url = "https://www.freesupertips.com/_next/data/HOrP8NG9BbfBQJAGCESpF/free-football-betting-tips.json?page_slug=%2Ffree-football-betting-tips%2F"

        if debug_mode:
            print(f"\n[FreeSupertips] Fetching tips from: {url}")

        headers = {
            "accept": "application/json",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }

        timeout = httpx.Timeout(60.0, connect=30.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Extraire les tips depuis pageProps > responses
        responses = data.get("pageProps", {}).get("responses", {})

        pronostics = []

        # 1. Extraire depuis predictionsFeatured
        predictions_featured = responses.get("predictionsFeatured", [])
        for prediction in predictions_featured:
            tips_list = prediction.get("tips", [])

            for tip_raw in tips_list:
                try:
                    # Informations du match depuis prediction
                    teams = prediction.get("teams", [])
                    home_team = None
                    away_team = None

                    for team in teams:
                        if team.get("homeAway") == "home":
                            home_team = team.get("name")
                        elif team.get("homeAway") == "away":
                            away_team = team.get("name")

                    # Competition
                    competition_list = prediction.get("competition", [])
                    competition = competition_list[0].get("name") if competition_list else None

                    # DateTime
                    start_timestamp = prediction.get("start")
                    date_time = datetime.fromtimestamp(start_timestamp).isoformat() if start_timestamp else None

                    # Tip info
                    tip_title = tip_raw.get("title", "")
                    tip_type = tip_raw.get("title", "").lower().replace(" ", "_")
                    tip_text = tip_raw.get("textOne", "")
                    odds_decimal = tip_raw.get("odds")
                    confidence = tip_raw.get("confidence")

                    # Reasoning
                    reasoning_data = tip_raw.get("reasoning", {})
                    reasoning_description = reasoning_data.get("description", "")
                    # Nettoyer le HTML du reasoning
                    reason_tip = re.sub(r'<[^>]+>', '', reasoning_description).strip()

                    pronostic = {
                        "match": f"{home_team} vs {away_team}" if home_team and away_team else prediction.get("name"),
                        "dateTime": date_time,
                        "competition": competition,
                        "homeTeam": home_team,
                        "awayTeam": away_team,
                        "tipTitle": tip_title,
                        "tipType": tip_type,
                        "tipText": tip_text,
                        "reasonTip": reason_tip,
                        "odds": odds_decimal,
                        "confidence": confidence
                    }

                    pronostics.append(pronostic)

                    if max_tips and len(pronostics) >= max_tips:
                        break

                except Exception as e:
                    if debug_mode:
                        print(f"[FreeSupertips] Erreur parsing tip (predictionsFeatured): {str(e)}")
                    continue

            if max_tips and len(pronostics) >= max_tips:
                break

        # 2. Extraire depuis tipsFootball
        if not max_tips or len(pronostics) < max_tips:
            tips_football = responses.get("tipsFootball", [])

            for tip_football in tips_football:
                try:
                    # Competition
                    competition_list = tip_football.get("competition", [])
                    competition = competition_list[0].get("name") if competition_list else None

                    # Type de tip
                    type_list = tip_football.get("type", [])
                    tip_type = type_list[0].get("slug") if type_list else None
                    tip_title = tip_football.get("title", "")

                    # DateTime
                    start_timestamp = tip_football.get("start")
                    date_time = datetime.fromtimestamp(start_timestamp).isoformat() if start_timestamp else None

                    # Odds depuis betslipTableData
                    betslip_data = tip_football.get("betslipTableData", {})
                    odds_decimal = betslip_data.get("odds")

                    # Reasoning
                    reasoning_data = tip_football.get("reasoning", {})
                    reasoning_description = reasoning_data.get("description", "")
                    reason_tip = re.sub(r'<[^>]+>', '', reasoning_description).strip()

                    # Legs (matchs)
                    legs = tip_football.get("legs", [])

                    # Si c'est un accumulateur avec plusieurs legs, on cree un pronostic par leg
                    if legs:
                        for leg in legs:
                            try:
                                teams = leg.get("teams", [])
                                home_team = teams[0].get("name") if len(teams) > 0 else None
                                away_team = teams[1].get("name") if len(teams) > 1 else None

                                leg_start = leg.get("start")
                                leg_date_time = datetime.fromtimestamp(leg_start).isoformat() if leg_start else date_time

                                # TextOne contient souvent le tip specifique pour ce leg
                                text_one = leg.get("textOne", tip_title)

                                pronostic = {
                                    "match": leg.get("name") or f"{home_team} vs {away_team}",
                                    "dateTime": leg_date_time,
                                    "competition": competition,
                                    "homeTeam": home_team,
                                    "awayTeam": away_team,
                                    "tipTitle": tip_title,
                                    "tipType": tip_type,
                                    "tipText": text_one,
                                    "reasonTip": reason_tip,
                                    "odds": odds_decimal,
                                    "confidence": None  # Pas de confidence dans tipsFootball
                                }

                                pronostics.append(pronostic)

                                if max_tips and len(pronostics) >= max_tips:
                                    break

                            except Exception as e:
                                if debug_mode:
                                    print(f"[FreeSupertips] Erreur parsing leg: {str(e)}")
                                continue
                    else:
                        # Tip simple sans legs
                        pronostic = {
                            "match": None,
                            "dateTime": date_time,
                            "competition": competition,
                            "homeTeam": None,
                            "awayTeam": None,
                            "tipTitle": tip_title,
                            "tipType": tip_type,
                            "tipText": None,
                            "reasonTip": reason_tip,
                            "odds": odds_decimal,
                            "confidence": None
                        }

                        pronostics.append(pronostic)

                    if max_tips and len(pronostics) >= max_tips:
                        break

                except Exception as e:
                    if debug_mode:
                        print(f"[FreeSupertips] Erreur parsing tip (tipsFootball): {str(e)}")
                    continue

        if debug_mode:
            print(f"[FreeSupertips] {len(pronostics)} pronostics extraits avant deduplication")

        # Dedupliquer les pronostics
        pronostics = deduplicate_pronostics(pronostics)

        if debug_mode:
            print(f"[FreeSupertips] {len(pronostics)} pronostics apres deduplication")

        return {
            "success": True,
            "pronostics": pronostics,
            "total_pronostics": len(pronostics),
            "error_message": None
        }

    except httpx.TimeoutException as e:
        error_msg = f"Timeout lors de la requete: {str(e)}"
        print(f"[FreeSupertips ERROR] {error_msg}")
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
    except httpx.HTTPStatusError as e:
        error_msg = f"Erreur HTTP {e.response.status_code}: {e.response.reason_phrase}"
        print(f"[FreeSupertips ERROR] {error_msg}")
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
    except Exception as e:
        import traceback
        error_msg = f"Erreur inattendue: {str(e)}"
        print(f"[FreeSupertips ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
