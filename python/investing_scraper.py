"""
Scraper spécialisé pour investing.com - Calendrier économique
Utilise Crawl4AI pour interagir avec le formulaire et extraire les événements économiques
"""
import asyncio
import json
import re
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
    time_filter: str = "timeRemain"
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
        time_filter: Filtre temporel ("timeRemain" = événements restants)
    
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
            
            # Extraire les données depuis le JavaScript
            try:
                html_content = api_result.html or api_result.cleaned_html or ""
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Chercher les données JSON stockées dans l'attribut data
                body = soup.find('body')
                if body and body.get('data-calendar-json'):
                    try:
                        json_data = json.loads(body.get('data-calendar-json'))
                        events = parse_json_response(json_data)
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


def parse_json_response(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse la réponse JSON de l'API investing.com
    
    Args:
        json_data: Dictionnaire JSON de la réponse API
    
    Returns:
        Liste des événements économiques formatés
    """
    events = []
    
    try:
        # La structure de la réponse peut varier
        # Chercher les données dans différentes structures possibles
        if 'data' in json_data:
            data = json_data['data']
            
            # Si data est une string HTML
            if isinstance(data, str):
                soup = BeautifulSoup(data, 'html.parser')
                events = parse_html_table(soup)
            # Si data est une liste d'événements
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        events.append(format_event(item))
            # Si data est un dict avec une liste d'événements
            elif isinstance(data, dict):
                if 'events' in data:
                    for item in data['events']:
                        events.append(format_event(item))
                elif 'rows' in data:
                    for item in data['rows']:
                        events.append(format_event(item))
        
        # Chercher directement des événements dans la racine
        if not events and 'events' in json_data:
            for item in json_data['events']:
                events.append(format_event(item))
        
    except Exception as e:
        print(f"Erreur lors du parsing JSON: {e}")
        events = []
    
    return events


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
            if 'data' in data and isinstance(data['data'], str):
                # Les données peuvent être dans une propriété 'data' en HTML
                html_data = data['data']
                soup = BeautifulSoup(html_data, 'html.parser')
                events = parse_html_table(soup)
            elif 'data' in data and isinstance(data['data'], list):
                events = [format_event(event) for event in data['data']]
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
    Parse la table HTML du calendrier économique
    
    Args:
        soup: BeautifulSoup object du HTML
    
    Returns:
        Liste des événements économiques
    """
    events = []
    
    try:
        # Chercher la table du calendrier économique
        # La structure peut varier, on cherche plusieurs sélecteurs possibles
        table = soup.find('table', {'id': 'economicCalendarData'}) or \
                soup.find('table', class_=re.compile(r'calendar|economic', re.I)) or \
                soup.find('tbody', {'id': 'economicCalendarData'})
        
        if not table:
            # Chercher toutes les lignes de données
            rows = soup.find_all('tr', class_=re.compile(r'js-event-item|event', re.I))
        else:
            rows = table.find_all('tr', class_=re.compile(r'js-event-item|event', re.I))
        
        for row in rows:
            try:
                event = parse_event_row(row)
                if event:
                    events.append(event)
            except Exception as e:
                # Continuer avec la ligne suivante en cas d'erreur
                continue
                
    except Exception as e:
        print(f"Erreur lors du parsing de la table: {e}")
    
    return events


def parse_event_row(row) -> Optional[Dict[str, Any]]:
    """
    Parse une ligne d'événement économique
    
    Args:
        row: BeautifulSoup element d'une ligne <tr>
    
    Returns:
        Dictionnaire représentant l'événement ou None
    """
    try:
        cells = row.find_all(['td', 'th'])
        if len(cells) < 5:
            return None
        
        # Structure typique: time, country, event, actual, forecast, previous, impact
        event_data = {
            "time": extract_text(cells[0]) if len(cells) > 0 else "",
            "country": extract_text(cells[1]) if len(cells) > 1 else "",
            "event": extract_text(cells[2]) if len(cells) > 2 else "",
            "actual": extract_text(cells[3]) if len(cells) > 3 else "",
            "forecast": extract_text(cells[4]) if len(cells) > 4 else "",
            "previous": extract_text(cells[5]) if len(cells) > 5 else "",
            "impact": extract_impact(row)
        }
        
        return format_event(event_data)
        
    except Exception as e:
        return None


def extract_text(element) -> str:
    """Extrait le texte d'un élément HTML en nettoyant les espaces"""
    if element:
        text = element.get_text(strip=True)
        return text
    return ""


def extract_impact(row) -> str:
    """Extrait le niveau d'impact depuis les classes CSS ou icônes"""
    try:
        # Chercher les classes d'impact (bull, bear, etc.)
        impact_classes = row.get('class', [])
        for cls in impact_classes:
            if 'bull' in cls.lower() or 'high' in cls.lower():
                return "High"
            elif 'bear' in cls.lower() or 'low' in cls.lower():
                return "Low"
            elif 'medium' in cls.lower():
                return "Medium"
        
        # Chercher les icônes d'impact
        impact_icons = row.find_all(['i', 'span'], class_=re.compile(r'bull|bear|impact', re.I))
        if impact_icons:
            icon_class = impact_icons[0].get('class', [])
            if any('bull' in c.lower() or 'high' in c.lower() for c in icon_class):
                return "High"
            elif any('bear' in c.lower() or 'low' in c.lower() for c in icon_class):
                return "Low"
        
        return "Medium"
    except:
        return "Medium"


def format_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formate un événement économique en dictionnaire structuré
    
    Args:
        event_data: Dictionnaire brut des données d'événement
    
    Returns:
        Dictionnaire formaté avec tous les champs standardisés
    """
    return {
        "time": event_data.get("time", ""),
        "country": event_data.get("country", ""),
        "event": event_data.get("event", ""),
        "actual": event_data.get("actual", ""),
        "forecast": event_data.get("forecast", ""),
        "previous": event_data.get("previous", ""),
        "impact": event_data.get("impact", "Medium")
    }

