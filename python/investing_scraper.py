"""
Scraper spécialisé pour investing.com - Calendrier économique
Utilise httpx pour les requêtes API et Selenium uniquement pour initialiser les cookies
"""
import asyncio
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


# =============================================================================
# SCHEMA D'EXTRACTION POUR LES ÉVÉNEMENTS ÉCONOMIQUES
# =============================================================================

ECONOMIC_EVENT_SCHEMA = {
    "name": "EconomicEvents",
    "baseSelector": "tr[id^='eventRowId_']",
    "baseFields": [
        {"name": "event_id", "type": "attribute", "attribute": "id"},
        {"name": "datetime", "type": "attribute", "attribute": "data-event-datetime"}
    ],
    "fields": [
        {"name": "time", "selector": "td.time", "type": "text"},
        {"name": "country", "selector": "td.flagCur span[title]", "type": "attribute", "attribute": "title"},
        {"name": "country_code", "selector": "td.flagCur", "type": "text"},
        {"name": "event", "selector": "td.event a", "type": "text"},
        {"name": "event_url", "selector": "td.event a", "type": "attribute", "attribute": "href"},
        {"name": "actual", "selector": "td[id^='eventActual_']", "type": "text"},
        {"name": "forecast", "selector": "td[id^='eventForecast_']", "type": "text"},
        {"name": "previous", "selector": "td[id^='eventPrevious_']", "type": "text"},
        {"name": "impact_icons", "selector": "td.sentiment i.grayFullBullishIcon", "type": "list", "fields": []}
    ]
}

# Schema pour les en-têtes de jour
DAY_HEADER_SCHEMA = {
    "name": "DayHeaders",
    "baseSelector": "tr:has(td.theDay)",
    "fields": [
        {"name": "day", "selector": "td.theDay", "type": "text"}
    ]
}


# =============================================================================
# CACHE DES COOKIES EN MÉMOIRE
# =============================================================================

_cookies_cache: Optional[Dict[str, Any]] = None
_cookies_cache_timestamp: Optional[datetime] = None
COOKIES_CACHE_DURATION = timedelta(hours=1)


# =============================================================================
# INITIALISATION DES COOKIES AVEC SELENIUM
# =============================================================================

def get_cookies_with_selenium() -> Dict[str, str]:
    """
    Ouvre investing.com avec Selenium et récupère tous les cookies
    
    Returns:
        Dictionnaire des cookies au format {name: value}
    """
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://www.investing.com/economic-calendar/')
        
        # Attendre que la page se charge et que les cookies soient générés
        driver.implicitly_wait(5)
        time.sleep(3)  # Attendre quelques secondes supplémentaires pour les cookies dynamiques
        
        # Récupérer tous les cookies
        selenium_cookies = driver.get_cookies()
        
        # Convertir en dictionnaire simple {name: value}
        cookies_dict = {}
        for cookie in selenium_cookies:
            cookies_dict[cookie['name']] = cookie['value']
        
        return cookies_dict
        
    except Exception as e:
        import traceback
        print(f"❌ Erreur lors de la récupération des cookies avec Selenium: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        return {}
    finally:
        if driver:
            driver.quit()


def get_cookies(cache: bool = True) -> Dict[str, str]:
    """
    Récupère les cookies, en utilisant le cache si disponible et valide
    
    Args:
        cache: Si True, utilise le cache si disponible et non expiré
    
    Returns:
        Dictionnaire des cookies au format {name: value}
    """
    global _cookies_cache, _cookies_cache_timestamp
    
    # Vérifier si le cache est valide
    if cache and _cookies_cache is not None and _cookies_cache_timestamp is not None:
        elapsed = datetime.now() - _cookies_cache_timestamp
        if elapsed < COOKIES_CACHE_DURATION:
            print("✅ Utilisation des cookies en cache")
            return _cookies_cache
    
    # Récupérer de nouveaux cookies
    print("🔐 Récupération des cookies avec Selenium...")
    cookies = get_cookies_with_selenium()
    
    # Mettre en cache
    if cache:
        _cookies_cache = cookies
        _cookies_cache_timestamp = datetime.now()
    
    return cookies


# =============================================================================
# REQUÊTE API AVEC HTTPX
# =============================================================================

async def make_api_request(
    cookies: Dict[str, str],
    date_from: str,
    date_to: str,
    countries: Optional[List[int]] = None,
    categories: Optional[List[str]] = None,
    importance: Optional[List[int]] = None,
    timezone: int = 58,
    time_filter: str = "timeOnly",
    debug_mode: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Fait une requête POST vers l'API investing.com pour récupérer les événements économiques
    
    Args:
        cookies: Dictionnaire des cookies
        date_from: Date de début au format YYYY-MM-DD
        date_to: Date de fin au format YYYY-MM-DD
        countries: Liste des IDs de pays (None = tous)
        categories: Liste des catégories (None = toutes)
        importance: Liste des niveaux d'importance [1,2,3] (None = tous)
        timezone: ID du fuseau horaire (58 = GMT+1)
        time_filter: Filtre temporel ("timeRemain" ou "timeOnly")
    
    Returns:
        Réponse JSON de l'API ou None en cas d'erreur
    """
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
    
    # Liste complète des pays par défaut (tous les pays)
    default_countries = [
        95, 86, 29, 25, 54, 114, 145, 47, 34, 8, 174, 163, 32, 70, 6, 232, 27, 37, 122, 15,
        78, 113, 107, 55, 24, 121, 59, 89, 72, 71, 22, 17, 74, 51, 39, 93, 106, 14, 48, 66,
        33, 23, 10, 119, 35, 92, 102, 57, 94, 204, 97, 68, 96, 103, 111, 42, 109, 188, 7, 139,
        247, 105, 82, 172, 21, 43, 20, 60, 87, 44, 193, 148, 125, 45, 53, 38, 170, 100, 56, 80,
        52, 238, 36, 90, 112, 110, 11, 26, 162, 9, 12, 46, 85, 41, 202, 63, 123, 61, 143, 4, 5,
        180, 168, 138, 178, 84, 75
    ]
    
    # Liste complète des catégories par défaut
    default_categories = [
        "_employment", "_economicActivity", "_inflation", "_credit",
        "_centralBanks", "_confidenceIndex", "_balance", "_Bonds"
    ]
    
    # Préparer les paramètres POST
    params = []
    
    # Countries
    country_list = countries if countries is not None else default_countries
    for country_id in country_list:
        params.append(("country[]", str(country_id)))
    
    # Categories
    category_list = categories if categories is not None else default_categories
    for category in category_list:
        params.append(("category[]", category))
    
    # Importance
    importance_list = importance if importance is not None else [1, 2, 3]
    for imp in importance_list:
        params.append(("importance[]", str(imp)))
    
    # Autres paramètres
    params.extend([
        ("dateFrom", date_from),
        ("dateTo", date_to),
        ("timeZone", str(timezone)),
        ("timeFilter", time_filter),
        ("currentTab", "custom"),
        ("limit_from", "0")
    ])
    
    # Headers
    headers = {
        "accept": "*/*",
        "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.investing.com",
        "referer": "https://www.investing.com/economic-calendar/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    try:
        # Créer une copie des headers pour éviter toute modification
        request_headers = dict(headers)

        # Construire le header Cookie manuellement (sans encodage, les cookies sont déjà des strings)
        cookie_parts = []
        for name, value in cookies.items():
            # Convertir en string et garder tel quel (les cookies de Selenium sont déjà des strings)
            cookie_parts.append(f"{name}={str(value)}")

        if cookie_parts:
            request_headers["Cookie"] = "; ".join(cookie_parts)
            if debug_mode:
                print(f"🍪 Cookies ajoutés: {len(cookie_parts)} cookies")

        # Créer un timeout explicite
        timeout = httpx.Timeout(120.0, connect=30.0)

        # Convertir params en dict pour httpx
        # httpx avec AsyncClient a besoin d'un dict ou de bytes, pas d'une liste de tuples
        from urllib.parse import urlencode
        encoded_data = urlencode(params)

        # Utiliser httpx.AsyncClient avec transport asynchrone explicite
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # Faire la requête POST avec content au lieu de data
            response = await client.post(
                url,
                content=encoded_data,
                headers=request_headers
            )
            response.raise_for_status()

            # Parser la réponse JSON (pas besoin d'await pour httpx)
            return response.json()
            
    except httpx.TimeoutException as e:
        print(f"❌ Timeout lors de la requête API: {e}")
        print(f"   URL: {url}")
        print(f"   Timeout: 120 secondes")
        return None
    except httpx.HTTPStatusError as e:
        print(f"❌ Erreur HTTP lors de la requête API: {e.response.status_code}")
        print(f"   URL: {url}")
        print(f"   Raison: {e.response.reason_phrase}")
        try:
            error_body = e.response.text[:500]  # Premiers 500 caractères
            print(f"   Réponse: {error_body}")
        except:
            pass
        return None
    except httpx.RequestError as e:
        print(f"❌ Erreur de requête API: {type(e).__name__}")
        print(f"   URL: {url}")
        print(f"   Détails: {str(e)}")
        if hasattr(e, 'request'):
            print(f"   Méthode: {e.request.method if hasattr(e.request, 'method') else 'N/A'}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de décodage JSON: {e}")
        print(f"   Position: ligne {e.lineno}, colonne {e.colno}")
        print(f"   Message: {e.msg}")
        return None
    except Exception as e:
        import traceback
        print(f"❌ Erreur inattendue lors de la requête API: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        return None


# =============================================================================
# FONCTIONS DE POST-TRAITEMENT
# =============================================================================

def process_extracted_events(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-traitement des événements extraits
    
    Args:
        raw_events: Liste des événements bruts extraits
    
    Returns:
        Liste des événements formatés et nettoyés
    """
    events = []
    
    for raw in raw_events:
        # Calculer impact depuis le nombre d'icônes
        impact_icons = raw.get("impact_icons", [])
        impact_count = len(impact_icons) if isinstance(impact_icons, list) else 0
        
        if impact_count >= 3:
            impact = "High"
        elif impact_count == 2:
            impact = "Medium"
        elif impact_count == 1:
            impact = "Low"
        else:
            impact = "Medium"  # Valeur par défaut
        
        # Convertir datetime en ISO 8601
        raw_datetime = raw.get("datetime", "")
        parsed_datetime = ""
        day = ""
        
        if raw_datetime:
            try:
                dt = datetime.strptime(raw_datetime, '%Y/%m/%d %H:%M:%S')
                parsed_datetime = dt.isoformat()
                day = dt.strftime('%A, %B %d, %Y')
            except (ValueError, TypeError):
                pass
        
        # Extraire code pays (3 lettres) depuis le texte
        country_code = ""
        country_code_text = raw.get("country_code", "") or ""
        currency_match = re.search(r'\b([A-Z]{3})\b', country_code_text)
        if currency_match:
            country_code = currency_match.group(1)
        
        # Extraire et nettoyer l'event_id
        event_id = raw.get("event_id", "") or ""
        if event_id.startswith("eventRowId_"):
            event_id = event_id.replace("eventRowId_", "")
        
        # Ne pas ajouter les événements sans nom
        event_name = (raw.get("event", "") or "").strip().replace('\xa0', ' ')
        if not event_name:
            continue
        
        events.append({
            "time": (raw.get("time", "") or "").strip().replace('\xa0', ' '),
            "datetime": raw_datetime,
            "parsed_datetime": parsed_datetime,
            "day": day,
            "country": (raw.get("country", "") or "").strip(),
            "country_code": country_code,
            "event": event_name,
            "event_url": (raw.get("event_url", "") or "").strip(),
            "actual": (raw.get("actual", "") or "").strip().replace('\xa0', ' '),
            "forecast": (raw.get("forecast", "") or "").strip().replace('\xa0', ' '),
            "previous": (raw.get("previous", "") or "").strip().replace('\xa0', ' '),
            "impact": impact,
            "event_id": event_id
        })
    
    return events


def extract_events_with_strategy(html_content: str) -> List[Dict[str, Any]]:
    """
    Extrait les événements du HTML en utilisant BeautifulSoup et le schéma d'extraction
    
    Args:
        html_content: Contenu HTML à parser
    
    Returns:
        Liste des événements extraits et traités
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        raw_events = []
        
        # Trouver tous les événements avec le sélecteur de base
        event_rows = soup.select(ECONOMIC_EVENT_SCHEMA["baseSelector"])
        
        for row in event_rows:
            event_data = {}
            
            # Extraire les baseFields (attributs)
            for field in ECONOMIC_EVENT_SCHEMA["baseFields"]:
                attr_name = field["attribute"]
                if attr_name in row.attrs:
                    event_data[field["name"]] = row.attrs[attr_name]
            
            # Extraire les champs normaux
            for field in ECONOMIC_EVENT_SCHEMA["fields"]:
                selector = field.get("selector")
                if not selector:
                    continue
                
                elements = row.select(selector)
                
                if field["type"] == "list":
                    # Pour les listes (comme impact_icons)
                    event_data[field["name"]] = elements
                elif field["type"] == "attribute":
                    # Pour les attributs
                    attr_name = field.get("attribute")
                    if elements and attr_name:
                        event_data[field["name"]] = elements[0].get(attr_name, "")
                    else:
                        event_data[field["name"]] = ""
                else:
                    # Pour le texte
                    if elements:
                        text = elements[0].get_text(strip=True)
                        event_data[field["name"]] = text
                    else:
                        event_data[field["name"]] = ""
            
            raw_events.append(event_data)
        
        return process_extracted_events(raw_events)
        
    except Exception as e:
        import traceback
        print(f"❌ Erreur lors de l'extraction avec BeautifulSoup: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"   Taille HTML: {len(html_content)} caractères")
        print(f"   Traceback:")
        traceback.print_exc()
        return []


# =============================================================================
# FONCTION PRINCIPALE DE SCRAPING
# =============================================================================

async def scrape_economic_calendar(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    countries: Optional[List[int]] = None,
    categories: Optional[List[str]] = None,
    importance: Optional[List[int]] = None,
    timezone: int = 58,
    time_filter: str = "timeOnly",
    debug_mode: bool = True,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Scrape le calendrier économique d'investing.com via l'API
    
    Args:
        date_from: Date de début au format YYYY-MM-DD (défaut: aujourd'hui)
        date_to: Date de fin au format YYYY-MM-DD (défaut: dans 30 jours)
        countries: Liste des IDs de pays à filtrer (None = tous)
        categories: Liste des catégories à filtrer (None = toutes)
        importance: Liste des niveaux d'importance [1,2,3] (None = tous)
        timezone: ID du fuseau horaire (58 = GMT+1)
        time_filter: Filtre temporel (défaut: "timeOnly")
        debug_mode: Active les logs détaillés
        use_cache: Utilise le cache des cookies si disponible
    
    Returns:
        Dictionnaire contenant:
        - success: bool
        - events: Liste des événements économiques
        - date_range: {"from": str, "to": str}
        - total_events: int
        - error_message: Optional[str]
    """
    # Définir les dates par défaut
    if date_from is None:
        date_from = datetime.now().strftime("%Y-%m-%d")
    if date_to is None:
        date_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    if importance is None:
        importance = [1, 2, 3]
    
    try:
        print("\n" + "="*70)
        print("🚀 DÉMARRAGE DU SCRAPING")
        print("="*70)
        print(f"📅 Période: {date_from} → {date_to}")
        print(f"🌍 Timezone: {timezone}")
        print(f"⚙️  Mode debug: {debug_mode}")
        print("="*70 + "\n")
        
        # 1. Récupérer les cookies
        cookies = get_cookies(cache=use_cache)
        if not cookies:
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "error_message": "Impossible de récupérer les cookies"
            }
        
        # 2. Faire la requête API
        print("📡 Envoi de la requête API...")
        api_response = await make_api_request(
            cookies=cookies,
            date_from=date_from,
            date_to=date_to,
            countries=countries,
            categories=categories,
            importance=importance,
            timezone=timezone,
            time_filter=time_filter,
            debug_mode=debug_mode
        )
        
        if not api_response:
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "error_message": "Erreur lors de la requête API"
            }
        
        # 3. Extraire le HTML de la réponse
        html_content = api_response.get("data", "")
        if not html_content:
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "error_message": "Aucune donnée dans la réponse API"
            }
        
        print(f"📄 HTML récupéré: {len(html_content)} caractères")
        
        # 4. Parser le HTML pour extraire les événements
        events = extract_events_with_strategy(html_content)
        
        if not events:
            print("⚠️  Aucun événement trouvé, tentative extraction jours fériés...")
            events = _extract_holidays_fallback(html_content)
            print(f"✅ Jours fériés extraits: {len(events)}")
        
        print("\n" + "="*70)
        print(f"✅ SCRAPING TERMINÉ - {len(events)} événements extraits")
        print("="*70 + "\n")
        
        return {
            "success": True,
            "events": events,
            "date_range": {"from": date_from, "to": date_to},
            "total_events": len(events),
            "error_message": None
        }
                
    except asyncio.TimeoutError:
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "error_message": "Timeout: La requête a pris trop de temps"
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ Erreur détaillée:\n{error_detail}")
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "error_message": f"Erreur générale: {str(e)}"
        }


# =============================================================================
# FONCTIONS DE PARSING POUR CAS SPÉCIAUX (jours fériés, en-têtes)
# =============================================================================

def parse_day_header(row) -> Optional[str]:
    """
    Parse les lignes d'en-tête de jour
    
    Args:
        row: BeautifulSoup element <tr>
    
    Returns:
        String du jour (ex: "Tuesday, January 7, 2025") ou None
    """
    try:
        day_cell = row.find('td', class_='theDay')
        if day_cell:
            return extract_text(day_cell)
    except Exception as e:
        print(f"⚠️  Erreur parsing day header: {type(e).__name__} - {str(e)}")
    return None


def parse_holiday_row(row) -> Optional[Dict[str, Any]]:
    """
    Parse les lignes de jours fériés
    
    Args:
        row: BeautifulSoup element <tr>
    
    Returns:
        Dict avec les infos du jour férié ou None
    """
    try:
        cells = row.find_all('td')
        if len(cells) < 3:
            return None
        
        # Vérifier si c'est un jour férié
        holiday_span = cells[2].find('span', class_='bold')
        if not holiday_span or extract_text(holiday_span) != 'Holiday':
            return None
        
        # Extraire le pays
        country = ""
        country_cell = cells[1]
        if country_cell:
            flag_span = country_cell.find('span', title=True)
            if flag_span:
                country = flag_span.get('title', '')
        
        # Nom du jour férié
        holiday_name = extract_text(cells[3]) if len(cells) > 3 else ""
        
        return {
            "type": "holiday",
            "time": extract_text(cells[0]),
            "country": country,
            "event": holiday_name,
            "impact": "Holiday"
        }
        
    except Exception as e:
        print(f"⚠️  Erreur parsing holiday: {type(e).__name__} - {str(e)}")
    return None


def _extract_holidays_fallback(html_content: str) -> List[Dict[str, Any]]:
    """
    Extrait les jours fériés du HTML (fallback pour les cas où il n'y a que des jours fériés)
    
    Args:
        html_content: Contenu HTML à parser
    
    Returns:
        Liste des jours fériés formatés
    """
    holidays = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')
        current_day = None
        
        for row in rows:
            # Vérifier si c'est un en-tête de jour
            day_header = parse_day_header(row)
            if day_header:
                current_day = day_header
                continue
            
            # Vérifier si c'est un jour férié
            holiday = parse_holiday_row(row)
            if holiday:
                if current_day:
                    holiday['day'] = current_day
                holidays.append(holiday)
                
    except Exception as e:
        import traceback
        print(f"❌ Erreur lors de l'extraction des jours fériés: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        traceback.print_exc()
    
    return holidays


def extract_text(element) -> str:
    """Extrait et nettoie le texte d'un élément HTML"""
    if element is None:
        return ""
    text = element.get_text(strip=True)
    # Remplacer les caractères non-breaking spaces
    return text.replace('\xa0', ' ')
