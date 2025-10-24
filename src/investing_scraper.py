"""
Economic calendar scraper for Investing.com using API requests
"""

import time
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random
import json
import requests
from bs4 import BeautifulSoup

from csv_exporter import CSVExporter
from symbol_mapper import SymbolMapper

logger = logging.getLogger(__name__)


class InvestingComScraper:
    """Scraper for Investing.com economic calendar using API requests"""
    
    # Mapping des country IDs vers noms de pays (basé sur les IDs courants)
    COUNTRY_MAP = {
        25: "United States", 32: "Eurozone", 6: "Australia", 37: "Japan",
        72: "Germany", 22: "United Kingdom", 17: "Canada", 39: "Switzerland",
        14: "China", 10: "New Zealand", 35: "Sweden", 43: "Norway",
        56: "France", 36: "South Korea", 110: "India", 11: "Brazil",
        26: "Italy", 12: "Russia", 4: "South Africa", 5: "Mexico"
    }
    
    # Mapping des niveaux d'impact Investing.com
    IMPACT_MAP = {
        1: "Low",
        2: "Medium", 
        3: "High",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "holiday": "Holiday"
    }
    
    def __init__(self, base_url: str = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
                 timeout: int = 30, retry_attempts: int = 3, csv_exporter=None, symbol_mapper=None,
                 countries: List[int] = None, timezone: int = 55):
        self.base_url = base_url
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.csv_exporter = csv_exporter
        self.symbol_mapper = symbol_mapper or SymbolMapper()
        self.countries = countries or [25, 32, 6, 37, 72, 22, 17, 39, 14, 10, 35, 43, 56, 36, 110, 11, 26, 12, 4, 5]
        self.timezone = timezone
        
        # Headers pour simuler un navigateur
        self.headers = {
            'accept': '*/*',
            'accept-language': 'fr-FR,fr;q=0.9,en-FR;q=0.8,en;q=0.7,ar-EG;q=0.6,ar;q=0.5,en-US;q=0.4',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.investing.com',
            'referer': 'https://www.investing.com/economic-calendar/',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Session pour maintenir les cookies
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def _make_api_request(self, date_from: datetime, date_to: datetime, limit_from: int = 0) -> Optional[Dict]:
        """
        Faire une requête POST à l'API Investing.com
        
        Args:
            date_from: Date de début
            date_to: Date de fin
            limit_from: Offset pour pagination
            
        Returns:
            Réponse JSON ou None en cas d'erreur
        """
        # Formater les dates au format YYYY-MM-DD
        date_from_str = date_from.strftime('%Y-%m-%d')
        date_to_str = date_to.strftime('%Y-%m-%d')
        
        # Préparer les données POST (form-urlencoded avec valeurs multiples)
        post_data = []
        
        # Ajouter les pays (valeurs multiples)
        for country_id in self.countries:
            post_data.append(('country[]', str(country_id)))
        
        # Ajouter les autres paramètres
        post_data.extend([
            ('dateFrom', date_from_str),
            ('dateTo', date_to_str),
            ('timeZone', str(self.timezone)),
            ('timeFilter', 'timeRemain'),
            ('currentTab', 'custom'),
            ('limit_from', str(limit_from))
        ])
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"API request attempt {attempt + 1}/{self.retry_attempts}: {date_from_str} to {date_to_str}")
                
                # Utiliser post_data directement (requests gère mieux les valeurs multiples)
                response = self.session.post(
                    self.base_url,
                    data=post_data,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        return json_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.debug(f"Response text: {response.text[:500]}")
                        if attempt < self.retry_attempts - 1:
                            time.sleep(random.uniform(2, 4))
                            continue
                        return None
                else:
                    logger.warning(f"API returned status {response.status_code}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(random.uniform(2, 4))
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    delay = random.uniform(2, 4) * (attempt + 1)
                    time.sleep(delay)
                    continue
                return None
        
        return None
    
    def _parse_json_response(self, json_data: Dict, reference_date: datetime = None) -> List[Dict]:
        """
        Parser la réponse JSON de l'API Investing.com
        
        Args:
            json_data: Données JSON de la réponse API
            reference_date: Date de référence à utiliser si la date n'est pas trouvée dans les données
            
        Returns:
            Liste d'événements extraits
        """
        events = []
        
        try:
            # Logger la structure de la réponse pour debug
            logger.debug(f"Parsing JSON response. Keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            
            # La structure de la réponse peut varier, on essaie plusieurs formats possibles
            data = json_data.get('data', [])
            
            if not data:
                # Essayer d'autres clés possibles
                data = json_data.get('events', [])
            
            logger.debug(f"Data type: {type(data)}, length/size: {len(data) if hasattr(data, '__len__') else 'N/A'}")
            
            # Si data est une string (HTML), on doit parser le HTML
            if isinstance(data, str) and data.strip():
                logger.debug(f"Response contains HTML string (length: {len(data)}), parsing HTML table...")
                logger.debug(f"First 200 chars of HTML: {data[:200]}")
                events = self._parse_html_response(data, reference_date)
                return events
            
            if isinstance(data, str):
                # Si data est une string JSON, essayer de la parser
                try:
                    data = json.loads(data)
                except:
                    # Si ce n'est pas du JSON, peut-être du HTML
                    if '<' in data and '>' in data:
                        return self._parse_html_response(data, reference_date)
                    pass
            
            if not isinstance(data, list):
                # Logger pour debug
                logger.debug(f"Data type: {type(data)}, keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'N/A'}")
                logger.warning(f"Unexpected data format: {type(data)}")
                # Essayer quand même de parser comme HTML si c'est une string
                if isinstance(data, str) and ('<' in data or 'table' in data.lower()):
                    return self._parse_html_response(data, reference_date)
                return []
            
            for event_data in data:
                event = self._transform_event(event_data, reference_date)
                if event:
                    events.append(event)
            
            logger.info(f"Parsed {len(events)} events from API response")
            return events
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.debug(f"JSON data structure: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            return []
    
    def _parse_html_response(self, html_content: str, reference_date: datetime = None) -> List[Dict]:
        """
        Parser le HTML retourné par l'API Investing.com
        
        Args:
            html_content: Contenu HTML de la réponse
            reference_date: Date de référence à utiliser si la date n'est pas trouvée dans les données
            
        Returns:
            Liste d'événements extraits du HTML
        """
        events = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Parser toutes les lignes tr
            all_rows = soup.find_all('tr')
            logger.debug(f"Found {len(all_rows)} total <tr> rows in HTML")
            
            current_date = reference_date
            date_headers_found = 0
            event_rows_found = 0
            events_parsed = 0
            
            for row in all_rows:
                # Vérifier si c'est une ligne d'en-tête de date (theDay)
                # Chercher un td avec la classe 'theDay'
                the_day = row.find('td', class_='theDay')
                if the_day:
                    date_headers_found += 1
                    # Extraire la date depuis l'ID (theDay1704067200 = timestamp)
                    the_day_id = the_day.get('id', '')
                    if the_day_id and the_day_id.startswith('theDay'):
                        try:
                            # Extraire le timestamp depuis l'ID
                            timestamp_str = the_day_id.replace('theDay', '')
                            if timestamp_str.isdigit():
                                timestamp = int(timestamp_str)
                                current_date = datetime.fromtimestamp(timestamp)
                                logger.debug(f"Found date header: {current_date}")
                        except:
                            # Sinon, essayer de parser depuis le texte
                            day_text = the_day.get_text(strip=True)
                            # Format: "Monday, January 1, 2024"
                            try:
                                current_date = datetime.strptime(day_text, '%A, %B %d, %Y')
                            except:
                                try:
                                    # Format alternatif
                                    current_date = datetime.strptime(day_text, '%A, %d %B %Y')
                                except:
                                    pass
                    continue  # Skip cette ligne, c'est un en-tête
                
                # Parser les lignes d'événements
                row_id = row.get('id', '')
                if row_id and 'eventRowId' in row_id:
                    event_rows_found += 1
                    # Utiliser current_date si disponible, sinon reference_date
                    date_for_event = current_date if current_date else reference_date
                    if date_for_event:
                        logger.debug(f"Parsing event row {row_id} with date: {date_for_event.date()}")
                    event = self._parse_html_event_row(row, date_for_event)
                    if event:
                        events_parsed += 1
                        # Log pour les événements Holiday
                        if event.get('Impact') == 'Holiday':
                            logger.debug(f"Parsed Holiday event: {event.get('Event')} on {event.get('DateTime')}")
                        events.append(event)
                    else:
                        logger.debug(f"Failed to parse event row with id: {row_id}")
            
            # Count holidays in parsed events
            holidays_parsed = [e for e in events if e.get('Impact') == 'Holiday']
            logger.info(f"Parsed {len(events)} events from HTML (found {date_headers_found} date headers, {event_rows_found} event rows, {events_parsed} successfully parsed, {len(holidays_parsed)} holidays)")
            
            # Vérifier si le HTML contient des références à "Holiday" même si non parsées
            if 'Holiday' in html_content or 'holiday' in html_content.lower():
                holiday_count_in_html = html_content.lower().count('holiday')
                if len(holidays_parsed) == 0 and holiday_count_in_html > 0:
                    logger.warning(f"HTML contains {holiday_count_in_html} mentions of 'holiday' but no Holiday events were parsed - this may indicate a parsing issue")
                    # Chercher les lignes avec "Holiday" dans le HTML pour debug
                    holiday_rows = soup.find_all('tr', string=lambda text: text and 'holiday' in text.lower())
                    if not holiday_rows:
                        # Chercher dans les cellules sentiment
                        sentiment_cells_with_holiday = soup.find_all('td', class_=lambda x: x and ('sentiment' in str(x).lower() if x else False))
                        holiday_cells = [cell for cell in sentiment_cells_with_holiday if 'holiday' in cell.get_text(strip=True).lower()]
                        if holiday_cells:
                            logger.debug(f"Found {len(holiday_cells)} sentiment cells containing 'Holiday' text")
            
            # Si aucun événement trouvé, logger plus de détails
            if len(events) == 0:
                logger.warning(f"No events parsed. HTML content length: {len(html_content)}")
                logger.debug(f"First 500 chars of HTML: {html_content[:500]}")
                # Chercher toutes les lignes avec un id
                all_ids = [row.get('id', '') for row in all_rows if row.get('id')]
                logger.debug(f"Sample row IDs found: {all_ids[:10]}")
            
            return events
            
        except Exception as e:
            logger.error(f"Error parsing HTML response: {e}", exc_info=True)
            return []
    
    def _parse_html_event_row(self, row, reference_date: datetime = None) -> Optional[Dict]:
        """
        Parser une ligne HTML d'événement Investing.com
        
        Structure réelle:
        - data-event-datetime="2024/01/01 00:00:00" dans le <tr>
        - <td class="time js-time">00:00</td> - heure
        - <td class="flagCur"> avec <span title="Country"> et devise (KRW, USD, etc.)
        - <td class="sentiment"> avec data-img_key="bull1" (Low), "bull2" (Medium), "bull3" (High)
        - <td class="event"> avec <a> contenant le nom
        - <td class="act"> - Actual
        - <td class="fore"> - Forecast  
        - <td class="prev"> - Previous
        
        Args:
            row: BeautifulSoup element représentant une ligne de table
            reference_date: Date de référence à utiliser si la date n'est pas trouvée
            
        Returns:
            Dictionnaire d'événement ou None
        """
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                return None
            
            event_data = {}
            
            # 1. DATE/HEURE - Extraire depuis data-event-datetime (format: "2024/01/01 00:00:00")
            datetime_attr = row.get('data-event-datetime', '')
            if datetime_attr:
                try:
                    # Format: "2024/01/01 00:00:00"
                    event_time = datetime.strptime(datetime_attr, '%Y/%m/%d %H:%M:%S')
                    event_data['timestamp'] = event_time.timestamp()
                except:
                    try:
                        # Essayer d'autres formats
                        event_time = datetime.strptime(datetime_attr, '%Y-%m-%d %H:%M:%S')
                        event_data['timestamp'] = event_time.timestamp()
                    except:
                        event_data['date'] = datetime_attr
            
            # 2. HEURE - Extraire depuis la cellule time (fallback si pas de data-event-datetime)
            # Pour les événements Holiday, on utilise "All Day" et on se base sur reference_date
            if not event_data.get('timestamp') and not event_data.get('date'):
                time_cell = row.find('td', class_=lambda x: x and ('time' in str(x).lower() if x else False))
                if time_cell:
                    time_text = time_cell.get_text(strip=True)
                    if time_text and time_text != 'All Day':
                        if ':' in time_text:
                            event_data['time'] = time_text
                    # Pour "All Day", on utilisera reference_date sans heure spécifique
            
            # 3. CURRENCY - Extraire depuis la cellule flagCur (texte après le span)
            flag_cell = row.find('td', class_=lambda x: x and ('flagcur' in str(x).lower() if x else False))
            if flag_cell:
                # La devise est le texte après le span (ex: "KRW" après le drapeau)
                flag_text = flag_cell.get_text(strip=True)
                # Chercher un code de devise (3-4 lettres majuscules)
                currency_match = re.search(r'\b([A-Z]{3,4})\b', flag_text)
                if currency_match:
                    event_data['currency'] = currency_match.group(1)
            
            # 4. COUNTRY - Extraire depuis le title du span dans flagCur
            if flag_cell:
                country_span = flag_cell.find('span', title=True)
                if country_span:
                    country_name = country_span.get('title', '')
                    if country_name:
                        event_data['country'] = country_name
            
            # 5. IMPACT - Extraire depuis data-img_key dans la cellule sentiment
            sentiment_cell = row.find('td', class_=lambda x: x and ('sentiment' in str(x).lower() if x else False))
            if sentiment_cell:
                # Vérifier d'abord si c'est un Holiday (texte dans la cellule ou dans un span)
                sentiment_text = sentiment_cell.get_text(strip=True)
                # Vérifier aussi dans les spans enfants (ex: <span class="bold">Holiday</span>)
                sentiment_spans = sentiment_cell.find_all('span')
                for span in sentiment_spans:
                    span_text = span.get_text(strip=True)
                    if 'holiday' in span_text.lower():
                        sentiment_text = 'Holiday'  # Forcer Holiday si trouvé dans un span
                        break
                
                if 'holiday' in sentiment_text.lower():
                    event_data['impact'] = 'Holiday'
                else:
                    impact_attr = sentiment_cell.get('data-img_key', '')
                    if impact_attr:
                        # bull1 = Low, bull2 = Medium, bull3 = High
                        if 'bull3' in impact_attr or '3' in impact_attr:
                            event_data['impact'] = 'High'
                        elif 'bull2' in impact_attr or '2' in impact_attr:
                            event_data['impact'] = 'Medium'
                        elif 'bull1' in impact_attr or '1' in impact_attr:
                            event_data['impact'] = 'Low'
                        else:
                            # Vérifier le title de la cellule
                            impact_title = sentiment_cell.get('title', '')
                            if 'high' in impact_title.lower():
                                event_data['impact'] = 'High'
                            elif 'medium' in impact_title.lower():
                                event_data['impact'] = 'Medium'
                            elif 'low' in impact_title.lower():
                                event_data['impact'] = 'Low'
            
            # 6. EVENT NAME - Extraire depuis le lien <a> dans la cellule event
            event_cell = row.find('td', class_=lambda x: x and ('event' in str(x).lower() if x else False))
            if event_cell:
                event_link = event_cell.find('a')
                if event_link:
                    event_data['title'] = event_link.get_text(strip=True)
                else:
                    # Pas de lien, prendre le texte de la cellule
                    event_text = event_cell.get_text(strip=True)
                    if event_text:
                        event_data['title'] = event_text
            
            # Si l'impact n'a pas été détecté mais que le nom de l'événement contient des mots-clés Holiday, le forcer
            # (fallback pour les cas où la cellule sentiment n'est pas trouvée ou mal parsée)
            if not event_data.get('impact') and event_data.get('title'):
                event_name_temp = event_data.get('title', '')
                if event_name_temp:
                    event_name_lower = event_name_temp.lower()
                    if any(holiday_keyword in event_name_lower for holiday_keyword in ['holiday', 'christmas', 'new year', 'new year\'s', 'thanksgiving', 'easter', 'independence day']):
                        event_data['impact'] = 'Holiday'
            
            # 7. ACTUAL - Extraire depuis la cellule avec classe "act" ou id "eventActual_*"
            actual_cell = row.find('td', class_=lambda x: x and ('act' in str(x).lower() if x else False))
            if not actual_cell:
                actual_cell = row.find('td', id=re.compile(r'eventActual'))
            if actual_cell:
                actual_text = actual_cell.get_text(strip=True)
                if actual_text and actual_text != '&nbsp;':
                    event_data['actual'] = actual_text
            
            # 8. FORECAST - Extraire depuis la cellule avec classe "fore" ou id "eventForecast_*"
            forecast_cell = row.find('td', class_=lambda x: x and ('fore' in str(x).lower() if x else False))
            if not forecast_cell:
                forecast_cell = row.find('td', id=re.compile(r'eventForecast'))
            if forecast_cell:
                forecast_text = forecast_cell.get_text(strip=True)
                if forecast_text and forecast_text != '&nbsp;':
                    event_data['forecast'] = forecast_text
            
            # 9. PREVIOUS - Extraire depuis la cellule avec classe "prev" ou id "eventPrevious_*"
            previous_cell = row.find('td', class_=lambda x: x and ('prev' in str(x).lower() if x else False))
            if not previous_cell:
                previous_cell = row.find('td', id=re.compile(r'eventPrevious'))
            if previous_cell:
                previous_text = previous_cell.get_text(strip=True)
                if previous_text and previous_text != '&nbsp;':
                    event_data['previous'] = previous_text
            
            # Si on a au moins un titre, transformer l'événement
            if event_data.get('title'):
                transformed = self._transform_event(event_data, reference_date)
                if not transformed:
                    logger.debug(f"Failed to transform event with title: {event_data.get('title')}")
                return transformed
            else:
                logger.debug(f"No title found in event row. Row ID: {row.get('id', 'N/A')}, cells: {len(cells)}")
                logger.debug(f"Found in row: datetime={event_data.get('timestamp') or event_data.get('date')}, currency={event_data.get('currency')}, country={event_data.get('country')}")
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing HTML row: {e}")
            return None
    
    def _transform_event(self, event_data: Dict, reference_date: datetime = None) -> Optional[Dict]:
        """
        Transformer un événement Investing.com vers le format attendu
        
        Args:
            event_data: Données d'un événement depuis l'API
            reference_date: Date de référence à utiliser si la date n'est pas trouvée dans les données
            
        Returns:
            Dictionnaire au format CSV ou None
        """
        try:
            # Extraire les informations de base
            event_name = event_data.get('title', event_data.get('event', event_data.get('name', '')))
            if not event_name:
                return None
            
            # DateTime
            event_time = None
            timestamp = event_data.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, (int, float)):
                        # Vérifier si c'est en millisecondes (13 chiffres)
                        if timestamp > 1000000000000:
                            timestamp = timestamp / 1000.0
                        event_time = datetime.fromtimestamp(timestamp)
                    elif isinstance(timestamp, str) and timestamp.isdigit():
                        ts_int = int(timestamp)
                        # Vérifier si c'est en millisecondes
                        if ts_int > 1000000000000:
                            ts_int = ts_int // 1000
                        event_time = datetime.fromtimestamp(ts_int)
                except Exception as e:
                    logger.debug(f"Could not parse timestamp {timestamp}: {e}")
            
            # Si pas de timestamp, essayer de parser date et heure séparément
            date_str = event_data.get('date', '')
            time_str = event_data.get('time', '')
            
            # Si on a une date, l'utiliser
            parsed_date = None
            if date_str and not event_time:
                try:
                    # Essayer différents formats de date
                    date_formats = [
                        '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', '%d-%m-%Y',
                        '%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M:%S',
                        '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M',
                        '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y'
                    ]
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            event_time = parsed_date
                            break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Could not parse date {date_str}: {e}")
            
            # Si on a une date parsée mais pas d'heure (heure = 0), et qu'on a une heure séparée, les combiner
            # Ou si on a une date sans heure explicite et qu'on a une heure séparée
            if event_time and event_time.hour == 0 and event_time.minute == 0 and time_str:
                try:
                    time_str_clean = time_str.replace('AM', '').replace('PM', '').replace('am', '').replace('pm', '').strip()
                    if ':' in time_str_clean:
                        parts = time_str_clean.split(':')
                        hour = int(parts[0])
                        minute = int(parts[1]) if len(parts) > 1 else 0
                        
                        # Gérer AM/PM si présent
                        if 'PM' in time_str.upper() and hour < 12:
                            hour += 12
                        elif 'AM' in time_str.upper() and hour == 12:
                            hour = 0
                        
                        event_time = event_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except Exception as e:
                    logger.debug(f"Could not combine time {time_str} with date: {e}")
            
            # Si on a seulement l'heure (pas de date), utiliser la date de référence
            if not event_time and time_str and reference_date:
                try:
                    # Parser l'heure (format: "08:30" ou "08:30 AM")
                    time_str_clean = time_str.replace('AM', '').replace('PM', '').replace('am', '').replace('pm', '').strip()
                    if ':' in time_str_clean:
                        parts = time_str_clean.split(':')
                        hour = int(parts[0])
                        minute = int(parts[1]) if len(parts) > 1 else 0
                        
                        # Gérer AM/PM si présent
                        if 'PM' in time_str.upper() and hour < 12:
                            hour += 12
                        elif 'AM' in time_str.upper() and hour == 12:
                            hour = 0
                        
                        event_time = reference_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except Exception as e:
                    logger.debug(f"Could not parse time {time_str}: {e}")
            
            # Si toujours pas de date, utiliser la date de référence (ou maintenant si pas de référence)
            if not event_time:
                if reference_date:
                    # Pour les événements sans date/heure (comme les Holidays "All Day"), utiliser la date de référence
                    # Utiliser midi par défaut seulement si vraiment aucune info de date/heure
                    event_time = reference_date.replace(hour=12, minute=0, second=0, microsecond=0)
                    logger.debug(f"Using reference_date {reference_date} for event without timestamp: {event_data.get('title', 'Unknown')}")
                else:
                    event_time = datetime.now()
                    logger.warning(f"No reference_date available, using current time for event: {event_data.get('title', 'Unknown')}")
            
            # Country
            country_id = event_data.get('countryId', event_data.get('country_id', event_data.get('country')))
            country = self._get_country_name(country_id)
            
            # Currency
            currency = event_data.get('currency', event_data.get('code', ''))
            if not currency:
                # Essayer d'extraire depuis le pays
                currency = self._get_currency_from_country(country_id)
            
            # Impact
            impact_value = event_data.get('impact', event_data.get('importance', event_data.get('priority')))
            
            # Si l'impact n'est pas détecté mais que l'événement semble être un Holiday (nom contient Holiday/Christmas/New Year), forcer Holiday
            # Cette vérification doit se faire AVANT d'appeler _parse_impact pour éviter les valeurs par défaut
            if not impact_value or (isinstance(impact_value, str) and impact_value.lower() not in ['holiday', 'high', 'medium', 'low']):
                event_name_lower = event_name.lower()
                if any(holiday_keyword in event_name_lower for holiday_keyword in ['holiday', 'christmas', 'new year', 'new year\'s', 'thanksgiving', 'easter', 'independence day']):
                    impact_value = 'Holiday'
            
            impact = self._parse_impact(impact_value)
            
            # Actual/Forecast/Previous
            actual = event_data.get('actual', event_data.get('actualValue', 'N/A'))
            forecast = event_data.get('forecast', event_data.get('forecastValue', 'N/A'))
            previous = event_data.get('previous', event_data.get('previousValue', 'N/A'))
            
            # Convertir en string si numérique
            if actual != 'N/A' and actual is not None:
                actual = str(actual)
            else:
                actual = 'N/A'
                
            if forecast != 'N/A' and forecast is not None:
                forecast = str(forecast)
            else:
                forecast = 'N/A'
                
            if previous != 'N/A' and previous is not None:
                previous = str(previous)
            else:
                previous = 'N/A'
            
            return {
                'DateTime': event_time,
                'Event': event_name,
                'Country': country,
                'Impact': impact,
                'Currency': currency,
                'Actual': actual,
                'Forecast': forecast,
                'Previous': previous
            }
            
        except Exception as e:
            logger.error(f"Error transforming event: {e}")
            logger.debug(f"Event data: {event_data}")
            return None
    
    def _get_country_name(self, country_id) -> str:
        """Obtenir le nom du pays depuis son ID"""
        if country_id is None:
            return 'Unknown'
        
        # Essayer de convertir en int si c'est une string
        try:
            country_id = int(country_id)
        except:
            # Si c'est déjà un nom de pays, le retourner
            if isinstance(country_id, str):
                return country_id
            return 'Unknown'
        
        return self.COUNTRY_MAP.get(country_id, f'Country_{country_id}')
    
    def _get_currency_from_country(self, country_id) -> str:
        """Obtenir la devise depuis le country ID (mapping basique)"""
        currency_map = {
            25: "USD", 32: "EUR", 6: "AUD", 37: "JPY",
            72: "EUR", 22: "GBP", 17: "CAD", 39: "CHF",
            14: "CNY", 10: "NZD", 35: "SEK", 43: "NOK",
            56: "EUR", 36: "KRW", 110: "INR", 11: "BRL",
            26: "EUR", 12: "RUB", 4: "ZAR", 5: "MXN"
        }
        
        try:
            country_id = int(country_id)
            return currency_map.get(country_id, '')
        except:
            return ''
    
    def _parse_impact(self, impact_value) -> str:
        """Parser le niveau d'impact"""
        if impact_value is None:
            return 'Medium'
        
        # Si c'est déjà une string avec une valeur valide, la retourner directement
        if isinstance(impact_value, str):
            impact_lower = impact_value.lower()
            if impact_lower in ['holiday', 'high', 'medium', 'low']:
                return impact_value if impact_value == 'Holiday' else impact_value.capitalize()
        
        # Essayer de convertir en int si c'est une string numérique
        try:
            impact_value = int(impact_value)
        except:
            pass
        
        # Essayer de convertir en string et mettre en minuscule
        impact_str = str(impact_value).lower()
        
        # Vérifier dans le mapping
        if impact_value in self.IMPACT_MAP:
            return self.IMPACT_MAP[impact_value]
        
        if impact_str in self.IMPACT_MAP:
            return self.IMPACT_MAP[impact_str]
        
        # Vérifier des patterns communs (Holiday en premier pour priorité)
        if 'holiday' in impact_str:
            return 'Holiday'
        elif 'high' in impact_str or impact_str == '3':
            return 'High'
        elif 'medium' in impact_str or impact_str == '2':
            return 'Medium'
        elif 'low' in impact_str or impact_str == '1':
            return 'Low'
        
        return 'Medium'  # Par défaut
    
    def scrape_single_day(self, target_date: datetime) -> List[Dict]:
        """
        Scraper les événements pour une seule journée
        
        Args:
            target_date: Date cible
            
        Returns:
            Liste d'événements
        """
        logger.info(f"Scraping Investing.com for {target_date.date()}")
        
        # Utiliser la même date pour from et to
        json_data = self._make_api_request(target_date, target_date)
        
        if not json_data:
            logger.warning(f"No data received for {target_date.date()}")
            return []
        
        events = self._parse_json_response(json_data, target_date)
        
        logger.info(f"Scraped {len(events)} events from Investing.com for {target_date.date()}")
        return events
    
    def scrape_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scraper les événements pour une plage de dates
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Liste d'événements
        """
        logger.info(f"Scraping Investing.com from {start_date.date()} to {end_date.date()}")
        
        all_events = []
        
        # Liste des jours fériés importants à scraper spécifiquement (car l'API ne les retourne pas toujours dans les chunks)
        important_holidays = []
        current_year = start_date.year
        end_year = end_date.year
        
        # Ajouter les jours fériés pour chaque année dans la plage
        for year in range(current_year, end_year + 1):
            # Christmas (25 décembre)
            christmas = datetime(year, 12, 25)
            if start_date <= christmas <= end_date:
                important_holidays.append(christmas)
            
            # New Year (1 janvier)
            new_year = datetime(year, 1, 1)
            if start_date <= new_year <= end_date:
                important_holidays.append(new_year)
        
        logger.info(f"Found {len(important_holidays)} important holiday dates in range to scrape separately")
        
        # Faire une requête pour toute la plage (l'API peut gérer les plages)
        # Mais on peut aussi découper en chunks pour éviter les limites
        chunk_days = 30  # 30 jours par chunk
        
        current_start = start_date
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
            
            logger.info(f"Scraping chunk: {current_start.date()} to {current_end.date()}")
            
            json_data = self._make_api_request(current_start, current_end)
            
            if json_data:
                # Pour chaque chunk, utiliser la date de début comme référence
                events = self._parse_json_response(json_data, current_start)
                all_events.extend(events)
                
                # Délai entre les chunks pour respecter le rate limiting
                if current_end < end_date:
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
            else:
                logger.warning(f"No data received for chunk {current_start.date()} to {current_end.date()}")
            
            current_start = current_end + timedelta(days=1)
        
        # Scraper spécifiquement les jours fériés importants pour s'assurer qu'ils sont inclus
        # (car l'API ne les retourne pas toujours dans les chunks)
        holiday_events = []
        for holiday_date in important_holidays:
            logger.info(f"Scraping holiday date: {holiday_date.date()}")
            try:
                events = self.scrape_single_day(holiday_date)
                holiday_events.extend(events)
                # Délai pour respecter le rate limiting
                delay = random.uniform(1, 2)
                time.sleep(delay)
            except Exception as e:
                logger.warning(f"Failed to scrape holiday date {holiday_date.date()}: {e}")
        
        if holiday_events:
            logger.info(f"Scraped {len(holiday_events)} additional events from holiday dates")
            all_events.extend(holiday_events)
        
        logger.info(f"Scraped {len(all_events)} total events from Investing.com")
        return all_events

