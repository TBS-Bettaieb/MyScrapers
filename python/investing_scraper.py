"""
Scraper spécialisé pour investing.com - Calendrier économique
Utilise Crawl4AI avec JsonCssExtractionStrategy pour extraire les événements économiques
"""
import asyncio
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
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
# FONCTIONS DE POST-TRAITEMENT
# =============================================================================

def process_extracted_events(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-traitement des événements extraits par JsonCssExtractionStrategy
    
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
    Extrait les événements du HTML en utilisant JsonCssExtractionStrategy
    
    Args:
        html_content: Contenu HTML à parser
    
    Returns:
        Liste des événements extraits et traités
    """
    try:
        strategy = JsonCssExtractionStrategy(ECONOMIC_EVENT_SCHEMA)
        # Signature: extract(url, html_content)
        extracted_data = strategy.extract("", html_content)
        
        if extracted_data:
            # extract() peut retourner une liste ou une string JSON
            if isinstance(extracted_data, str):
                raw_events = json.loads(extracted_data)
            else:
                raw_events = extracted_data
            
            if isinstance(raw_events, list):
                return process_extracted_events(raw_events)
        
        return []
    except Exception as e:
        print(f"Erreur lors de l'extraction avec JsonCssExtractionStrategy: {e}")
        return []


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
        print(f"Erreur lors de l'extraction des jours fériés: {e}")
    
    return holidays


async def scrape_economic_calendar(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    countries: Optional[List[int]] = None,
    categories: Optional[List[str]] = None,
    importance: Optional[List[int]] = None,
    timezone: int = 58,
    time_filter: str = "timeOnly"
) -> Dict[str, Any]:
    """
    Scrape le calendrier économique d'investing.com
    
    Args:
        date_from: Date de début au format YYYY-MM-DD (défaut: aujourd'hui)
        date_to: Date de fin au format YYYY-MM-DD (défaut: dans 30 jours)
        countries: Liste des IDs de pays à filtrer (None = tous)
        categories: Liste des catégories à filtrer (None = toutes)
        importance: Liste des niveaux d'importance [1,2,3] (None = tous)
        timezone: ID du fuseau horaire (58 = GMT+1)
        time_filter: Filtre temporel ("timeOnly" = événements avec heure uniquement)
    
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
    
    # Préparer les filtres par défaut (basés sur le curl fourni)
    if countries is None:
        # Liste complète des pays du curl
        countries = [95, 86, 29, 25, 54, 114, 145, 47, 34, 8, 174, 163, 32, 70, 6, 232, 27, 37, 122, 15, 78, 113, 107, 55, 24, 121, 59, 89, 72, 71, 22, 17, 74, 51, 39, 93, 106, 14, 48, 66, 33, 23, 10, 119, 35, 92, 102, 57, 94, 204, 97, 68, 96, 103, 111, 42, 109, 188, 7, 139, 247, 105, 82, 172, 21, 43, 20, 60, 87, 44, 193, 148, 125, 45, 53, 38, 170, 100, 56, 80, 52, 238, 36, 90, 112, 110, 11, 26, 162, 9, 12, 46, 85, 41, 202, 63, 123, 61, 143, 4, 5, 180, 168, 138, 178, 84, 75]
    
    if categories is None:
        categories = ["_employment", "_economicActivity", "_inflation", "_credit", "_centralBanks", "_confidenceIndex", "_balance", "_Bonds"]
    
    if importance is None:
        importance = [1, 2, 3]
    
    try:
        # Construire le script JavaScript pour appeler l'API
        js_code = f"""
        (async function() {{
            const formData = new URLSearchParams();
            
            // Ajouter les pays
            const countries = {json.dumps(countries)};
            countries.forEach(country => {{
                formData.append('country[]', country);
            }});
            
            // Ajouter les catégories
            const categories = {json.dumps(categories)};
            categories.forEach(category => {{
                formData.append('category[]', category);
            }});
            
            // Ajouter les niveaux d'importance
            const importance = {json.dumps(importance)};
            importance.forEach(imp => {{
                formData.append('importance[]', imp);
            }});
            
            // Ajouter les dates et autres paramètres
            formData.append('dateFrom', '{date_from}');
            formData.append('dateTo', '{date_to}');
            formData.append('timeZone', '{timezone}');
            formData.append('timeFilter', '{time_filter}');
            formData.append('currentTab', 'custom');
            formData.append('limit_from', '0');
            
            try {{
                const response = await fetch('https://www.investing.com/economic-calendar/Service/getCalendarFilteredData', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    }},
                    body: formData.toString()
                }});
                
                const data = await response.json();
                window.__investing_calendar_data = data;
                return data;
            }} catch (error) {{
                window.__investing_calendar_error = error.message;
                return {{ error: error.message }};
            }}
        }})();
        """
        
        async with AsyncWebCrawler(
            headless=True,
            verbose=False,
            browser_type="chromium"
        ) as crawler:
            # D'abord charger la page principale pour obtenir les cookies
            base_result = await crawler.arun(
                url="https://www.investing.com/economic-calendar/",
                wait_for="body"
            )
            
            if not base_result.success:
                error_msg = base_result.error_message or "Erreur inconnue lors du chargement"
                # Vérifier si c'est un problème de blocage
                if "blocked" in error_msg.lower() or "403" in error_msg or "forbidden" in error_msg.lower():
                    error_msg = "Accès bloqué par investing.com. Vérifiez les headers et cookies."
                return {
                    "success": False,
                    "events": [],
                    "date_range": {"from": date_from, "to": date_to},
                    "total_events": 0,
                    "error_message": f"Erreur lors du chargement de la page: {error_msg}"
                }
            
            # Exécuter le script JavaScript pour appeler l'API et stocker le résultat
            js_code_with_return = js_code + """
            // Attendre un peu pour que la requête se termine
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Retourner les données ou une indication d'erreur
            if (window.__investing_calendar_data) {
                // Créer un élément script pour stocker le JSON (pas de limite de taille)
                const scriptElement = document.createElement('script');
                scriptElement.id = 'investing-calendar-data';
                scriptElement.type = 'application/json';
                scriptElement.textContent = JSON.stringify(window.__investing_calendar_data);
                document.body.appendChild(scriptElement);
                
                // Marquer comme chargé
                document.body.setAttribute('data-calendar-loaded', 'true');
            } else if (window.__investing_calendar_error) {
                document.body.setAttribute('data-calendar-error', window.__investing_calendar_error);
            }
            """
            
            api_result = await crawler.arun(
                url="https://www.investing.com/economic-calendar/",
                js_code=js_code_with_return,
                wait_for="body[data-calendar-loaded]",
                page_timeout=60000,
                delay_before_return_html=2.0
            )
            
            if not api_result.success:
                return {
                    "success": False,
                    "events": [],
                    "date_range": {"from": date_from, "to": date_to},
                    "total_events": 0,
                    "error_message": f"Erreur lors de l'appel API: {api_result.error_message}"
                }
            
            # DEBUG: Sauvegarder le HTML pour analyse
            try:
                import tempfile
                debug_dir = tempfile.gettempdir()
                debug_file = os.path.join(debug_dir, 'investing_debug.html')
                html_content = api_result.html or api_result.cleaned_html or ""
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"DEBUG: HTML sauvegardé dans {debug_file}")
            except Exception as debug_error:
                print(f"DEBUG: Erreur lors de la sauvegarde du HTML: {debug_error}")
            
            # Extraire les données avec JsonCssExtractionStrategy
            try:
                html_content = api_result.html or api_result.cleaned_html or ""
                
                # Extraire le JSON depuis l'élément script (minimal BeautifulSoup)
                soup = BeautifulSoup(html_content, 'html.parser')
                body = soup.find('body')
                script_element = soup.find('script', {'id': 'investing-calendar-data', 'type': 'application/json'})
                
                if script_element and script_element.string:
                    try:
                        json_data = json.loads(script_element.string)
                        print("DEBUG: JSON récupéré depuis l'élément <script>")
                        print(f"DEBUG: Taille du JSON: {len(script_element.string)} caractères")
                        
                        # DEBUG: Sauvegarder le JSON pour analyse
                        try:
                            import tempfile
                            debug_dir = tempfile.gettempdir()
                            json_file = os.path.join(debug_dir, 'investing_debug.json')
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(json_data, f, indent=2, ensure_ascii=False)
                            print(f"DEBUG: JSON sauvegardé dans {json_file}")
                        except Exception as debug_error:
                            print(f"DEBUG: Erreur lors de la sauvegarde du JSON: {debug_error}")
                        
                        # Extraire le HTML depuis json_data['data']
                        if 'data' in json_data and isinstance(json_data['data'], str):
                            calendar_html = json_data['data']
                            
                            # Utiliser JsonCssExtractionStrategy pour extraire les événements
                            events = extract_events_with_strategy(calendar_html)
                            
                            # Si pas d'événements extraits, essayer le parsing des jours fériés
                            if not events:
                                print("DEBUG: Aucun événement extrait avec la stratégie, vérification des jours fériés")
                                events = _extract_holidays_fallback(calendar_html)
                            
                            print(f"DEBUG: {len(events)} événements extraits avec JsonCssExtractionStrategy")
                        else:
                            print("DEBUG: Pas de HTML dans json_data['data'], extraction directe")
                            events = extract_events_with_strategy(html_content)
                            
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: Erreur JSON decode: {e}")
                        events = extract_events_with_strategy(html_content)
                        
                elif body and body.get('data-calendar-error'):
                    return {
                        "success": False,
                        "events": [],
                        "date_range": {"from": date_from, "to": date_to},
                        "total_events": 0,
                        "error_message": f"Erreur JavaScript: {body.get('data-calendar-error')}"
                    }
                else:
                    # Fallback: extraction directe du HTML de la page
                    print("DEBUG: Aucune donnée JSON trouvée, extraction directe du HTML")
                    events = extract_events_with_strategy(html_content)
                
                return {
                    "success": True,
                    "events": events,
                    "date_range": {"from": date_from, "to": date_to},
                    "total_events": len(events),
                    "error_message": None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "events": [],
                    "date_range": {"from": date_from, "to": date_to},
                    "total_events": 0,
                    "error_message": f"Erreur lors du parsing: {str(e)}"
                }
                
    except asyncio.TimeoutError:
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "error_message": "Timeout: La requête a pris trop de temps (>60s)"
        }
    except ConnectionError as e:
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "error_message": f"Erreur de connexion: {str(e)}"
        }
    except Exception as e:
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
        print(f"Erreur parsing day header: {e}")
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
        print(f"Erreur parsing holiday: {e}")
    return None


def extract_text(element) -> str:
    """Extrait et nettoie le texte d'un élément HTML"""
    if element is None:
        return ""
    text = element.get_text(strip=True)
    # Remplacer les caractères non-breaking spaces
    return text.replace('\xa0', ' ')

