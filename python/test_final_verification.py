"""
Test final pour vérifier que la solution fonctionne correctement
"""
import asyncio
import sys
import io
from investing_scraper import scrape_economic_calendar

# Forcer l'encodage UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def test_final():
    """
    Test final avec les mêmes paramètres que votre requête originale
    """
    print("="*70)
    print("🧪 TEST FINAL DE VÉRIFICATION")
    print("="*70)
    print("\n📋 Paramètres de test (identiques à votre requête):")
    print("   - date_from: 2025-12-02")
    print("   - date_to: 2025-12-20")
    print("   - timezone: 58")
    print("   - time_filter: timeOnly")
    print("   - use_date_splitting: True (par défaut)")
    print("   - days_per_chunk: 1 (par défaut)")
    print("\n" + "="*70 + "\n")

    result = await scrape_economic_calendar(
        date_from="2025-12-02",
        date_to="2025-12-20",
        timezone=58,
        time_filter="timeOnly",
        debug_mode=False  # Mode production
    )

    print("\n" + "="*70)
    print("📊 RÉSULTATS")
    print("="*70)

    if result['success']:
        # Séparer les événements économiques des jours fériés
        events = []
        holidays = []

        for event in result["events"]:
            if event.get("type") == "holiday" or event.get("impact") == "Holiday":
                holidays.append(event)
            else:
                events.append(event)

        print(f"✅ Succès: {result['success']}")
        print(f"📈 Événements économiques: {len(events)}")
        print(f"🏖️  Jours fériés: {len(holidays)}")
        print(f"📊 Total: {result['total_events']}")
        print(f"📄 Chunks traités: {result['total_pages']}")
        print(f"📅 Période: {result['date_range']['from']} → {result['date_range']['to']}")

        print("\n" + "="*70)
        print("📊 COMPARAISON")
        print("="*70)

        old_total = 403  # Ancien résultat avec pagination
        chrome_total = 945  # Résultat Chrome
        new_total = result['total_events']

        print(f"🔴 Ancienne méthode (pagination): {old_total} événements")
        print(f"🌐 Chrome (réalité): {chrome_total} événements")
        print(f"🟢 Nouvelle méthode (découpage): {new_total} événements")

        improvement = ((new_total - old_total) / old_total) * 100
        coverage = (new_total / chrome_total) * 100

        print(f"\n📈 Amélioration: +{improvement:.1f}% ({new_total - old_total} événements supplémentaires)")
        print(f"📊 Couverture Chrome: {coverage:.1f}%")

        if new_total >= chrome_total * 0.95:  # 95% de couverture minimum
            print("\n✅ TEST RÉUSSI! La solution fonctionne correctement.")
        else:
            print("\n⚠️  TEST PARTIELLEMENT RÉUSSI. Couverture inférieure à 95%.")

        # Afficher quelques exemples
        print("\n" + "="*70)
        print("📝 EXEMPLES D'ÉVÉNEMENTS")
        print("="*70)

        print("\n🔹 Événements économiques (5 premiers):")
        for i, event in enumerate(events[:5], 1):
            print(f"   {i}. {event.get('event', 'N/A')} - {event.get('country', 'N/A')} ({event.get('time', 'N/A')})")

        if holidays:
            print("\n🔹 Jours fériés:")
            for i, holiday in enumerate(holidays, 1):
                print(f"   {i}. {holiday.get('event', 'N/A')} - {holiday.get('country', 'N/A')}")

    else:
        print(f"❌ Échec: {result.get('error_message', 'Erreur inconnue')}")

    print("\n" + "="*70)
    print("🏁 FIN DU TEST")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_final())
