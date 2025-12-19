"""
Scraper spécialisé pour investing.com - Calendrier économique
Utilise Crawl4AI pour interagir avec le formulaire et extraire les événements économiques
"""
import asyncio
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup


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
                document.body.setAttribute('data-calendar-loaded', 'true');
                document.body.setAttribute('data-calendar-json', JSON.stringify(window.__investing_calendar_data));
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
            
            # Extraire les données depuis le JavaScript
            try:
                html_content = api_result.html or api_result.cleaned_html or ""
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Chercher les données JSON stockées dans l'attribut data
                body = soup.find('body')
                if body and body.get('data-calendar-json'):
                    try:
                        json_data = json.loads(body.get('data-calendar-json'))
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
                        parse_result = parse_json_response(json_data)
                        if parse_result.get("success"):
                            events = parse_result.get("events", [])
                        else:
                            events = []
                    except json.JSONDecodeError:
                        events = parse_calendar_data(api_result)
                elif body and body.get('data-calendar-error'):
                    return {
                        "success": False,
                        "events": [],
                        "date_range": {"from": date_from, "to": date_to},
                        "total_events": 0,
                        "error_message": f"Erreur JavaScript: {body.get('data-calendar-error')}"
                    }
                else:
                    # Fallback: parser le HTML
                    events = parse_calendar_data(api_result)
                
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


def parse_json_response(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse la réponse complète de l'API investing.com
    
    Args:
        json_data: Réponse JSON de l'API contenant le HTML dans data['data']
    
    Returns:
        Dict avec events groupés par jour
    """
    events_by_day = {}
    current_day = None
    all_events = []
    
    try:
        # Le HTML est dans json_data['data']
        if 'data' not in json_data:
            return {
                "success": False,
                "error": "Pas de données dans la réponse",
                "events": [],
                "events_by_day": {},
                "total_events": 0,
                "days_count": 0
            }
        
        html_content = json_data['data']
        
        # Si data n'est pas une string HTML, essayer d'autres formats
        if not isinstance(html_content, str):
            # Fallback pour les autres formats
            if isinstance(html_content, list):
                for item in html_content:
                    if isinstance(item, dict):
                        formatted = format_event(item)
                        all_events.append(formatted)
            elif isinstance(html_content, dict):
                if 'events' in html_content:
                    for item in html_content['events']:
                        formatted = format_event(item)
                        all_events.append(formatted)
                elif 'rows' in html_content:
                    for item in html_content['rows']:
                        formatted = format_event(item)
                        all_events.append(formatted)
            
            return {
                "success": True,
                "total_events": len(all_events),
                "events": all_events,
                "events_by_day": {},
                "days_count": 0
            }
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Trouver toutes les lignes <tr>
        rows = soup.find_all('tr')
        
        for row in rows:
            # 1. Vérifier si c'est un en-tête de jour
            day_header = parse_day_header(row)
            if day_header:
                current_day = day_header
                if current_day not in events_by_day:
                    events_by_day[current_day] = []
                continue
            
            # 2. Vérifier si c'est un jour férié
            holiday = parse_holiday_row(row)
            if holiday:
                if current_day:
                    holiday['day'] = current_day
                    events_by_day[current_day].append(holiday)
                all_events.append(holiday)
                continue
            
            # 3. Vérifier si c'est un événement normal (id = eventRowId_*)
            event_id = row.get('id', '')
            if event_id.startswith('eventRowId_'):
                event = parse_event_row(row)
                if event:
                    # Ajouter le jour à l'événement
                    if current_day:
                        event['day'] = current_day
                        events_by_day[current_day].append(event)
                    all_events.append(event)
        
        return {
            "success": True,
            "total_events": len(all_events),
            "events": all_events,
            "events_by_day": events_by_day,
            "days_count": len(events_by_day)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "events": [],
            "events_by_day": {},
            "total_events": 0,
            "days_count": 0
        }


def parse_calendar_data(crawl_result) -> List[Dict[str, Any]]:
    """
    Parse les données du calendrier économique depuis le résultat de Crawl4AI
    
    Args:
        crawl_result: Résultat de crawler.arun()
    
    Returns:
        Liste des événements économiques formatés
    """
    events = []
    
    try:
        # Méthode 1: Essayer d'extraire le JSON depuis le JavaScript
        html_content = crawl_result.html or crawl_result.cleaned_html or ""
        
        # Chercher les données JSON dans le HTML
        json_match = re.search(r'window\.__investing_calendar_data\s*=\s*({.*?});', html_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            # Parser la structure JSON d'investing.com
            if 'data' in data:
                parse_result = parse_json_response(data)
                if parse_result.get("success"):
                    events = parse_result.get("events", [])
                else:
                    # Fallback: parser le HTML directement
                    soup = BeautifulSoup(html_content, 'html.parser')
                    events = parse_html_table(soup)
            else:
                events = parse_html_table(BeautifulSoup(html_content, 'html.parser'))
        else:
            # Méthode 2: Parser directement le HTML de la table
            soup = BeautifulSoup(html_content, 'html.parser')
            events = parse_html_table(soup)
            
    except Exception as e:
        # En cas d'erreur, retourner une liste vide
        print(f"Erreur lors du parsing: {e}")
        events = []
    
    return events


def parse_html_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Parse la table HTML du calendrier économique (fallback method)
    
    Args:
        soup: BeautifulSoup object du HTML
    
    Returns:
        Liste des événements économiques
    """
    events = []
    current_day = None
    
    try:
        # Trouver toutes les lignes <tr>
        rows = soup.find_all('tr')
        
        for row in rows:
            try:
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
                    events.append(holiday)
                    continue
                
                # Vérifier si c'est un événement normal (id = eventRowId_*)
                event_id = row.get('id', '')
                if event_id.startswith('eventRowId_'):
                    event = parse_event_row(row)
                    if event:
                        if current_day:
                            event['day'] = current_day
                        events.append(event)
            except Exception as e:
                # Continuer avec la ligne suivante en cas d'erreur
                continue
                
    except Exception as e:
        print(f"Erreur lors du parsing de la table: {e}")
    
    return events


def parse_event_row(row) -> Optional[Dict[str, Any]]:
    """
    Parse une ligne d'événement économique avec la structure investing.com
    
    Args:
        row: BeautifulSoup element d'une ligne <tr>
    
    Returns:
        Dictionnaire représentant l'événement ou None
    """
    try:
        # Extraire l'ID et le timestamp depuis les attributs
        event_id = row.get('id', '').replace('eventRowId_', '')
        event_datetime = row.get('data-event-datetime', '')
        
        # Sélecteurs CSS pour chaque colonne
        time_cell = row.find('td', class_='time')
        flag_cell = row.find('td', class_='flagCur')
        sentiment_cell = row.find('td', class_='sentiment')
        event_cell = row.find('td', class_='event')
        
        # Valeurs avec IDs spécifiques (eventActual_ID, eventForecast_ID, etc.)
        actual_cell = row.find('td', id=f'eventActual_{event_id}') if event_id else None
        forecast_cell = row.find('td', id=f'eventForecast_{event_id}') if event_id else None
        previous_cell = row.find('td', id=f'eventPrevious_{event_id}') if event_id else None
        
        # === EXTRACTION DU PAYS ===
        country = ""
        country_code = ""
        if flag_cell:
            # Le pays est dans l'attribut title du span
            flag_span = flag_cell.find('span', title=True)
            if flag_span:
                country = flag_span.get('title', '')
            # Le code devise (JPY, EUR, USD) est dans le texte
            text = flag_cell.get_text(strip=True)
            # Chercher un code de 3 lettres (devise)
            currency_match = re.search(r'\b([A-Z]{3})\b', text)
            if currency_match:
                country_code = currency_match.group(1)
        
        # === EXTRACTION DU NOM DE L'ÉVÉNEMENT ===
        event_name = ""
        event_url = ""
        if event_cell:
            # Le nom est dans le lien <a>
            event_link = event_cell.find('a')
            if event_link:
                event_name = extract_text(event_link)
                event_url = event_link.get('href', '')
        
        # === EXTRACTION DE L'IMPACT (BULLS) ===
        impact = "Medium"  # Par défaut
        if sentiment_cell:
            # Compter les icônes de bulls pleins
            bulls = sentiment_cell.find_all('i', class_='grayFullBullishIcon')
            num_bulls = len(bulls)
            
            if num_bulls >= 3:
                impact = "High"     # 🐂🐂🐂
            elif num_bulls == 2:
                impact = "Medium"   # 🐂🐂
            elif num_bulls == 1:
                impact = "Low"      # 🐂
        
        # === EXTRACTION DES VALEURS ===
        actual = extract_text(actual_cell) if actual_cell else ""
        forecast = extract_text(forecast_cell) if forecast_cell else ""
        previous = extract_text(previous_cell) if previous_cell else ""
        
        # === EXTRACTION DU TEMPS ===
        time_str = extract_text(time_cell) if time_cell else ""
        
        # === PARSER LA DATE EN ISO 8601 ===
        parsed_datetime = ""
        if event_datetime:
            try:
                parsed_dt = datetime.strptime(event_datetime, '%Y/%m/%d %H:%M:%S')
                parsed_datetime = parsed_dt.isoformat()  # "2025-01-07T04:35:00"
            except Exception as e:
                print(f"Erreur parsing datetime: {e}")
        
        # Ne retourner que si on a un nom d'événement
        if not event_name:
            return None
        
        # Retourner l'événement formaté
        return {
            "time": time_str,
            "datetime": event_datetime,  # Format: "2025/01/07 04:35:00"
            "parsed_datetime": parsed_datetime,  # Format ISO 8601: "2025-01-07T04:35:00"
            "country": country,
            "country_code": country_code,
            "event": event_name,
            "event_url": event_url,
            "actual": actual,
            "forecast": forecast,
            "previous": previous,
            "impact": impact,
            "event_id": event_id
        }
        
    except Exception as e:
        print(f"Erreur parsing event row: {e}")
        return None


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


def format_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formate un événement économique en dictionnaire structuré
    
    Args:
        event_data: Dictionnaire brut des données d'événement
    
    Returns:
        Dictionnaire formaté avec tous les champs standardisés
    """
    # Parser datetime en ISO si disponible et non déjà parsé
    parsed_datetime = event_data.get("parsed_datetime", "")
    if not parsed_datetime and event_data.get("datetime"):
        try:
            parsed_dt = datetime.strptime(event_data["datetime"], '%Y/%m/%d %H:%M:%S')
            parsed_datetime = parsed_dt.isoformat()
        except Exception:
            pass
    
    # Extraire day depuis datetime si absent
    day = event_data.get("day", "")
    if not day and event_data.get("datetime"):
        try:
            parsed_dt = datetime.strptime(event_data["datetime"], '%Y/%m/%d %H:%M:%S')
            day = parsed_dt.strftime('%A, %B %d, %Y')  # "Friday, December 20, 2024"
        except Exception:
            pass
    
    return {
        "time": event_data.get("time", ""),
        "datetime": event_data.get("datetime", ""),
        "parsed_datetime": parsed_datetime,
        "day": day,
        "country": event_data.get("country", ""),
        "country_code": event_data.get("country_code", ""),
        "event": event_data.get("event", ""),
        "event_url": event_data.get("event_url", ""),
        "actual": event_data.get("actual", ""),
        "forecast": event_data.get("forecast", ""),
        "previous": event_data.get("previous", ""),
        "impact": event_data.get("impact", "Medium"),
        "event_id": event_data.get("event_id", "")
    }

