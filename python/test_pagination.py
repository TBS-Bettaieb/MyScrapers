import asyncio
import sys
import json
from investing_scraper import get_cookies, make_api_request

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def test_pagination():
    """Test pour comprendre la structure de pagination de l'API"""
    print("🔍 TEST DE PAGINATION")
    print("="*70 + "\n")

    # Récupérer les cookies
    cookies = get_cookies(cache=True)

    # Faire une requête avec limit_from=0
    print("📡 Requête 1: limit_from=0")
    response = await make_api_request(
        cookies=cookies,
        date_from="2025-12-20",
        date_to="2026-01-19",
        debug_mode=True
    )

    if response:
        print(f"\n📊 Structure de la réponse:")
        print(f"   Type: {type(response)}")
        print(f"   Clés: {list(response.keys())}")

        # Sauvegarder la réponse complète pour analyse
        with open('response_structure.json', 'w', encoding='utf-8') as f:
            # Ne pas sauvegarder le HTML complet, juste la structure
            response_copy = response.copy()
            if 'data' in response_copy:
                response_copy['data'] = f"<HTML de {len(response_copy['data'])} caractères>"
            json.dump(response_copy, f, indent=2, ensure_ascii=False)

        print(f"\n   Réponse sauvegardée dans response_structure.json")

        # Vérifier s'il y a des indicateurs de pagination
        for key, value in response.items():
            if key != 'data':
                print(f"   {key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_pagination())
