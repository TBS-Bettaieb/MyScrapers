"""
Scraper spécialisé pour investing.com - Calendrier économique
Utilise Crawl4AI avec JsonCssExtractionStrategy pour extraire les événements économiques
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
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
    time_filter: str = "timeOnly",
    debug_mode: bool = True,
    keep_open_seconds: int = 0
) -> Dict[str, Any]:
    """
    Scrape le calendrier économique d'investing.com via interactions de page Crawl4AI
    
    Args:
        date_from: Date de début au format YYYY-MM-DD (défaut: aujourd'hui)
        date_to: Date de fin au format YYYY-MM-DD (défaut: dans 30 jours)
        countries: Liste des IDs de pays à filtrer (None = tous)
        categories: Liste des catégories à filtrer (None = toutes)
        importance: Liste des niveaux d'importance [1,2,3] (None = tous)
        timezone: ID du fuseau horaire (58 = GMT+1)
        time_filter: Filtre temporel (défaut: "timeOnly")
        debug_mode: Active les logs détaillés
        keep_open_seconds: Temps en secondes pour garder le navigateur ouvert (0 = fermer immédiatement)
    
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
    
    # JavaScript ROBUSTE - Continue même en cas d'échec + délai inconditionnel
    js_interact_filters = r"""
    (async function() {
        const logStyle = 'background: #222; color: #00ff00; padding: 5px 10px; font-size: 14px; font-weight: bold;';
        const errorStyle = 'background: #ff0000; color: #fff; padding: 5px 10px; font-size: 14px; font-weight: bold;';
        const successStyle = 'background: #00ff00; color: #000; padding: 5px 10px; font-size: 14px; font-weight: bold;';
        const warningStyle = 'background: #ff9900; color: #000; padding: 5px 10px; font-size: 14px; font-weight: bold;';
        
        const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
        
        const clickWithRetry = async (selector, description, maxRetries = 3) => {
            for (let i = 0; i < maxRetries; i++) {
                try {
                    const element = document.querySelector(selector);
                    if (element && element.offsetParent !== null) {
                        element.click();
                        console.log('%c SUCCESS: ' + description, successStyle);
                        return true;
                    }
                    console.log('%c RETRY ' + (i + 1) + '/' + maxRetries + ': ' + description, logStyle);
                    await wait(500);
                } catch (e) {
                    console.error('%c ERROR: ' + description, errorStyle, e);
                }
            }
            console.log('%c SKIPPED (not found): ' + description, warningStyle);
            await wait(4000);
            return false;
        };
        
        const checkBox = async (selector, description) => {
            try {
                const element = document.querySelector(selector);
                if (element) {
                    if (!element.checked) {
                        element.checked = true;
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    console.log('%c CHECKED: ' + description, successStyle);
                    return true;
                }
            } catch (e) {
                console.error('%c ERROR checkbox: ' + description, errorStyle, e);
            }
            return false;
        };
        
        console.log('%c START INVESTING SCRIPT', 'background: #0066ff; color: #fff; padding: 10px; font-size: 16px; font-weight: bold;');
        
        try {
            // STEP 0: Handle popups (non-bloquant)
            console.log('%c STEP 0: Handling popups', logStyle);
            await wait(2000);
            
            await clickWithRetry('#onetrust-accept-btn-handler', 'OneTrust Accept');
            await wait(1500);
            
            await clickWithRetry('i.popupCloseIcon.largeBannerCloser', 'Banner Close');
            await wait(1000);
            
            const closeSelectors = ['i.popupCloseIcon', '.popupCloseIcon'];
            for (const selector of closeSelectors) {
                await clickWithRetry(selector, 'Popup ' + selector);
                await wait(500);
            }
            
            await wait(1500);
            
            // STEP 1: Open filters
            console.log('%c STEP 1: Opening filters', logStyle);
            const filterOpened = await clickWithRetry('#filterStateAnchor', 'Filter Button');
            
            if (filterOpened) {
                await wait(2000);
                
                // STEP 2: Select all countries
                console.log('%c STEP 2: Select all countries', logStyle);
                const allLinks = Array.from(document.querySelectorAll('a'));
                const selectAllCountries = allLinks.find(a => 
                    a.textContent.trim() === 'Select All' && 
                    a.onclick && 
                    a.onclick.toString().includes('country')
                );
                
                if (selectAllCountries) {
                    selectAllCountries.click();
                    console.log('%c Select All Countries clicked', successStyle);
                    await wait(800);
                }
                
                // STEP 3: Select time only radio
                console.log('%c STEP 3: Select Display time only', logStyle);
                await clickWithRetry('#timetimeOnly', 'Radio Display time only');
                await wait(500);
                
                // STEP 4: Select all categories
                console.log('%c STEP 4: Select all categories', logStyle);
                const selectAllCategories = allLinks.find(a => 
                    a.textContent.trim() === 'Select All' && 
                    a.onclick && 
                    a.onclick.toString().includes('category')
                );
                
                if (selectAllCategories) {
                    selectAllCategories.click();
                    console.log('%c Select All Categories clicked', successStyle);
                    await wait(800);
                }
                
                // STEP 5: Check all importance levels
                console.log('%c STEP 5: Checking importance levels', logStyle);
                await checkBox('#importance1', 'Importance Low');
                await wait(300);
                await checkBox('#importance2', 'Importance Medium');
                await wait(300);
                await checkBox('#importance3', 'Importance High');
                await wait(500);
                
                // STEP 6: Apply filters
                console.log('%c STEP 6: Applying filters', logStyle);
                await clickWithRetry('#ecSubmitButton', 'Apply Button');
                await wait(3000);
                
                // STEP 7: Select UTC timezone
                console.log('%c STEP 7: Selecting UTC timezone', logStyle);
                await clickWithRetry('#economicCurrentTimePop', 'Timezone Selector');
                await wait(800);
                await clickWithRetry('#liTz55', 'UTC Timezone');
                await wait(1500);
            } else {
                console.log('%c WARNING: Filters not opened, continuing anyway', warningStyle);
                await wait(4000);
            }
            
            console.log('%c SCRIPT EXECUTION COMPLETED', 'background: #00ff00; color: #000; padding: 10px; font-size: 16px; font-weight: bold;');
            
        } catch (error) {
            console.error('%c SCRIPT ERROR (but continuing): ', errorStyle, error);
        }
        
        window.INVESTING_SCRIPT_COMPLETED = true;
        
        // DÉLAI INCONDITIONNEL - TOUJOURS EXÉCUTÉ
        const keepOpenSeconds = window.KEEP_OPEN_SECONDS || 0;
        if (keepOpenSeconds > 0) {
            console.log('%c INSPECTION MODE: Keeping page open for ' + keepOpenSeconds + ' seconds', 'background: #ff9900; color: #000; padding: 10px; font-size: 16px; font-weight: bold;');
            
            let remaining = keepOpenSeconds;
            while (remaining > 0) {
                const nextWait = Math.min(5, remaining);
                console.log('%c Browser will close in ' + remaining + ' seconds...', 'background: #ff9900; color: #000; padding: 5px;');
                await wait(nextWait * 1000);
                remaining -= nextWait;
            }
            
            console.log('%c INSPECTION TIME ENDED - Closing now', 'background: #ff0000; color: #fff; padding: 10px;');
        }
        
        console.log('%c SCRIPT FULLY COMPLETED - Browser will close', 'background: #0066ff; color: #fff; padding: 10px; font-size: 16px; font-weight: bold;');
        
    })();
    """
    
    try:
        browser_config = BrowserConfig(
            headless=False,
            java_script_enabled=True,
            verbose=debug_mode,
        )
        
        # Injection du temps d'attente dans la page
        js_setup = f"window.KEEP_OPEN_SECONDS = {keep_open_seconds};"
        
        config = CrawlerRunConfig(
            js_code=[js_setup, js_interact_filters],
            wait_for="js:() => window.INVESTING_SCRIPT_COMPLETED === true",
            delay_before_return_html=15.0,
            page_timeout=120000,
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=JsonCssExtractionStrategy(ECONOMIC_EVENT_SCHEMA),
            wait_until="networkidle"
        )
        
        print("\n" + "="*70)
        print("🚀 DÉMARRAGE DU SCRAPING")
        print("="*70)
        print(f"📅 Période: {date_from} → {date_to}")
        print(f"🌍 Timezone: {timezone}")
        print(f"⚙️  Mode debug: {debug_mode}")
        print(f"⏱️  Keep open: {keep_open_seconds}s")
        print("="*70 + "\n")
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("🌐 Chargement de la page investing.com...")
            print(f"⏱️  Le navigateur restera ouvert {keep_open_seconds} secondes après exécution JS")
            print("📌 Ouvrez DevTools (F12) maintenant pour voir les logs !\n")
            
            result = await crawler.arun(
                url="https://www.investing.com/economic-calendar/",
                config=config
            )
            
            print("✅ Page chargée et JS exécuté (navigateur maintenant fermé)")
        
        # Traitement après fermeture du crawler
        if not result.success:
            error_msg = result.error_message or "Erreur inconnue lors du scraping"
            if "blocked" in error_msg.lower() or "403" in error_msg or "forbidden" in error_msg.lower():
                error_msg = "Accès bloqué par investing.com. Vérifiez les headers et cookies."
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "error_message": f"Erreur lors du scraping: {error_msg}"
            }
        
        # Traiter les données extraites
        events = []
        html_content = result.html or result.cleaned_html or ""
        
        print(f"📄 HTML récupéré: {len(html_content)} caractères")
        
        if result.extracted_content:
            try:
                extracted_data = json.loads(result.extracted_content)
                if isinstance(extracted_data, list):
                    events = process_extracted_events(extracted_data)
                elif isinstance(extracted_data, dict) and "EconomicEvents" in extracted_data:
                    events = process_extracted_events(extracted_data["EconomicEvents"])
                print(f"✅ Événements extraits via strategy: {len(events)}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Erreur parsing extracted_content: {e}")
                events = extract_events_with_strategy(html_content)
                print(f"✅ Événements extraits via fallback: {len(events)}")
        else:
            events = extract_events_with_strategy(html_content)
            print(f"✅ Événements extraits directement: {len(events)}")
        
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
    except ConnectionError as e:
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "error_message": f"Erreur de connexion: {str(e)}"
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

