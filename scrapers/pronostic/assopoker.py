"""
AssoPoker scraper avec Selenium
"""
import re
import time
from datetime import datetime
from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import deduplicate_pronostics, generate_pronostic_id


def _setup_chrome_driver() -> webdriver.Chrome:
    """
    Configure le driver Chrome avec options

    Returns:
        Driver Chrome configuré
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')

    # Activer la traduction automatique en français
    prefs = {
        'translate': {'enabled': True},
        'translate_whitelists': {'it': 'fr'},
        'translate.enabled': True
    }
    chrome_options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(options=chrome_options)
    return driver


async def scrape_assopoker(
    max_tips: Optional[int] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Scrape les pronostics de AssoPoker avec Selenium
    La page est automatiquement traduite en français par Chrome

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
    driver = None
    try:
        pronostics = []

        # Configurer le driver
        driver = _setup_chrome_driver()

        # Etape 1: Scraper la page schedine-oggi
        schedine_url = "https://www.assopoker.com/scommesse/schedine-oggi/"

        if debug_mode:
            print(f"\n[AssoPoker] Fetching schedine from: {schedine_url}")

        try:
            driver.get(schedine_url)

            # Attendre que la page soit chargée
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "block-schedina"))
            )

            # Attendre la traduction
            time.sleep(2)

            # Récupérer le HTML
            html = driver.page_source
            schedine_pronostics = _parse_schedine_page(html, debug_mode)
            pronostics.extend(schedine_pronostics)

            if debug_mode:
                print(f"[AssoPoker] Extracted {len(schedine_pronostics)} pronostics from schedine-oggi")

        except Exception as e:
            if debug_mode:
                print(f"[AssoPoker] Error fetching schedine-oggi: {str(e)}")

        # Etape 2: Scraper la page pronostici-oggi
        if not max_tips or len(pronostics) < max_tips:
            pronostici_url = "https://www.assopoker.com/scommesse/pronostici-oggi/"

            if debug_mode:
                print(f"\n[AssoPoker] Fetching pronostici from: {pronostici_url}")

            try:
                driver.get(pronostici_url)

                # Attendre le chargement (articles ou block-daily-tip)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "block-daily-tip"))
                    )
                except:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )

                # Attendre la traduction
                time.sleep(2)

                # Récupérer le HTML
                html = driver.page_source
                pronostici_pronostics = _parse_pronostici_page(html, debug_mode)
                pronostics.extend(pronostici_pronostics)

                if debug_mode:
                    print(f"[AssoPoker] Extracted {len(pronostici_pronostics)} pronostics from pronostici-oggi")

            except Exception as e:
                if debug_mode:
                    print(f"[AssoPoker] Error fetching pronostici-oggi: {str(e)}")

        if debug_mode:
            print(f"\n[AssoPoker] {len(pronostics)} pronostics extraits avant deduplication")

        # Dedupliquer les pronostics
        pronostics = deduplicate_pronostics(pronostics)

        if debug_mode:
            print(f"[AssoPoker] {len(pronostics)} pronostics apres deduplication")

        # Limiter au nombre max demande
        if max_tips:
            pronostics = pronostics[:max_tips]

        return {
            "success": True,
            "pronostics": pronostics,
            "total_pronostics": len(pronostics),
            "error_message": None
        }

    except Exception as e:
        import traceback
        error_msg = f"Erreur inattendue: {str(e)}"
        print(f"[AssoPoker ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "pronostics": [],
            "total_pronostics": 0,
            "error_message": error_msg
        }

    finally:
        if driver:
            driver.quit()


def _parse_schedine_page(html: str, debug_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Parse la page schedine-oggi pour extraire les pronostics

    Args:
        html: Contenu HTML de la page
        debug_mode: Active les logs detailles

    Returns:
        Liste des pronostics extraits
    """
    pronostics = []
    soup = BeautifulSoup(html, 'html.parser')

    # Trouver tous les blocs schedina
    schedina_blocks = soup.find_all(class_='block-schedina')

    if debug_mode:
        print(f"[AssoPoker] Found {len(schedina_blocks)} schedina blocks")

    for block in schedina_blocks:
        try:
            # Extraire le titre (contient la date)
            title_elem = block.find(class_='papion-block-title')
            schedina_title = title_elem.get_text(strip=True) if title_elem else ""

            # Mapping des mois en français (page traduite)
            month_map = {
                'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
                # Aussi supporter l'italien au cas où
                'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
                'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
                'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
            }

            # Extraire la date depuis le titre
            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', schedina_title, re.IGNORECASE)
            schedina_date = None
            if date_match:
                try:
                    day, month_name, year = date_match.groups()
                    month = month_map.get(month_name.lower(), 1)
                    schedina_date = datetime(int(year), month, int(day))
                except:
                    pass

            # Trouver la table de pronostics
            table = block.find('table')
            if not table:
                continue

            tbody = table.find('tbody')
            if not tbody:
                continue

            rows = tbody.find_all('tr')

            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue

                    # Cellule 0: Match + DateTime
                    match_cell = cells[0].get_text(strip=True)

                    # ETAPE 1: Extraire la date/heure si presente
                    # Formats possibles:
                    # - "Birmingham vs Derby,26 décembre à 13h30"
                    # - "Birmingham vs Derby le 26 décembre à 13h30"
                    # - "Birmingham vs Derby 26 décembre - 13:30"
                    date_time = None
                    time_match = None

                    # Chercher heure au format "13h30" ou "13:30"
                    time_pattern = r'(?:à|ore)\s+(\d{1,2})h(\d{2})|(\d{2}):(\d{2})'
                    time_match = re.search(time_pattern, match_cell)

                    if time_match and schedina_date:
                        if time_match.group(1):  # Format "13h30"
                            hour, minute = int(time_match.group(1)), int(time_match.group(2))
                        else:  # Format "13:30"
                            hour, minute = int(time_match.group(3)), int(time_match.group(4))
                        date_time = schedina_date.replace(hour=hour, minute=minute).isoformat()

                    # ETAPE 2: Nettoyer le texte pour extraire uniquement le match
                    # Supprimer tout ce qui est après la date (date + heure)
                    match_clean = re.sub(r',?\s*\d{1,2}\s+\w+.*$', '', match_cell)
                    match_clean = re.sub(r'\s+le\s+\d{1,2}\s+\w+.*$', '', match_clean)
                    # Supprimer ",le" orphelin en fin de ligne (artefact de traduction)
                    match_clean = re.sub(r',\s*le\s*$', '', match_clean)

                    # ETAPE 3: Extraire les equipes
                    # Gerer " - ", " vs ", " contre "
                    home_team = None
                    away_team = None
                    match_name = match_clean.strip()

                    # Essayer avec "contre"
                    if ' contre ' in match_name.lower():
                        teams = re.split(r'\s+contre\s+', match_name, flags=re.IGNORECASE)
                        if len(teams) == 2:
                            home_team = teams[0].strip()
                            away_team = teams[1].strip()
                    # Essayer avec " vs "
                    elif ' vs ' in match_name.lower():
                        teams = re.split(r'\s+vs\s+', match_name, flags=re.IGNORECASE)
                        if len(teams) == 2:
                            home_team = teams[0].strip()
                            away_team = teams[1].strip()
                    # Essayer avec " - "
                    elif ' - ' in match_name:
                        teams = match_name.split(' - ')
                        if len(teams) == 2:
                            home_team = teams[0].strip()
                            away_team = teams[1].strip()

                    # Cellule 1: Type de pronostic
                    tip_text = cells[1].get_text(strip=True)
                    tip_type = tip_text.lower().replace(" ", "_")

                    # Cellules 2+: Cotes (on prend la premiere cote disponible)
                    odds = None
                    for cell in cells[2:]:
                        try:
                            odds_text = cell.get_text(strip=True)
                            odds = float(odds_text.replace(',', '.'))
                            break
                        except:
                            continue

                    # Si dateTime est null, essayer d'extraire depuis tipTitle
                    if not date_time and schedina_title:
                        # Extraire la date depuis le titre si disponible
                        title_date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', schedina_title, re.IGNORECASE)
                        if title_date_match:
                            try:
                                day, month_name, year = title_date_match.groups()
                                month = month_map.get(month_name.lower(), 1)
                                # Date sans heure (00:00)
                                date_time = datetime(int(year), month, int(day)).isoformat()
                            except:
                                pass

                    pronostic = {
                        "id": generate_pronostic_id(
                            source="assopoker",
                            home_team=home_team,
                            away_team=away_team,
                            date_time=date_time,
                            tip_text=tip_text
                        ),
                        "source": "assopoker",
                        "match": f"{home_team} vs {away_team}" if home_team and away_team else match_name,
                        "dateTime": date_time,
                        "competition": None,
                        "sport": "Calcio",  # Par defaut Calcio pour les schedine
                        "homeTeam": home_team,
                        "awayTeam": away_team,
                        "tipTitle": schedina_title,
                        "tipType": tip_type,
                        "tipText": tip_text,
                        "reasonTip": None,
                        "odds": odds,
                        "confidence": None
                    }

                    pronostics.append(pronostic)

                except Exception as e:
                    if debug_mode:
                        print(f"[AssoPoker] Error parsing schedina row: {str(e)}")
                    continue

        except Exception as e:
            if debug_mode:
                print(f"[AssoPoker] Error parsing schedina block: {str(e)}")
            continue

    return pronostics


def _parse_pronostici_page(html: str, debug_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Parse la page pronostici-oggi pour extraire les pronostics
    Utilise UNIQUEMENT les blocs block-daily-tip

    Args:
        html: Contenu HTML de la page
        debug_mode: Active les logs detailles

    Returns:
        Liste des pronostics extraits
    """
    pronostics = []
    soup = BeautifulSoup(html, 'html.parser')

    # Mapping des mois (support français et italien)
    month_map_short = {
        'jan': 1, 'fév': 2, 'mar': 3, 'avr': 4, 'mai': 5, 'juin': 6,
        'juil': 7, 'août': 8, 'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12,
        'gen': 1, 'feb': 2, 'apr': 4, 'mag': 5, 'giu': 6,
        'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'dic': 12
    }

    month_map_long = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
    }

    # Chercher les blocs block-daily-tip UNIQUEMENT
    daily_tip_blocks = soup.find_all(class_='block-daily-tip')

    if debug_mode:
        print(f"[AssoPoker] Found {len(daily_tip_blocks)} block-daily-tip blocks")

    for block in daily_tip_blocks:
        try:
            # Trouver tous les tips dans ce bloc
            tip_wrappers = block.find_all(class_='tip--wrapper')

            if debug_mode:
                print(f"[AssoPoker] Found {len(tip_wrappers)} tips in block-daily-tip")

            for tip_wrapper in tip_wrappers:
                try:
                    # Sport et competition depuis l'icone
                    sport = None
                    competition = None
                    sport_icon = tip_wrapper.find(class_='sport-icon')
                    if sport_icon:
                        img = sport_icon.find('img')
                        if img:
                            sport = img.get('alt', '').strip()
                        # La competition est le texte apres l'image
                        competition_text = sport_icon.get_text(strip=True)
                        if sport:
                            competition = competition_text.replace(sport, '').strip()
                        else:
                            competition = competition_text

                    # Date et heure (support plusieurs formats après traduction Chrome)
                    date_time = None
                    time_elem = tip_wrapper.find('time')
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)

                        # Format 1: "Ven. 26 déc. 2025 - 19h30" (format Chrome traduit)
                        date_match = re.search(r'(\d{1,2})\s+(\w+)\.?\s+(\d{4})\s*-\s*(\d{1,2})h(\d{2})', time_text, re.IGNORECASE)
                        if date_match:
                            try:
                                day, month_name, year, hour, minute = date_match.groups()
                                # Enlever le point final si présent
                                month_name = month_name.rstrip('.')
                                month = month_map_short.get(month_name.lower(), 1)
                                date_time = datetime(int(year), month, int(day), int(hour), int(minute)).isoformat()
                            except Exception as e:
                                if debug_mode:
                                    print(f"[AssoPoker] Error parsing date format 1: {e}")

                        # Format 2: "ven 26 dic 2025 - ore 19:30" ou "ven 26 déc 2025 - heure 19:30"
                        if not date_time:
                            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})\s*-\s*(?:ore|heure[s]?)\s+(\d{1,2}):(\d{2})', time_text, re.IGNORECASE)
                            if date_match:
                                try:
                                    day, month_name, year, hour, minute = date_match.groups()
                                    month = month_map_short.get(month_name.lower(), 1)
                                    date_time = datetime(int(year), month, int(day), int(hour), int(minute)).isoformat()
                                except Exception as e:
                                    if debug_mode:
                                        print(f"[AssoPoker] Error parsing date format 2: {e}")

                    # Match
                    match_name = None
                    home_team = None
                    away_team = None
                    tip_title_elem = tip_wrapper.find(class_='tip-title')
                    if tip_title_elem:
                        match_name = tip_title_elem.get_text(strip=True)
                        # Extraire les equipes (format: "Monaco - Real Madrid")
                        teams = match_name.split(' - ')
                        if len(teams) == 2:
                            home_team = teams[0].strip()
                            away_team = teams[1].strip()

                    # Description/Raison
                    reason_tip = None
                    descrizione = tip_wrapper.find(class_='descrizione')
                    if descrizione:
                        # Extraire le texte des paragraphes
                        paragraphs = descrizione.find_all('p')
                        if paragraphs:
                            reason_tip = ' '.join([p.get_text(strip=True) for p in paragraphs])
                        else:
                            reason_tip = descrizione.get_text(strip=True)

                    # Mercato et Esito (type de pari)
                    tip_text = None
                    mercato_elem = tip_wrapper.find(class_='mercato')
                    esito_elem = tip_wrapper.find(class_='esito')

                    if mercato_elem and esito_elem:
                        mercato = mercato_elem.get_text(strip=True)
                        esito = esito_elem.get_text(strip=True)
                        tip_text = f"{mercato}: {esito}"
                    elif mercato_elem:
                        tip_text = mercato_elem.get_text(strip=True)

                    # Cotes (si disponibles)
                    odds = None
                    quota_elem = tip_wrapper.find(class_=lambda x: x and 'quota' in str(x).lower() if x else False)
                    if quota_elem:
                        try:
                            odds_text = quota_elem.get_text(strip=True)
                            odds = float(odds_text.replace(',', '.'))
                        except:
                            pass

                    pronostic = {
                        "id": generate_pronostic_id(
                            source="assopoker",
                            home_team=home_team,
                            away_team=away_team,
                            date_time=date_time,
                            tip_text=tip_text
                        ),
                        "source": "assopoker",
                        "match": match_name,
                        "dateTime": date_time,
                        "competition": competition,
                        "sport": sport,
                        "homeTeam": home_team,
                        "awayTeam": away_team,
                        "tipTitle": match_name,
                        "tipType": tip_text.lower().replace(" ", "_").replace(":", "_") if tip_text else None,
                        "tipText": tip_text,
                        "reasonTip": reason_tip,
                        "odds": odds,
                        "confidence": None
                    }

                    pronostics.append(pronostic)

                except Exception as e:
                    if debug_mode:
                        print(f"[AssoPoker] Error parsing tip wrapper: {str(e)}")
                    continue

        except Exception as e:
            if debug_mode:
                print(f"[AssoPoker] Error parsing block-daily-tip: {str(e)}")
            continue

    return pronostics
