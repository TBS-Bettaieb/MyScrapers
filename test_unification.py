"""
Script de test pour le service d'unification intégré
À exécuter après le démarrage du service
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8001"


def print_test(name: str, passed: bool, details: str = ""):
    """Afficher le résultat d'un test"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"       {details}")


def test_api_root():
    """Test 1: Vérifier que l'API principale répond"""
    print("\n🔍 Test 1: API Root")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("version") == "1.2.0" and
            "/unify/health" in data.get("endpoints", {})
        )

        print_test(
            "API Root accessible",
            passed,
            f"Version: {data.get('version')}, Endpoints: {len(data.get('endpoints', {}))}"
        )
        return passed
    except Exception as e:
        print_test("API Root accessible", False, f"Error: {e}")
        return False


def test_unify_health():
    """Test 2: Vérifier le health check du service d'unification"""
    print("\n🔍 Test 2: Unification Health Check")
    try:
        response = requests.get(f"{BASE_URL}/unify/health", timeout=10)
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("status") == "healthy" and
            data.get("ollama") == "ok" and
            data.get("chromadb") == "ok"
        )

        stats = data.get("stats", {})
        print_test(
            "Unification service healthy",
            passed,
            f"Sports: {stats.get('sports_mappings')}, Tips: {stats.get('tip_types_mappings')}"
        )

        if not passed:
            print(f"       Response: {json.dumps(data, indent=2)}")

        return passed
    except Exception as e:
        print_test("Unification service healthy", False, f"Error: {e}")
        return False


def test_unify_single_sport():
    """Test 3: Unifier un sport"""
    print("\n🔍 Test 3: Unifier un sport (calcio → football)")
    try:
        payload = {
            "text": "calcio",
            "type": "sport",
            "threshold": 0.7
        }

        response = requests.post(
            f"{BASE_URL}/unify",
            json=payload,
            timeout=10
        )
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("unified") == "football" and
            data.get("confidence", 0) >= 0.7 and
            data.get("needs_review") == False
        )

        print_test(
            "Unification sport",
            passed,
            f"{data.get('original')} → {data.get('unified')} (conf: {data.get('confidence'):.2f})"
        )
        return passed
    except Exception as e:
        print_test("Unification sport", False, f"Error: {e}")
        return False


def test_unify_single_tip():
    """Test 4: Unifier un tip type"""
    print("\n🔍 Test 4: Unifier un tip type (1X2: 1 → home_win)")
    try:
        payload = {
            "text": "1X2: 1",
            "type": "tip_type",
            "threshold": 0.7
        }

        response = requests.post(
            f"{BASE_URL}/unify",
            json=payload,
            timeout=10
        )
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("unified") == "home_win" and
            data.get("confidence", 0) >= 0.7 and
            data.get("needs_review") == False
        )

        print_test(
            "Unification tip type",
            passed,
            f"{data.get('original')} → {data.get('unified')} (conf: {data.get('confidence'):.2f})"
        )
        return passed
    except Exception as e:
        print_test("Unification tip type", False, f"Error: {e}")
        return False


def test_unify_bulk():
    """Test 5: Unifier en batch"""
    print("\n🔍 Test 5: Unification batch (N8N workflow)")
    try:
        payload = {
            "items": [
                {"sport": "calcio", "tipText": "BTTS"},
                {"sport": "basket", "tipText": "over 2.5"},
                {"sport": "fútbol", "tipText": "1X2: 1"}
            ],
            "threshold": 0.7
        }

        response = requests.post(
            f"{BASE_URL}/unify/bulk",
            json=payload,
            timeout=15
        )
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("success") == True and
            data.get("total") == 3 and
            len(data.get("items", [])) == 3
        )

        if passed:
            # Vérifier les unifications
            items = data.get("items", [])
            details = []
            for item in items:
                sport_ok = item.get("sport_unified") is not None
                tip_ok = item.get("tipText_unified") is not None
                details.append(
                    f"{item.get('sport')} → {item.get('sport_unified')} | "
                    f"{item.get('tipText')} → {item.get('tipText_unified')}"
                )
        else:
            details = [f"Error in response: {data}"]

        print_test(
            "Unification batch",
            passed,
            f"Processed {data.get('total')} items"
        )

        if passed:
            for detail in details:
                print(f"       - {detail}")

        return passed
    except Exception as e:
        print_test("Unification batch", False, f"Error: {e}")
        return False


def test_get_mappings():
    """Test 6: Récupérer les mappings"""
    print("\n🔍 Test 6: Récupérer les mappings")
    try:
        # Test sports
        response = requests.get(f"{BASE_URL}/unify/mappings/sport", timeout=5)
        sports_data = response.json()

        sports_ok = (
            response.status_code == 200 and
            sports_data.get("type") == "sport" and
            sports_data.get("total", 0) >= 15
        )

        print_test(
            "Get sports mappings",
            sports_ok,
            f"Total: {sports_data.get('total')}"
        )

        # Test tip types
        response = requests.get(f"{BASE_URL}/unify/mappings/tip_type", timeout=5)
        tips_data = response.json()

        tips_ok = (
            response.status_code == 200 and
            tips_data.get("type") == "tip_type" and
            tips_data.get("total", 0) >= 60
        )

        print_test(
            "Get tip types mappings",
            tips_ok,
            f"Total: {tips_data.get('total')}"
        )

        return sports_ok and tips_ok
    except Exception as e:
        print_test("Get mappings", False, f"Error: {e}")
        return False


def test_add_mapping():
    """Test 7: Ajouter un nouveau mapping"""
    print("\n🔍 Test 7: Ajouter un nouveau mapping")
    try:
        payload = {
            "original": "test_sport_unique_12345",
            "unified": "test_unified",
            "type": "sport"
        }

        response = requests.post(
            f"{BASE_URL}/unify/mapping/add",
            json=payload,
            timeout=10
        )
        data = response.json()

        passed = (
            response.status_code == 200 and
            data.get("success") == True
        )

        print_test(
            "Add new mapping",
            passed,
            data.get("message", "")
        )

        # Vérifier que le mapping a été ajouté
        if passed:
            time.sleep(1)  # Attendre que ChromaDB indexe
            verify_response = requests.post(
                f"{BASE_URL}/unify",
                json={"text": "test_sport_unique_12345", "type": "sport"},
                timeout=10
            )
            verify_data = verify_response.json()

            verified = verify_data.get("unified") == "test_unified"
            print_test(
                "Verify new mapping",
                verified,
                f"test_sport_unique_12345 → {verify_data.get('unified')}"
            )

            return verified

        return passed
    except Exception as e:
        print_test("Add new mapping", False, f"Error: {e}")
        return False


def run_all_tests():
    """Exécuter tous les tests"""
    print("=" * 60)
    print("🧪 TESTS DU SERVICE D'UNIFICATION INTÉGRÉ")
    print("=" * 60)

    # Vérifier que le service est accessible
    print("\n⏳ Vérification de la disponibilité du service...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Le service principal n'est pas accessible")
            print(f"   Assurez-vous que le service est démarré sur {BASE_URL}")
            return
        print("✅ Service principal accessible")
    except Exception as e:
        print(f"❌ Impossible de se connecter à {BASE_URL}")
        print(f"   Error: {e}")
        print("\n💡 Actions à faire :")
        print("   1. Démarrer le service : python -m uvicorn app:app --host 0.0.0.0 --port 8001")
        print("   2. Ou avec Docker : docker-compose up -d")
        print("   3. Configurer OLLAMA_URL vers votre serveur Ollama privé")
        return

    # Exécuter les tests
    results = []

    results.append(("API Root", test_api_root()))
    results.append(("Unification Health", test_unify_health()))
    results.append(("Unify Single Sport", test_unify_single_sport()))
    results.append(("Unify Single Tip", test_unify_single_tip()))
    results.append(("Unify Bulk", test_unify_bulk()))
    results.append(("Get Mappings", test_get_mappings()))
    results.append(("Add Mapping", test_add_mapping()))

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print("\n" + "=" * 60)
    print(f"Résultat: {passed}/{total} tests passés ({passed/total*100:.0f}%)")
    print("=" * 60)

    if passed == total:
        print("\n🎉 Tous les tests sont passés ! Le service d'unification fonctionne parfaitement.")
        print("\n✅ Prochaines étapes :")
        print("   1. Configurer N8N pour utiliser POST /unify/bulk")
        print("   2. Tester avec vos données réelles de pronostics")
        print("   3. Ajouter des mappings personnalisés si nécessaire")
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")
        print("\n💡 Vérifications :")
        print("   1. Le serveur Ollama est-il accessible ?")
        print("   2. Le modèle nomic-embed-text est-il installé ?")
        print("   3. La variable OLLAMA_URL est-elle correcte ?")
        print("   4. ChromaDB a-t-il les permissions d'écriture ?")


if __name__ == "__main__":
    run_all_tests()
