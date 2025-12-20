"""
Script pour vérifier le nombre réel d'événements sur Investing.com avec Chrome
et comparer avec les résultats de notre scraper
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def count_events_with_chrome(date_from="2025-12-02", date_to="2025-12-20", timezone=58, headless=False):
    """
    Compte les événements sur Investing.com en utilisant Chrome
    """
    driver = None
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        chrome_options.add_argument('--window-size=1920,1080')

        driver = webdriver.Chrome(options=chrome_options)

        # Construire l'URL avec les paramètres
        url = f"https://www.investing.com/economic-calendar/"
        print(f"\n🌐 Ouverture de {url}")
        driver.get(url)

        # Attendre que la page se charge
        print("⏳ Attente du chargement de la page...")
        time.sleep(5)

        # Cliquer sur "Custom" pour accéder aux filtres personnalisés
        try:
            custom_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "customDateContainer"))
            )
            custom_button.click()
            print("✅ Clic sur 'Custom'")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Impossible de cliquer sur Custom: {e}")

        # Configurer les dates via JavaScript
        print(f"📅 Configuration des dates: {date_from} → {date_to}")
        driver.execute_script(f"""
            document.getElementById('startDate').value = '{date_from}';
            document.getElementById('endDate').value = '{date_to}';
        """)
        time.sleep(1)

        # Soumettre le formulaire de filtre
        try:
            submit_button = driver.find_element(By.ID, "filterStateAply")
            submit_button.click()
            print("✅ Filtre appliqué")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️  Impossible de soumettre le filtre: {e}")

        # Scroller pour charger tous les événements
        print("\n🔄 Scroll pour charger tous les événements...")

        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 50  # Limite de sécurité
        events_count = 0

        while scroll_count < max_scrolls:
            # Scroller vers le bas
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Attendre le chargement

            # Compter les événements actuels
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            event_rows = soup.select("tr[id^='eventRowId_']")
            new_events_count = len(event_rows)

            print(f"   Scroll {scroll_count + 1}: {new_events_count} événements trouvés")

            # Vérifier si de nouveaux événements ont été chargés
            if new_events_count == events_count:
                print("   ✅ Plus de nouveaux événements chargés")
                break

            events_count = new_events_count
            scroll_count += 1

            # Vérifier si on a atteint le bas
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("   ✅ Bas de page atteint")
                break
            last_height = new_height

        # Compter les événements finaux
        print("\n📊 Analyse finale...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Événements économiques
        event_rows = soup.select("tr[id^='eventRowId_']")
        economic_events = []

        for row in event_rows:
            event_name_elem = row.select_one("td.event a")
            if event_name_elem:
                event_name = event_name_elem.get_text(strip=True)
                if event_name:
                    economic_events.append(event_name)

        # Jours fériés
        holidays = []
        all_rows = soup.find_all('tr')
        for row in all_rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                holiday_span = cells[2].find('span', class_='bold')
                if holiday_span and holiday_span.get_text(strip=True) == 'Holiday':
                    holiday_name = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    if holiday_name:
                        holidays.append(holiday_name)

        print("\n" + "="*70)
        print("📊 RÉSULTATS DE CHROME")
        print("="*70)
        print(f"📅 Période: {date_from} → {date_to}")
        print(f"📈 Événements économiques: {len(economic_events)}")
        print(f"🏖️  Jours fériés: {len(holidays)}")
        print(f"📊 Total: {len(economic_events) + len(holidays)}")
        print("="*70)

        if len(economic_events) > 0:
            print(f"\n📝 Premiers événements:")
            for i, event in enumerate(economic_events[:10], 1):
                print(f"   {i}. {event}")

        if len(holidays) > 0:
            print(f"\n🏖️  Jours fériés:")
            for i, holiday in enumerate(holidays, 1):
                print(f"   {i}. {holiday}")

        # Sauvegarder le HTML pour analyse
        with open('chrome_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("\n💾 Page HTML sauvegardée dans 'chrome_page_source.html'")

        return {
            "economic_events": len(economic_events),
            "holidays": len(holidays),
            "total": len(economic_events) + len(holidays)
        }

    except Exception as e:
        import traceback
        print(f"\n❌ Erreur: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        traceback.print_exc()
        return None

    finally:
        if driver and not headless:
            print("\n⏸️  Navigateur ouvert. Appuyez sur Entrée pour fermer...")
            input()
        if driver:
            driver.quit()


if __name__ == "__main__":
    import sys
    import io
    # Forcer l'encodage UTF-8 pour la sortie console
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("="*70)
    print("🔍 VÉRIFICATION AVEC CHROME")
    print("="*70)

    # Tester avec les mêmes paramètres que l'API
    result = count_events_with_chrome(
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        headless=False  # Mode visible pour debug
    )

    if result:
        print("\n✅ Test terminé!")
        print(f"\n📊 Chrome a trouvé: {result['total']} événements au total")
        print(f"   - {result['economic_events']} événements économiques")
        print(f"   - {result['holidays']} jours fériés")
