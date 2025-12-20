"""
Analyse les réponses brutes de l'API pour comprendre la pagination
"""
import asyncio
import sys
import io
import json
from investing_scraper import get_cookies, make_api_request

# Forcer l'encodage UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def analyze_api_responses():
    """
    Analyse les réponses de l'API page par page
    """
    print("="*70)
    print("🔍 ANALYSE DES RÉPONSES API")
    print("="*70)

    # Récupérer les cookies
    cookies = get_cookies(cache=True)

    # Page 1: Sans pids[]
    print("\n📡 PAGE 1 (sans pids[])")
    response1 = await make_api_request(
        cookies=cookies,
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        time_filter="timeOnly",
        limit_from=0,
        previous_event_ids=None,
        debug_mode=True
    )

    if response1:
        print(f"   bind_scroll_handler: {response1.get('bind_scroll_handler')}")
        print(f"   rows_num: {response1.get('rows_num')}")
        print(f"   hasMoreResults: {response1.get('hasMoreResults')}")
        print(f"   HTML size: {len(response1.get('data', ''))} caractères")

        # Extraire les event IDs de la page 1
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response1.get('data', ''), 'html.parser')
        event_rows = soup.select("tr[id^='eventRowId_']")
        event_ids_page1 = [row.get('id', '').replace('eventRowId_', '') for row in event_rows]
        print(f"   Événements extraits: {len(event_ids_page1)}")
        print(f"   Premiers IDs: {event_ids_page1[:5]}")
        print(f"   Derniers IDs: {event_ids_page1[-5:]}")

        # Page 2: Avec pids[] de la page 1
        print("\n📡 PAGE 2 (avec pids[] de page 1)")
        response2 = await make_api_request(
            cookies=cookies,
            date_from="2025-12-02",
            date_to="2025-12-20",
            timezone=58,
            time_filter="timeOnly",
            limit_from=1,
            previous_event_ids=event_ids_page1,
            debug_mode=True
        )

        if response2:
            print(f"   bind_scroll_handler: {response2.get('bind_scroll_handler')}")
            print(f"   rows_num: {response2.get('rows_num')}")
            print(f"   hasMoreResults: {response2.get('hasMoreResults')}")
            print(f"   HTML size: {len(response2.get('data', ''))} caractères")

            soup2 = BeautifulSoup(response2.get('data', ''), 'html.parser')
            event_rows2 = soup2.select("tr[id^='eventRowId_']")
            event_ids_page2 = [row.get('id', '').replace('eventRowId_', '') for row in event_rows2]
            print(f"   Événements extraits: {len(event_ids_page2)}")
            print(f"   Premiers IDs: {event_ids_page2[:5]}")
            print(f"   Derniers IDs: {event_ids_page2[-5:]}")

            # Vérifier les doublons
            common_ids = set(event_ids_page1) & set(event_ids_page2)
            print(f"\n   🔍 Doublons entre page 1 et page 2: {len(common_ids)}")
            if len(common_ids) > 0:
                print(f"   Exemples de doublons: {list(common_ids)[:10]}")

            # Page 3: Avec pids[] de pages 1 + 2
            print("\n📡 PAGE 3 (avec pids[] de page 1 + page 2)")
            all_ids = event_ids_page1 + event_ids_page2
            response3 = await make_api_request(
                cookies=cookies,
                date_from="2025-12-02",
                date_to="2025-12-20",
                timezone=58,
                time_filter="timeOnly",
                limit_from=1,
                previous_event_ids=all_ids,
                debug_mode=True
            )

            if response3:
                print(f"   bind_scroll_handler: {response3.get('bind_scroll_handler')}")
                print(f"   rows_num: {response3.get('rows_num')}")
                print(f"   hasMoreResults: {response3.get('hasMoreResults')}")
                print(f"   HTML size: {len(response3.get('data', ''))} caractères")

                soup3 = BeautifulSoup(response3.get('data', ''), 'html.parser')
                event_rows3 = soup3.select("tr[id^='eventRowId_']")
                event_ids_page3 = [row.get('id', '').replace('eventRowId_', '') for row in event_rows3]
                print(f"   Événements extraits: {len(event_ids_page3)}")
                print(f"   Premiers IDs: {event_ids_page3[:5]}")
                print(f"   Derniers IDs: {event_ids_page3[-5:]}")

                # Comparer avec page 2
                if event_ids_page2 == event_ids_page3:
                    print(f"\n   ❌ PROBLÈME: Page 3 est identique à page 2!")
                else:
                    common_23 = set(event_ids_page2) & set(event_ids_page3)
                    print(f"\n   🔍 Doublons entre page 2 et page 3: {len(common_23)}")

    # Tester différentes stratégies
    print("\n" + "="*70)
    print("🧪 TEST DE STRATÉGIES ALTERNATIVES")
    print("="*70)

    # Stratégie 1: Ignorer limit_from (toujours 0)
    print("\n📡 Stratégie 1: limit_from=0 pour toutes les pages")
    response_s1 = await make_api_request(
        cookies=cookies,
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        time_filter="timeOnly",
        limit_from=0,  # Toujours 0
        previous_event_ids=event_ids_page1,
        debug_mode=False
    )

    if response_s1:
        soup_s1 = BeautifulSoup(response_s1.get('data', ''), 'html.parser')
        event_rows_s1 = soup_s1.select("tr[id^='eventRowId_']")
        event_ids_s1 = [row.get('id', '').replace('eventRowId_', '') for row in event_rows_s1]
        print(f"   Événements: {len(event_ids_s1)}")
        print(f"   bind_scroll_handler: {response_s1.get('bind_scroll_handler')}")

    # Stratégie 2: N'envoyer que les derniers IDs
    print("\n📡 Stratégie 2: Envoyer seulement les 10 derniers IDs")
    response_s2 = await make_api_request(
        cookies=cookies,
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        time_filter="timeOnly",
        limit_from=1,
        previous_event_ids=event_ids_page1[-10:],  # Seulement les 10 derniers
        debug_mode=False
    )

    if response_s2:
        soup_s2 = BeautifulSoup(response_s2.get('data', ''), 'html.parser')
        event_rows_s2 = soup_s2.select("tr[id^='eventRowId_']")
        event_ids_s2 = [row.get('id', '').replace('eventRowId_', '') for row in event_rows_s2]
        print(f"   Événements: {len(event_ids_s2)}")
        print(f"   bind_scroll_handler: {response_s2.get('bind_scroll_handler')}")
        print(f"   Premiers IDs: {event_ids_s2[:5]}")


if __name__ == "__main__":
    asyncio.run(analyze_api_responses())
