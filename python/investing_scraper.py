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
from enum import IntEnum
import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


# =============================================================================
# ÉNUMÉRATIONS POUR PAYS ET TIMEZONES
# =============================================================================


class Country(IntEnum):
    """Énumération des pays avec leurs codes numériques investing.com"""
    UNITED_KINGDOM = 4  # United Kingdom
    UNITED_STATES = 5  # United States
    CANADA = 6  # Canada
    MEXICO = 7  # Mexico
    BERMUDA = 8  # Bermuda
    SWEDEN = 9  # Sweden
    ITALY = 10  # Italy
    SOUTH_KOREA = 11  # South Korea
    SWITZERLAND = 12  # Switzerland
    INDIA = 14  # India
    COSTA_RICA = 15  # Costa Rica
    GERMANY = 17  # Germany
    NIGERIA = 20  # Nigeria
    NETHERLANDS = 21  # Netherlands
    FRANCE = 22  # France
    ISRAEL = 23  # Israel
    DENMARK = 24  # Denmark
    AUSTRALIA = 25  # Australia
    SPAIN = 26  # Spain
    CHILE = 27  # Chile
    ARGENTINA = 29  # Argentina
    BRAZIL = 32  # Brazil
    IRELAND = 33  # Ireland
    BELGIUM = 34  # Belgium
    JAPAN = 35  # Japan
    SINGAPORE = 36  # Singapore
    CHINA = 37  # China
    PORTUGAL = 38  # Portugal
    HONG_KONG = 39  # Hong Kong
    THAILAND = 41  # Thailand
    MALAYSIA = 42  # Malaysia
    NEW_ZEALAND = 43  # New Zealand
    PAKISTAN = 44  # Pakistan
    PHILIPPINES = 45  # Philippines
    TAIWAN = 46  # Taiwan
    BANGLADESH = 47  # Bangladesh
    INDONESIA = 48  # Indonesia
    GREECE = 51  # Greece
    SAUDI_ARABIA = 52  # Saudi Arabia
    POLAND = 53  # Poland
    AUSTRIA = 54  # Austria
    CZECH_REPUBLIC = 55  # Czech Republic
    RUSSIA = 56  # Russia
    KENYA = 57  # Kenya
    EGYPT = 59  # Egypt
    NORWAY = 60  # Norway
    UKRAINE = 61  # Ukraine
    TURKIYE = 63  # Türkiye
    IRAQ = 66  # Iraq
    LEBANON = 68  # Lebanon
    BULGARIA = 70  # Bulgaria
    FINLAND = 71  # Finland
    EURO_ZONE = 72  # Euro Zone
    GHANA = 74  # Ghana
    ZIMBABWE = 75  # Zimbabwe
    COTE_DIVOIRE = 78  # Cote D'Ivoire
    RWANDA = 80  # Rwanda
    MOZAMBIQUE = 82  # Mozambique
    ZAMBIA = 84  # Zambia
    TANZANIA = 85  # Tanzania
    ANGOLA = 86  # Angola
    OMAN = 87  # Oman
    ESTONIA = 89  # Estonia
    SLOVAKIA = 90  # Slovakia
    JORDAN = 92  # Jordan
    HUNGARY = 93  # Hungary
    KUWAIT = 94  # Kuwait
    ALBANIA = 95  # Albania
    LITHUANIA = 96  # Lithuania
    LATVIA = 97  # Latvia
    ROMANIA = 100  # Romania
    KAZAKHSTAN = 102  # Kazakhstan
    LUXEMBOURG = 103  # Luxembourg
    MOROCCO = 105  # Morocco
    ICELAND = 106  # Iceland
    CYPRUS = 107  # Cyprus
    MALTA = 109  # Malta
    SOUTH_AFRICA = 110  # South Africa
    MALAWI = 111  # Malawi
    SLOVENIA = 112  # Slovenia
    CROATIA = 113  # Croatia
    AZERBAIJAN = 114  # Azerbaijan
    JAMAICA = 119  # Jamaica
    ECUADOR = 121  # Ecuador
    COLOMBIA = 122  # Colombia
    UGANDA = 123  # Uganda
    PERU = 125  # Peru
    VENEZUELA = 138  # Venezuela
    MONGOLIA = 139  # Mongolia
    UNITED_ARAB_EMIRATES = 143  # United Arab Emirates
    BAHRAIN = 145  # Bahrain
    PARAGUAY = 148  # Paraguay
    SRI_LANKA = 162  # Sri Lanka
    BOTSWANA = 163  # Botswana
    UZBEKISTAN = 168  # Uzbekistan
    QATAR = 170  # Qatar
    NAMIBIA = 172  # Namibia
    BOSNIA_HERZEGOVINA = 174  # Bosnia-Herzegovina
    VIETNAM = 178  # Vietnam
    URUGUAY = 180  # Uruguay
    MAURITIUS = 188  # Mauritius
    PALESTINIAN_TERRITORY = 193  # Palestinian Territory
    TUNISIA = 202  # Tunisia
    KYRGYZSTAN = 204  # Kyrgyzstan
    CAYMAN_ISLANDS = 232  # Cayman Islands
    SERBIA = 238  # Serbia
    MONTENEGRO = 247  # Montenegro

    @classmethod
    def get_by_code(cls, code: int) -> Optional['Country']:
        """Retourne le Country correspondant au code, ou None si introuvable"""
        try:
            return cls(code)
        except ValueError:
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Country']:
        """Retourne le Country correspondant au nom (case-insensitive), ou None si introuvable"""
        name_lower = name.lower().strip()
        # Mapping des noms vers les codes
        _name_map = {
            4: 'United Kingdom',
            5: 'United States',
            6: 'Canada',
            7: 'Mexico',
            8: 'Bermuda',
            9: 'Sweden',
            10: 'Italy',
            11: 'South Korea',
            12: 'Switzerland',
            14: 'India',
            15: 'Costa Rica',
            17: 'Germany',
            20: 'Nigeria',
            21: 'Netherlands',
            22: 'France',
            23: 'Israel',
            24: 'Denmark',
            25: 'Australia',
            26: 'Spain',
            27: 'Chile',
            29: 'Argentina',
            32: 'Brazil',
            33: 'Ireland',
            34: 'Belgium',
            35: 'Japan',
            36: 'Singapore',
            37: 'China',
            38: 'Portugal',
            39: 'Hong Kong',
            41: 'Thailand',
            42: 'Malaysia',
            43: 'New Zealand',
            44: 'Pakistan',
            45: 'Philippines',
            46: 'Taiwan',
            47: 'Bangladesh',
            48: 'Indonesia',
            51: 'Greece',
            52: 'Saudi Arabia',
            53: 'Poland',
            54: 'Austria',
            55: 'Czech Republic',
            56: 'Russia',
            57: 'Kenya',
            59: 'Egypt',
            60: 'Norway',
            61: 'Ukraine',
            63: 'Türkiye',
            66: 'Iraq',
            68: 'Lebanon',
            70: 'Bulgaria',
            71: 'Finland',
            72: 'Euro Zone',
            74: 'Ghana',
            75: 'Zimbabwe',
            78: "Cote D'Ivoire",
            80: 'Rwanda',
            82: 'Mozambique',
            84: 'Zambia',
            85: 'Tanzania',
            86: 'Angola',
            87: 'Oman',
            89: 'Estonia',
            90: 'Slovakia',
            92: 'Jordan',
            93: 'Hungary',
            94: 'Kuwait',
            95: 'Albania',
            96: 'Lithuania',
            97: 'Latvia',
            100: 'Romania',
            102: 'Kazakhstan',
            103: 'Luxembourg',
            105: 'Morocco',
            106: 'Iceland',
            107: 'Cyprus',
            109: 'Malta',
            110: 'South Africa',
            111: 'Malawi',
            112: 'Slovenia',
            113: 'Croatia',
            114: 'Azerbaijan',
            119: 'Jamaica',
            121: 'Ecuador',
            122: 'Colombia',
            123: 'Uganda',
            125: 'Peru',
            138: 'Venezuela',
            139: 'Mongolia',
            143: 'United Arab Emirates',
            145: 'Bahrain',
            148: 'Paraguay',
            162: 'Sri Lanka',
            163: 'Botswana',
            168: 'Uzbekistan',
            170: 'Qatar',
            172: 'Namibia',
            174: 'Bosnia-Herzegovina',
            178: 'Vietnam',
            180: 'Uruguay',
            188: 'Mauritius',
            193: 'Palestinian Territory',
            202: 'Tunisia',
            204: 'Kyrgyzstan',
            232: 'Cayman Islands',
            238: 'Serbia',
            247: 'Montenegro',
        }
        # Recherche exacte (case-insensitive)
        for code, country_name in _name_map.items():
            if country_name.lower() == name_lower:
                return cls(code)
        # Recherche par nom normalisé (sans underscores)
        name_normalized = name_lower.replace(' ', '_').replace('-', '_')
        for country in cls:
            if country.name.lower() == name_normalized:
                return country
        return None


class Timezone(IntEnum):
    """Énumération des fuseaux horaires avec leurs IDs investing.com"""
    GMT_1200_ENIWETOK_KWAJALEIN = 1  # (GMT +12:00) Eniwetok, Kwajalein
    GMT_1100_MIDWAY_ISLAND = 2  # (GMT -11:00) Midway Island
    GMT_1000_HAWAII = 3  # (GMT -10:00) Hawaii
    GMT_900_ALASKA = 4  # (GMT -9:00) Alaska
    GMT_800_PACIFIC_TIME_US_CANADA = 5  # (GMT -8:00) Pacific Time (US & Canada)
    GMT_700_MOUNTAIN_TIME_US_CANADA = 6  # (GMT -7:00) Mountain Time (US & Canada)
    GMT_600_CENTRAL_TIME_US_CANADA = 7  # (GMT -6:00) Central Time (US & Canada)
    GMT_500_EASTERN_TIME_US_CANADA = 8  # (GMT -5:00) Eastern Time (US & Canada)
    GMT_400_CARACAS = 9  # (GMT -4:00) Caracas
    GMT_400_ATLANTIC_TIME_CANADA = 10  # (GMT -4:00) Atlantic Time (Canada)
    GMT_330_NEWFOUNDLAND = 11  # (GMT -3:30) Newfoundland
    GMT_300_BRASILIA = 12  # (GMT -3:00) Brasilia
    GMT_100_AZORES = 14  # (GMT -1:00) Azores
    GMT_DUBLIN_EDINBURGH_LISBON_LONDON = 15  # (GMT) Dublin, Edinburgh, Lisbon, London
    GMT_100_AMSTERDAM_BERLIN_BERN_ROME_STOCKHOLM_VIENNA = 16  # (GMT +1:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna
    GMT_200_JERUSALEM = 17  # (GMT +2:00) Jerusalem
    GMT_300_MOSCOW_ST_PETERSBURG_VOLGOGRAD = 18  # (GMT +3:00) Moscow, St. Petersburg, Volgograd
    GMT_330_TEHRAN = 19  # (GMT +3:30) Tehran
    GMT_400_ABU_DHABI_DUBAI_MUSCAT = 20  # (GMT +4:00) Abu Dhabi, Dubai, Muscat
    GMT_430_KABUL = 21  # (GMT +4:30) Kabul
    GMT_500_EKATERINBURG = 22  # (GMT +5:00) Ekaterinburg
    GMT_530_CHENNAI_KOLKATA_MUMBAI_NEW_DELHI = 23  # (GMT +5:30) Chennai, Kolkata, Mumbai, New Delhi
    GMT_545_KATHMANDU = 24  # (GMT +5:45) Kathmandu
    GMT_600_DHAKA = 25  # (GMT +6:00) Dhaka
    GMT_630_YANGON_RANGOON = 26  # (GMT +6:30) Yangon (Rangoon)
    GMT_700_BANGKOK_HANOI_JAKARTA = 27  # (GMT +7:00) Bangkok, Hanoi, Jakarta
    GMT_800_BEIJING_CHONGQING_HONG_KONG_URUMQI = 28  # (GMT +8:00) Beijing, Chongqing, Hong Kong, Urumqi
    GMT_900_OSAKA_SAPPORO_TOKYO = 29  # (GMT +9:00) Osaka, Sapporo, Tokyo
    GMT_1030_ADELAIDE = 30  # (GMT +10:30) Adelaide
    GMT_1100_CANBERRA_MELBOURNE_SYDNEY = 31  # (GMT +11:00) Canberra, Melbourne, Sydney
    GMT_1100_SOLOMON_IS_NEW_CALEDONIA = 32  # (GMT +11:00) Solomon Is., New Caledonia
    GMT_1300_AUCKLAND_WELLINGTON = 33  # (GMT +13:00) Auckland, Wellington
    GMT_1100_SAMOA = 35  # (GMT -11:00) Samoa
    GMT_800_BAJA_CALIFORNIA = 36  # (GMT -8:00) Baja California
    GMT_700_ARIZONA = 37  # (GMT -7:00) Arizona
    GMT_600_CHIHUAHUA_LA_PAZ_MAZATLAN = 38  # (GMT -6:00) Chihuahua, La Paz, Mazatlan
    GMT_600_CENTRAL_AMERICA = 39  # (GMT -6:00) Central America
    GMT_600_GUADALAJARA_MEXICO_CITY_MONTERREY = 40  # (GMT -6:00) Guadalajara, Mexico City, Monterrey
    GMT_600_SASKATCHEWAN = 41  # (GMT -6:00) Saskatchewan
    GMT_500_BOGOTA_LIMA_QUITO = 42  # (GMT -5:00) Bogota, Lima, Quito
    GMT_500_INDIANA_EAST = 43  # (GMT -5:00) Indiana (East)
    GMT_300_ASUNCION = 44  # (GMT -3:00) Asuncion
    GMT_400_CUIABA = 45  # (GMT -4:00) Cuiaba
    GMT_400_GEORGETOWN_LA_PAZ_MANAUS_SAN_JUAN = 46  # (GMT -4:00) Georgetown, La Paz, Manaus, San Juan
    GMT_300_SANTIAGO = 47  # (GMT -3:00) Santiago
    GMT_300_BUENOS_AIRES = 48  # (GMT -3:00) Buenos Aires
    GMT_300_CAYENNE_FORTALEZA = 49  # (GMT -3:00) Cayenne, Fortaleza
    GMT_300_GREENLAND = 50  # (GMT -3:00) Greenland
    GMT_300_MONTEVIDEO = 51  # (GMT -3:00) Montevideo
    GMT_100_CAPE_VERDE_IS = 53  # (GMT -1:00) Cape Verde Is.
    GMT_100_CASABLANCA = 54  # (GMT +1:00) Casablanca
    GMT_COORDINATED_UNIVERSAL_TIME = 55  # (GMT) Coordinated Universal Time
    GMT_MONROVIA_REYKJAVIK = 56  # (GMT) Monrovia, Reykjavik
    GMT_100_BELGRADE_BRATISLAVA_BUDAPEST_LJUBLJANA_PRAGUE = 57  # (GMT +1:00) Belgrade, Bratislava, Budapest, Ljubljana, Prague
    GMT_100_BRUSSELS_COPENHAGEN_MADRID_PARIS = 58  # (GMT +1:00) Brussels, Copenhagen, Madrid, Paris
    GMT_100_SARAJEVO_SKOPJE_WARSAW_ZAGREB = 59  # (GMT +1:00) Sarajevo, Skopje, Warsaw, Zagreb
    GMT_100_WEST_CENTRAL_AFRICA = 60  # (GMT +1:00) West Central Africa
    GMT_200_WINDHOEK = 61  # (GMT +2:00) Windhoek
    GMT_200_AMMAN = 62  # (GMT +2:00) Amman
    GMT_300_ISTANBUL = 63  # (GMT +3:00) Istanbul
    GMT_200_BEIRUT = 64  # (GMT +2:00) Beirut
    GMT_200_CAIRO = 65  # (GMT +2:00) Cairo
    GMT_200_DAMASCUS = 66  # (GMT +2:00) Damascus
    GMT_0200_JOHANNESBURG = 67  # (GMT +02:00) Johannesburg
    GMT_200_HELSINKI_KYIV_RIGA_SOFIA_TALLINN_VILNIUS = 68  # (GMT +2:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius
    GMT_300_KUWAIT_RIYADH = 70  # (GMT +3:00) Kuwait, Riyadh
    GMT_300_BAGHDAD = 71  # (GMT +3:00) Baghdad
    GMT_300_NAIROBI = 72  # (GMT +3:00) Nairobi
    GMT_400_BAKU = 73  # (GMT +4:00) Baku
    GMT_500_KARACHI = 77  # (GMT +5:00) Karachi
    GMT_530_COLOMBO = 79  # (GMT +5:30) Colombo
    GMT_900_SEOUL = 88  # (GMT +9:00) Seoul
    GMT_1000_BRISBANE = 91  # (GMT +10:00) Brisbane
    GMT_1000_VLADIVOSTOK = 94  # (GMT +10:00) Vladivostok
    GMT_800_SINGAPORE = 113  # (GMT +8:00) Singapore
    GMT_100_LAGOS = 166  # (GMT +1:00) Lagos
    GMT_0800_MANILA = 178  # (GMT +08:00) Manila

    @classmethod
    def get_by_code(cls, code: int) -> Optional['Timezone']:
        """Retourne le Timezone correspondant au code, ou None si introuvable"""
        try:
            return cls(code)
        except ValueError:
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Timezone']:
        """Retourne le Timezone correspondant au nom (case-insensitive), ou None si introuvable"""
        name_lower = name.lower().strip()
        # Mapping des noms vers les codes
        _name_map = {
            1: '(GMT +12:00) Eniwetok, Kwajalein',
            2: '(GMT -11:00) Midway Island',
            3: '(GMT -10:00) Hawaii',
            4: '(GMT -9:00) Alaska',
            5: '(GMT -8:00) Pacific Time (US & Canada)',
            6: '(GMT -7:00) Mountain Time (US & Canada)',
            7: '(GMT -6:00) Central Time (US & Canada)',
            8: '(GMT -5:00) Eastern Time (US & Canada)',
            9: '(GMT -4:00) Caracas',
            10: '(GMT -4:00) Atlantic Time (Canada)',
            11: '(GMT -3:30) Newfoundland',
            12: '(GMT -3:00) Brasilia',
            14: '(GMT -1:00) Azores',
            15: '(GMT) Dublin, Edinburgh, Lisbon, London',
            16: '(GMT +1:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna',
            17: '(GMT +2:00) Jerusalem',
            18: '(GMT +3:00) Moscow, St. Petersburg, Volgograd',
            19: '(GMT +3:30) Tehran',
            20: '(GMT +4:00) Abu Dhabi, Dubai, Muscat',
            21: '(GMT +4:30) Kabul',
            22: '(GMT +5:00) Ekaterinburg',
            23: '(GMT +5:30) Chennai, Kolkata, Mumbai, New Delhi',
            24: '(GMT +5:45) Kathmandu',
            25: '(GMT +6:00) Dhaka',
            26: '(GMT +6:30) Yangon (Rangoon)',
            27: '(GMT +7:00) Bangkok, Hanoi, Jakarta',
            28: '(GMT +8:00) Beijing, Chongqing, Hong Kong, Urumqi',
            29: '(GMT +9:00) Osaka, Sapporo, Tokyo',
            30: '(GMT +10:30) Adelaide',
            31: '(GMT +11:00) Canberra, Melbourne, Sydney',
            32: '(GMT +11:00) Solomon Is., New Caledonia',
            33: '(GMT +13:00) Auckland, Wellington',
            35: '(GMT -11:00) Samoa',
            36: '(GMT -8:00) Baja California',
            37: '(GMT -7:00) Arizona',
            38: '(GMT -6:00) Chihuahua, La Paz, Mazatlan',
            39: '(GMT -6:00) Central America',
            40: '(GMT -6:00) Guadalajara, Mexico City, Monterrey',
            41: '(GMT -6:00) Saskatchewan',
            42: '(GMT -5:00) Bogota, Lima, Quito',
            43: '(GMT -5:00) Indiana (East)',
            44: '(GMT -3:00) Asuncion',
            45: '(GMT -4:00) Cuiaba',
            46: '(GMT -4:00) Georgetown, La Paz, Manaus, San Juan',
            47: '(GMT -3:00) Santiago',
            48: '(GMT -3:00) Buenos Aires',
            49: '(GMT -3:00) Cayenne, Fortaleza',
            50: '(GMT -3:00) Greenland',
            51: '(GMT -3:00) Montevideo',
            53: '(GMT -1:00) Cape Verde Is.',
            54: '(GMT +1:00) Casablanca',
            55: '(GMT) Coordinated Universal Time',
            56: '(GMT) Monrovia, Reykjavik',
            57: '(GMT +1:00) Belgrade, Bratislava, Budapest, Ljubljana, Prague',
            58: '(GMT +1:00) Brussels, Copenhagen, Madrid, Paris',
            59: '(GMT +1:00) Sarajevo, Skopje, Warsaw, Zagreb',
            60: '(GMT +1:00) West Central Africa',
            61: '(GMT +2:00) Windhoek',
            62: '(GMT +2:00) Amman',
            63: '(GMT +3:00) Istanbul',
            64: '(GMT +2:00) Beirut',
            65: '(GMT +2:00) Cairo',
            66: '(GMT +2:00) Damascus',
            67: '(GMT +02:00) Johannesburg',
            68: '(GMT +2:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius',
            70: '(GMT +3:00) Kuwait, Riyadh',
            71: '(GMT +3:00) Baghdad',
            72: '(GMT +3:00) Nairobi',
            73: '(GMT +4:00) Baku',
            77: '(GMT +5:00) Karachi',
            79: '(GMT +5:30) Colombo',
            88: '(GMT +9:00) Seoul',
            91: '(GMT +10:00) Brisbane',
            94: '(GMT +10:00) Vladivostok',
            113: '(GMT +8:00) Singapore',
            166: '(GMT +1:00) Lagos',
            178: '(GMT +08:00) Manila',
        }
        # Recherche exacte (case-insensitive)
        for code, timezone_name in _name_map.items():
            if timezone_name.lower() == name_lower:
                return cls(code)
        # Recherche partielle dans les noms
        for code, timezone_name in _name_map.items():
            if name_lower in timezone_name.lower() or timezone_name.lower() in name_lower:
                return cls(code)
        # Recherche par nom normalisé (sans underscores)
        name_normalized = name_lower.replace(' ', '_').replace('-', '_')
        for timezone in cls:
            if timezone.name.lower() == name_normalized:
                return timezone
        return None


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
    timezone: int = 55,
    time_filter: str = "timeOnly",
    limit_from: int = 0,
    previous_event_ids: Optional[List[str]] = None,
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
        limit_from: Offset de pagination (0 pour la première page, 1 pour les suivantes)
        previous_event_ids: Liste des IDs d'événements déjà récupérés (pagination par curseur)

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
    
    # Ajouter les IDs des événements précédents (pagination par curseur)
    if previous_event_ids:
        for event_id in previous_event_ids:
            # Format: "event-537228:" (avec deux points à la fin)
            if not event_id.startswith("event-"):
                event_id = f"event-{event_id}"
            if not event_id.endswith(":"):
                event_id = f"{event_id}:"
            params.append(("pids[]", event_id))

    # Autres paramètres
    params.extend([
        ("dateFrom", date_from),
        ("dateTo", date_to),
        ("timeZone", str(timezone)),
        ("timeFilter", time_filter),
        ("currentTab", "custom"),
        ("limit_from", str(limit_from))
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
    use_cache: bool = True,
    max_events: Optional[int] = None,
    use_date_splitting: bool = True,
    days_per_chunk: int = 1
) -> Dict[str, Any]:
    """
    Scrape le calendrier économique d'investing.com via l'API avec pagination automatique

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
        max_events: Nombre maximum d'événements à récupérer (None = tous)
        use_date_splitting: Si True, divise la période en chunks pour contourner la limite de l'API
        days_per_chunk: Nombre de jours par chunk (défaut: 1)

    Returns:
        Dictionnaire contenant:
        - success: bool
        - events: Liste des événements économiques
        - date_range: {"from": str, "to": str}
        - total_events: int
        - total_pages: int
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
        if use_date_splitting:
            print(f"📆 Découpage par périodes: {days_per_chunk} jour(s) par chunk")
        print("="*70 + "\n")

        # 1. Récupérer les cookies
        cookies = get_cookies(cache=use_cache)
        if not cookies:
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "total_pages": 0,
                "error_message": "Impossible de récupérer les cookies"
            }

        # 2. Découper la période en chunks (date splitting est maintenant la seule méthode supportée)
        if not use_date_splitting:
            return {
                "success": False,
                "events": [],
                "date_range": {"from": date_from, "to": date_to},
                "total_events": 0,
                "total_pages": 0,
                "error_message": "use_date_splitting=False n'est plus supporté. Utilisez use_date_splitting=True (défaut)."
            }
        
        if use_date_splitting:
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
            end_date = datetime.strptime(date_to, "%Y-%m-%d")
            total_days = (end_date - start_date).days + 1

            print(f"📊 Nombre de jours: {total_days}")
            print(f"📆 Stratégie: découpage en chunks de {days_per_chunk} jour(s)\n")

            all_events = []
            all_event_ids = set()  # Utiliser un set pour un lookup plus rapide
            chunk_num = 0
            current_date = start_date

            while current_date <= end_date:
                chunk_end = min(current_date + timedelta(days=days_per_chunk - 1), end_date)
                chunk_num += 1

                chunk_from = current_date.strftime("%Y-%m-%d")
                chunk_to = chunk_end.strftime("%Y-%m-%d")

                if debug_mode:
                    print(f"📡 Chunk {chunk_num}: {chunk_from} → {chunk_to}")
                else:
                    print(f"📡 Chunk {chunk_num}/{((end_date - start_date).days // days_per_chunk + 1)}: {chunk_from} → {chunk_to}")

                # Faire la requête pour ce chunk
                api_response = await make_api_request(
                    cookies=cookies,
                    date_from=chunk_from,
                    date_to=chunk_to,
                    countries=countries,
                    categories=categories,
                    importance=importance,
                    timezone=timezone,
                    time_filter=time_filter,
                    limit_from=0,
                    previous_event_ids=None,
                    debug_mode=False
                )

                if not api_response:
                    print(f"   ⚠️  Erreur pour le chunk {chunk_num}, passage au suivant")
                    current_date = chunk_end + timedelta(days=1)
                    continue

                # Extraire le HTML
                html_content = api_response.get("data", "")
                if not html_content:
                    print(f"   ⚠️  Pas de données pour le chunk {chunk_num}")
                    current_date = chunk_end + timedelta(days=1)
                    continue

                # Parser les événements
                chunk_events = extract_events_with_strategy(html_content)
                holidays = _extract_holidays_fallback(html_content)
                combined_events = chunk_events + holidays

                # Filtrer les doublons
                new_events_count = 0
                duplicate_count = 0

                for event in combined_events:
                    event_id = event.get("event_id", "")

                    # Vérifier si cet événement existe déjà
                    if event_id and event_id in all_event_ids:
                        duplicate_count += 1
                        continue

                    # Ajouter l'événement
                    all_events.append(event)
                    new_events_count += 1

                    if event_id:
                        all_event_ids.add(event_id)

                print(f"   ✅ {len(combined_events)} événements extraits, {new_events_count} nouveaux, {duplicate_count} doublons")

                # Vérifier la limite max_events
                if max_events is not None and len(all_events) >= max_events:
                    print(f"⚠️  Limite max_events atteinte ({max_events})")
                    break

                current_date = chunk_end + timedelta(days=1)

            print("\n" + "="*70)
            print(f"✅ SCRAPING TERMINÉ - {len(all_events)} événements extraits sur {chunk_num} chunk(s)")
            print("="*70 + "\n")

            return {
                "success": True,
                "events": all_events,
                "date_range": {"from": date_from, "to": date_to},
                "total_events": len(all_events),
                "total_pages": chunk_num,
                "error_message": None
            }
                
    except asyncio.TimeoutError:
        return {
            "success": False,
            "events": [],
            "date_range": {"from": date_from, "to": date_to},
            "total_events": 0,
            "total_pages": 0,
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
            "total_pages": 0,
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

        # Extraire l'event_id depuis l'attribut id du <tr>
        event_id = ""
        if row.get('id'):
            row_id = row.get('id')
            if row_id.startswith("eventRowId_"):
                event_id = row_id.replace("eventRowId_", "")

        return {
            "type": "holiday",
            "time": extract_text(cells[0]),
            "country": country,
            "event": holiday_name,
            "impact": "Holiday",
            "event_id": event_id
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
