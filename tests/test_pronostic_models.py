"""
Test des modeles de donnees pour les pronostics
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Pronostic, PronosticResponse


def test_pronostic_creation():
    """Test de creation d'un pronostic"""
    print("=== Test de creation d'un pronostic ===")

    # Creation avec tous les champs
    prono1 = Pronostic(
        match="Manchester United vs Liverpool",
        dateTime="2025-12-23T15:00:00",
        competition="Premier League",
        homeTeam="Manchester United",
        awayTeam="Liverpool",
        tipTitle="Both Teams To Score",
        tipType="both_teams_to_score",
        tipText="Yes - Both Teams To Score",
        reasonTip="Both teams have strong attacking records",
        odds=1.85,
        confidence="high"
    )

    print(f"Pronostic 1: {prono1}")
    print(f"Dict: {prono1.to_dict()}")
    print(f"Is valid: {prono1.is_valid()}")
    print(f"Match key: {prono1.get_match_key()}")

    # Creation avec champs minimaux
    prono2 = Pronostic(
        tipTitle="Over 2.5 Goals",
        tipText="Over 2.5 Goals"
    )

    print(f"\nPronostic 2 (minimal): {prono2}")
    print(f"Is valid: {prono2.is_valid()}")


def test_pronostic_from_dict():
    """Test de creation depuis un dictionnaire"""
    print("\n=== Test de creation depuis dictionnaire ===")

    data = {
        "match": "Arsenal vs Chelsea",
        "dateTime": "2025-12-24T18:00:00",
        "competition": "Premier League",
        "homeTeam": "Arsenal",
        "awayTeam": "Chelsea",
        "tipTitle": "Match Result",
        "tipType": "match_result",
        "tipText": "Arsenal to Win",
        "reasonTip": "Arsenal has home advantage",
        "odds": 2.10,
        "confidence": "medium",
        "extra_field": "This will be ignored"  # Champ non defini dans la classe
    }

    prono = Pronostic.from_dict(data)
    print(f"Pronostic from dict: {prono}")
    print(f"Dict roundtrip: {prono.to_dict()}")


def test_response_creation():
    """Test de creation d'une reponse"""
    print("\n=== Test de creation d'une reponse ===")

    # Reponse de succes
    pronostics = [
        Pronostic(
            match="Team A vs Team B",
            tipTitle="Tip 1",
            tipText="Prediction 1",
            odds=1.50
        ),
        Pronostic(
            match="Team C vs Team D",
            tipTitle="Tip 2",
            tipText="Prediction 2",
            odds=2.00
        )
    ]

    response = PronosticResponse.success_response(pronostics, source="FreeSupertips")
    print(f"Success response: {response}")
    print(f"Dict: {response.to_dict()}")

    # Reponse d'erreur
    error_response = PronosticResponse.error(
        "Timeout lors de la requete",
        source="FootyAccumulators"
    )
    print(f"\nError response: {error_response}")
    print(f"Dict: {error_response.to_dict()}")


def test_response_from_dict():
    """Test de creation d'une reponse depuis un dictionnaire"""
    print("\n=== Test de creation reponse depuis dictionnaire ===")

    data = {
        "success": True,
        "pronostics": [
            {
                "match": "Match 1",
                "tipTitle": "Tip 1",
                "tipText": "Prediction 1",
                "odds": 1.75
            },
            {
                "match": "Match 2",
                "tipTitle": "Tip 2",
                "tipText": "Prediction 2",
                "odds": 2.25
            }
        ],
        "total_pronostics": 2,
        "error_message": None,
        "source": "FreeSupertips"
    }

    response = PronosticResponse.from_dict(data)
    print(f"Response from dict: {response}")
    print(f"Number of pronostics: {len(response.pronostics)}")
    print(f"First pronostic type: {type(response.pronostics[0])}")


async def test_with_real_scraper():
    """Test avec un vrai scraper"""
    print("\n=== Test avec le scraper FreeSupertips ===")

    try:
        from scrapers.pronostic import scrape_freesupertips

        # Scraper avec limite de 3 tips
        result = await scrape_freesupertips(max_tips=3, debug_mode=True)

        # Convertir en PronosticResponse
        pronostics_obj = [Pronostic.from_dict(p) for p in result["pronostics"]]
        response = PronosticResponse(
            success=result["success"],
            pronostics=pronostics_obj,
            total_pronostics=result["total_pronostics"],
            error_message=result["error_message"],
            source="FreeSupertips"
        )

        print(f"\nResponse object: {response}")
        print(f"\nFirst pronostic details:")
        if response.pronostics:
            first = response.pronostics[0]
            print(f"  Match: {first.match}")
            print(f"  DateTime: {first.dateTime}")
            print(f"  Tip: {first.tipText}")
            print(f"  Odds: {first.odds}")
            print(f"  Reason: {first.reasonTip[:100] if first.reasonTip else 'N/A'}...")

        # Verifier que to_dict() fonctionne
        response_dict = response.to_dict()
        print(f"\nResponse as dict keys: {response_dict.keys()}")

    except Exception as e:
        print(f"Erreur lors du test avec scraper: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_pronostic_creation()
    test_pronostic_from_dict()
    test_response_creation()
    test_response_from_dict()

    # Test avec scraper reel (decommenter si necessaire)
    # asyncio.run(test_with_real_scraper())
