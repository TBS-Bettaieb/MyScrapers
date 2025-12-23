"""
FootyAccumulators scraper
"""
import json
from datetime import datetime
from typing import Dict, Optional, Any
import httpx

from .utils import deduplicate_pronostics


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
