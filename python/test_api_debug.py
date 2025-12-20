"""
Script de débogage pour comprendre pourquoi l'API ne retourne pas tous les événements
"""
import asyncio
import sys
import io
from investing_scraper import scrape_economic_calendar

# Forcer l'encodage UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_api_pagination():
    """
    Teste la pagination de l'API et affiche les détails
    """
    print("="*70)
    print("🔍 TEST DE PAGINATION API")
    print("="*70)

    result = await scrape_economic_calendar(
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        time_filter="timeOnly",
        debug_mode=True,
        use_cache=True
    )

    print("\n" + "="*70)
    print("📊 RÉSULTATS API")
    print("="*70)
    print(f"✅ Succès: {result['success']}")
    print(f"📈 Événements économiques: {result['total_events']}")
    print(f"📄 Pages: {result['total_pages']}")
    print(f"📅 Période: {result['date_range']['from']} → {result['date_range']['to']}")

    if result['error_message']:
        print(f"❌ Erreur: {result['error_message']}")

    print("="*70)

    # Comparer avec Chrome
    chrome_total = 945  # Résultat obtenu précédemment
    api_total = result['total_events']
    difference = chrome_total - api_total

    print("\n" + "="*70)
    print("📊 COMPARAISON CHROME vs API")
    print("="*70)
    print(f"🌐 Chrome: {chrome_total} événements")
    print(f"🔌 API: {api_total} événements")
    print(f"❌ Différence: {difference} événements manquants ({(difference/chrome_total)*100:.1f}%)")
    print("="*70)

    # Afficher quelques événements
    if result['events']:
        print("\n📝 Premiers événements de l'API:")
        for i, event in enumerate(result['events'][:10], 1):
            print(f"   {i}. {event.get('event', 'N/A')} (ID: {event.get('event_id', 'N/A')})")

        print(f"\n📝 Derniers événements de l'API:")
        for i, event in enumerate(result['events'][-10:], len(result['events'])-9):
            print(f"   {i}. {event.get('event', 'N/A')} (ID: {event.get('event_id', 'N/A')})")


if __name__ == "__main__":
    asyncio.run(test_api_pagination())
