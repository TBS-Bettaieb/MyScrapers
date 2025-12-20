"""
Teste une stratégie de découpage par plage de dates
"""
import asyncio
import sys
import io
from datetime import datetime, timedelta
from investing_scraper import get_cookies, make_api_request
from bs4 import BeautifulSoup

# Forcer l'encodage UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def count_events_for_date_range(cookies, date_from, date_to):
    """
    Compte le nombre d'événements pour une plage de dates donnée
    """
    response = await make_api_request(
        cookies=cookies,
        date_from=date_from,
        date_to=date_to,
        timezone=58,
        time_filter="timeOnly",
        limit_from=0,
        previous_event_ids=None,
        debug_mode=False
    )

    if not response:
        return 0

    soup = BeautifulSoup(response.get('data', ''), 'html.parser')
    event_rows = soup.select("tr[id^='eventRowId_']")
    return len(event_rows)


async def test_date_splitting():
    """
    Teste le découpage de la période en plusieurs plages
    """
    print("="*70)
    print("🔍 TEST DE DÉCOUPAGE PAR PLAGES DE DATES")
    print("="*70)

    cookies = get_cookies(cache=True)

    # Période complète
    start_date = datetime.strptime("2025-12-02", "%Y-%m-%d")
    end_date = datetime.strptime("2025-12-20", "%Y-%m-%d")
    total_days = (end_date - start_date).days + 1

    print(f"\n📅 Période totale: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Nombre de jours: {total_days} jours")

    # Tester différentes tailles de chunks
    chunk_sizes = [1, 2, 3, 5, 7]

    for chunk_size in chunk_sizes:
        print(f"\n{'='*70}")
        print(f"🧪 TEST: Chunks de {chunk_size} jour(s)")
        print(f"{'='*70}")

        total_events = 0
        chunk_num = 0
        current_date = start_date

        while current_date <= end_date:
            chunk_end = min(current_date + timedelta(days=chunk_size - 1), end_date)
            chunk_num += 1

            date_from_str = current_date.strftime("%Y-%m-%d")
            date_to_str = chunk_end.strftime("%Y-%m-%d")

            count = await count_events_for_date_range(cookies, date_from_str, date_to_str)
            total_events += count

            print(f"   Chunk {chunk_num:2d}: {date_from_str} → {date_to_str} : {count:4d} événements")

            current_date = chunk_end + timedelta(days=1)

        print(f"\n   📊 Total: {total_events} événements sur {chunk_num} chunks")

        # Calculer le pourcentage par rapport à Chrome (945 événements)
        chrome_total = 945
        percentage = (total_events / chrome_total) * 100
        print(f"   📈 Couverture: {percentage:.1f}% par rapport à Chrome ({chrome_total} événements)")

        # Si on atteint 100%, on a trouvé la bonne stratégie
        if total_events >= chrome_total:
            print(f"\n   ✅ SUCCÈS! Tous les événements sont récupérés avec des chunks de {chunk_size} jour(s)")
            break


if __name__ == "__main__":
    asyncio.run(test_date_splitting())
