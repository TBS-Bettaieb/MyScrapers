import asyncio
import sys
from investing_scraper import scrape_economic_calendar

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def main():
    print("🔧 TEST DU SCRAPER INVESTING.COM")
    print("="*70 + "\n")
    
    result = await scrape_economic_calendar(
        debug_mode=True,
        use_cache=True  # Utilise le cache des cookies si disponible
    )
    
    print("\n📊 RÉSULTATS:")
    print(f"   Success: {result['success']}")
    print(f"   Total events: {result['total_events']}")
    print(f"   Date range: {result['date_range']}")
    
    if result['error_message']:
        print(f"   ❌ Erreur: {result['error_message']}")
    
    if result['events']:
        print(f"\n📋 Premiers événements:")
        for i, event in enumerate(result['events'][:5], 1):
            print(f"   {i}. {event['time']} - {event['country']} - {event['event']}")

if __name__ == "__main__":
    asyncio.run(main())