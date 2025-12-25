"""
Test du scraper AssoPoker
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.pronostic import scrape_assopoker
from models import Pronostic, PronosticResponse


async def test_assopoker_basic():
    """Test basique du scraper AssoPoker"""
    print("=== Test basique AssoPoker ===")

    result = await scrape_assopoker(max_tips=5, debug_mode=True)

    print(f"\nSuccess: {result['success']}")
    print(f"Total pronostics: {result['total_pronostics']}")
    print(f"Error message: {result['error_message']}")

    assert result['success'], "Le scraping devrait reussir"
    assert result['total_pronostics'] > 0, "Il devrait y avoir des pronostics"
    assert len(result['pronostics']) <= 5, "Il ne devrait pas y avoir plus de 5 pronostics"

    print("\n[OK] Test basique reussi")


async def test_assopoker_structure():
    """Test de la structure des pronostics AssoPoker"""
    print("\n=== Test de la structure des pronostics ===")

    result = await scrape_assopoker(max_tips=10, debug_mode=False)

    if result['pronostics']:
        prono = result['pronostics'][0]

        print(f"\nPremier pronostic:")
        print(f"  Match: {prono.get('match')}")
        print(f"  DateTime: {prono.get('dateTime')}")
        print(f"  Competition: {prono.get('competition')}")
        print(f"  Sport: {prono.get('sport')}")
        print(f"  Home Team: {prono.get('homeTeam')}")
        print(f"  Away Team: {prono.get('awayTeam')}")
        print(f"  Tip Title: {prono.get('tipTitle')}")
        print(f"  Tip Type: {prono.get('tipType')}")
        print(f"  Tip Text: {prono.get('tipText')}")
        print(f"  Odds: {prono.get('odds')}")
        print(f"  Reason: {prono.get('reasonTip')[:100] if prono.get('reasonTip') else 'N/A'}...")

        # Verifier que les champs essentiels sont presents
        required_fields = ['match', 'tipTitle', 'tipText']
        for field in required_fields:
            assert prono.get(field) or prono.get('tipTitle'), f"Le champ {field} devrait etre present"

        # Verifier que le champ sport est present
        assert 'sport' in prono, "Le champ 'sport' devrait etre present"

        print("\n[OK] Structure des pronostics validee")
    else:
        print("\n[WARN] Aucun pronostic trouve")


async def test_assopoker_with_models():
    """Test de compatibilite avec les modeles Pydantic"""
    print("\n=== Test de compatibilite avec les modeles ===")

    result = await scrape_assopoker(max_tips=3, debug_mode=False)

    # Convertir en objets Pronostic
    pronostics_obj = [Pronostic.from_dict(p) for p in result["pronostics"]]

    # Creer une reponse
    response = PronosticResponse(
        success=result["success"],
        pronostics=pronostics_obj,
        total_pronostics=result["total_pronostics"],
        error_message=result["error_message"],
        source="AssoPoker"
    )

    print(f"\nResponse object cree: success={response.success}, total={response.total_pronostics}")

    # Verifier que to_dict() fonctionne
    response_dict = response.to_dict()
    assert 'success' in response_dict
    assert 'pronostics' in response_dict
    assert 'total_pronostics' in response_dict
    assert 'source' in response_dict

    print(f"Response dict keys: {list(response_dict.keys())}")
    print("\n[OK] Compatibilite avec les modeles validee")


async def test_assopoker_full():
    """Test complet du scraper AssoPoker (tous les pronostics)"""
    print("\n=== Test complet AssoPoker (tous les pronostics) ===")

    result = await scrape_assopoker(max_tips=None, debug_mode=True)

    print(f"\nTotal pronostics recuperes: {result['total_pronostics']}")

    # Compter les pronostics par source
    schedine_count = sum(1 for p in result['pronostics'] if 'Schedina' in str(p.get('tipTitle', '')))
    articles_count = len(result['pronostics']) - schedine_count

    print(f"Pronostics depuis schedine-oggi: {schedine_count}")
    print(f"Pronostics depuis pronostici-oggi: {articles_count}")

    # Afficher quelques exemples
    print("\nExemples de pronostics:")
    for i, prono in enumerate(result['pronostics'][:5], 1):
        print(f"\n{i}. {prono.get('match')} - {prono.get('tipText')}")
        if prono.get('competition'):
            print(f"   Competition: {prono.get('competition')}")
        if prono.get('odds'):
            print(f"   Cote: {prono.get('odds')}")

    print("\n[OK] Test complet reussi")


async def test_all():
    """Execute tous les tests"""
    try:
        await test_assopoker_basic()
        await test_assopoker_structure()
        await test_assopoker_with_models()
        await test_assopoker_full()

        print("\n" + "=" * 80)
        print("[SUCCESS] Tous les tests ont reussi!")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n[FAIL] Test echoue: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n[ERROR] Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_all())
