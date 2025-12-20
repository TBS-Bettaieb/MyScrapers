import asyncio
import sys
from investing_scraper import get_cookies, make_api_request

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def main():
    print("🔍 DEBUG PAGE 2")
    print("="*70 + "\n")

    cookies = get_cookies(cache=True)

    # Page 1
    print("📡 Récupération page 1 (offset=0)...")
    response1 = await make_api_request(
        cookies=cookies,
        date_from="2025-01-01",
        date_to="2025-06-30",
        limit_from=0,
        debug_mode=True
    )

    if response1:
        print(f"\n📊 Page 1:")
        print(f"   rows_num: {response1.get('rows_num')}")
        print(f"   bind_scroll_handler: {response1.get('bind_scroll_handler')}")
        print(f"   Nombre de pids: {len(response1.get('pids', []))}")
        print(f"   HTML size: {len(response1.get('data', ''))} chars")

        # Vérifier le contenu HTML
        html = response1.get('data', '')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select("tr[id^='eventRowId_']")
        print(f"   Lignes d'événements trouvées: {len(rows)}")

    # Page 2
    print(f"\n📡 Récupération page 2 (offset=200)...")
    response2 = await make_api_request(
        cookies=cookies,
        date_from="2025-01-01",
        date_to="2025-06-30",
        limit_from=200,
        debug_mode=True
    )

    if response2:
        print(f"\n📊 Page 2:")
        print(f"   rows_num: {response2.get('rows_num')}")
        print(f"   bind_scroll_handler: {response2.get('bind_scroll_handler')}")
        print(f"   Nombre de pids: {len(response2.get('pids', []))}")
        print(f"   HTML size: {len(response2.get('data', ''))} chars")

        # Vérifier le contenu HTML
        html = response2.get('data', '')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select("tr[id^='eventRowId_']")
        print(f"   Lignes d'événements trouvées: {len(rows)}")

        # Sauvegarder le HTML pour inspection
        with open('page2_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"   HTML sauvegardé dans page2_debug.html")

if __name__ == "__main__":
    asyncio.run(main())
