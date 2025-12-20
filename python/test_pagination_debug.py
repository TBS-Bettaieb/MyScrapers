import asyncio
import sys
import json
from investing_scraper import scrape_economic_calendar

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def main():
    print("🔧 TEST DEBUG PAGINATION")
    print("="*70 + "\n")

    # Tester avec la période complète pour voir la pagination
    result = await scrape_economic_calendar(
        date_from="2025-12-20",
        date_to="2026-01-19",
        debug_mode=True,
        use_cache=True
    )

    print("\n📊 RÉSULTATS:")
    print(f"   Success: {result['success']}")
    print(f"   Total events: {result['total_events']}")
    print(f"   Total pages: {result.get('total_pages', 'N/A')}")

    # Afficher les IDs uniques
    event_ids = [e.get('event_id', '') for e in result['events'] if e.get('event_id')]
    print(f"   Total IDs uniques: {len(set(event_ids))}")
    print(f"   Total événements avec ID: {len([e for e in result['events'] if e.get('event_id')])}")
    print(f"   Total événements sans ID: {len([e for e in result['events'] if not e.get('event_id')])}")

    # Afficher quelques IDs
    if event_ids:
        print(f"\n📋 Premiers IDs:")
        for i, event_id in enumerate(event_ids[:5], 1):
            event = [e for e in result['events'] if e.get('event_id') == event_id][0]
            print(f"   {i}. {event_id} - {event['event']}")

if __name__ == "__main__":
    asyncio.run(main())
