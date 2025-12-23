"""
Scraper specialise pour les pronostics sportifs
Supporte FreeSupertips (FootyAccumulators sera supprime)
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx


# =============================================================================
# FONCTION DE DEDUPLICATION
# =============================================================================

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


# =============================================================================
# SCRAPER FREESUPERTIPS SIMPLIFIE
# =============================================================================

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
                    import re
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


# =============================================================================
# SCRAPER FOOTYACCUMULATORS
# =============================================================================

async def scrape_footyaccumulators(
    max_tips: Optional[int] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Scrape les pronostics de FootyAccumulators

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
        # Etape 1: Recuperer la liste des liens de tips depuis la page principale
        main_url = "https://footyaccumulators.com/_next/data/lbPquX0iFiZiakOZ9G_Oc/football-tips.json?locale=fr"

        if debug_mode:
            print(f"\n[FootyAccumulators] Fetching tip links from: {main_url}")

        headers = {
            "accept": "application/json",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }

        timeout = httpx.Timeout(60.0, connect=30.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(main_url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Extraire footerTipLinks
        footer_tip_links = data.get("footerTipLinks", [])

        if debug_mode:
            print(f"[FootyAccumulators] Found {len(footer_tip_links)} tip categories")

        pronostics = []

        # Etape 2: Pour chaque lien, recuperer les tips
        for link_info in footer_tip_links:
            if max_tips and len(pronostics) >= max_tips:
                break

            full_url_path = link_info.get("full_url_path", "")
            category_title = link_info.get("title", "")

            if not full_url_path:
                continue

            # Construire l'URL de la page de tips
            tip_url = f"https://footyaccumulators.com/_next/data/lbPquX0iFiZiakOZ9G_Oc/{full_url_path}.json"

            if debug_mode:
                print(f"\n[FootyAccumulators] Fetching {category_title} from: {tip_url}")

            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(tip_url, headers=headers)
                    response.raise_for_status()
                    tip_data = response.json()

                # Extraire les widgets de la page
                widgets = tip_data.get("pageProps", {}).get("page", {}).get("meta", {}).get("widgets", [])

                # Chercher les widgets de type "Tipster"
                for widget in widgets:
                    if widget.get("component") != "Tipster":
                        continue

                    # Extraire les tips depuis widget.data.tips
                    tips = widget.get("data", {}).get("tips", [])

                    for tip_raw in tips:
                        if max_tips and len(pronostics) >= max_tips:
                            break

                        try:
                            # Extraire les informations du tip
                            tip_meta = tip_raw.get("meta", {})
                            tip_title = tip_meta.get("title", category_title)

                            # Extraire les matchs depuis grid
                            grid = tip_meta.get("grid", [])

                            # Informations generales du tip
                            starts_at = tip_raw.get("starts_at")
                            expires_at = tip_raw.get("expires_at")

                            date_time = None
                            if starts_at:
                                date_time = datetime.fromtimestamp(starts_at / 1000).isoformat()

                            # Extraire les odds depuis outcomes.odds
                            odds_value = None
                            outcomes = tip_raw.get("outcomes", {})
                            odds_list = outcomes.get("odds", [])
                            if odds_list:
                                # Prendre la valeur minimale des odds decimales
                                decimal_odds = [odd.get("oddsDecimal") for odd in odds_list if odd.get("oddsDecimal")]
                                if decimal_odds:
                                    odds_value = min(decimal_odds)

                            # Si c'est un accumulateur avec plusieurs matchs
                            if grid:
                                for match_info in grid:
                                    try:
                                        match_data = match_info.get("match", {})
                                        selection = match_info.get("selection", {})
                                        market = match_info.get("market", {})

                                        home_team = match_data.get("team_a_name")
                                        away_team = match_data.get("team_b_name")
                                        competition = match_data.get("competition_name")

                                        # DateTime du match
                                        match_date_iso = match_data.get("date_iso")
                                        if match_date_iso:
                                            match_date_time = datetime.fromisoformat(match_date_iso.replace('Z', '+00:00')).isoformat()
                                        else:
                                            match_date_time = date_time

                                        # Selection info
                                        selection_name = selection.get("headline") or selection.get("name", "")
                                        market_name = market.get("name", "")

                                        # Raison (description du tip)
                                        reason_json = match_info.get("reason", "{}")
                                        reason_text = ""
                                        try:
                                            reason_data = json.loads(reason_json) if isinstance(reason_json, str) else reason_json
                                            blocks = reason_data.get("blocks", [])
                                            reason_text = " ".join([block.get("text", "") for block in blocks])
                                        except:
                                            reason_text = str(reason_json)

                                        pronostic = {
                                            "match": f"{home_team} vs {away_team}" if home_team and away_team else None,
                                            "dateTime": match_date_time,
                                            "competition": competition,
                                            "homeTeam": home_team,
                                            "awayTeam": away_team,
                                            "tipTitle": tip_title,
                                            "tipType": category_title.lower().replace(" ", "_"),
                                            "tipText": selection_name,
                                            "reasonTip": reason_text,
                                            "odds": odds_value,
                                            "confidence": None
                                        }

                                        pronostics.append(pronostic)

                                    except Exception as e:
                                        if debug_mode:
                                            print(f"[FootyAccumulators] Erreur parsing match: {str(e)}")
                                        continue
                            else:
                                # Tip simple sans grid
                                pronostic = {
                                    "match": None,
                                    "dateTime": date_time,
                                    "competition": None,
                                    "homeTeam": None,
                                    "awayTeam": None,
                                    "tipTitle": tip_title,
                                    "tipType": category_title.lower().replace(" ", "_"),
                                    "tipText": None,
                                    "reasonTip": None,
                                    "odds": odds_value,
                                    "confidence": None
                                }

                                pronostics.append(pronostic)

                        except Exception as e:
                            if debug_mode:
                                print(f"[FootyAccumulators] Erreur parsing tip: {str(e)}")
                            continue

            except Exception as e:
                if debug_mode:
                    print(f"[FootyAccumulators] Erreur fetching {category_title}: {str(e)}")
                continue

        if debug_mode:
            print(f"\n[FootyAccumulators] {len(pronostics)} pronostics extraits avant deduplication")

        # Dedupliquer les pronostics
        pronostics = deduplicate_pronostics(pronostics)

        if debug_mode:
            print(f"[FootyAccumulators] {len(pronostics)} pronostics apres deduplication")

        return {
            "success": True,
            "pronostics": pronostics,
            "total_pronostics": len(pronostics),
            "error_message": None
        }

    except httpx.TimeoutException as e:
        error_msg = f"Timeout lors de la requete: {str(e)}"
        print(f"[FootyAccumulators ERROR] {error_msg}")
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
    except httpx.HTTPStatusError as e:
        error_msg = f"Erreur HTTP {e.response.status_code}: {e.response.reason_phrase}"
        print(f"[FootyAccumulators ERROR] {error_msg}")
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
    except Exception as e:
        import traceback
        error_msg = f"Erreur inattendue: {str(e)}"
        print(f"[FootyAccumulators ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }
