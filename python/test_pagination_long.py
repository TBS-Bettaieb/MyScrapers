import asyncio
import sys
from investing_scraper import scrape_economic_calendar

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def main():
    print("🔧 TEST DE PAGINATION AVEC LONGUE PÉRIODE")
    print("="*70 + "\n")

    # Tester avec une période de 6 mois pour avoir plusieurs pages
    result = await scrape_economic_calendar(
        date_from="2025-01-01",
        date_to="2025-06-30",
        debug_mode=True,
        use_cache=True
    )

    print("\n📊 RÉSULTATS:")
    print(f"   Success: {result['success']}")
    print(f"   Total events: {result['total_events']}")
    print(f"   Total pages: {result.get('total_pages', 'N/A')}")
    print(f"   Date range: {result['date_range']}")

    if result['error_message']:
        print(f"   ❌ Erreur: {result['error_message']}")

    if result['events']:
        print(f"\n📋 Premiers 5 événements:")
        for i, event in enumerate(result['events'][:5], 1):
            print(f"   {i}. {event.get('datetime', 'N/A')} - {event['country']} - {event['event']}")

        print(f"\n📋 Derniers 5 événements:")
        for i, event in enumerate(result['events'][-5:], len(result['events']) - 4):
            print(f"   {i}. {event.get('datetime', 'N/A')} - {event['country']} - {event['event']}")

if __name__ == "__main__":
    asyncio.run(main())
