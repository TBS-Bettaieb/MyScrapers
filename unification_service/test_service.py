"""
Script de test pour le service d'unification
"""
import requests
import json
from typing import List, Dict


BASE_URL = "http://localhost:8002"


def print_section(title: str):
    """Afficher un titre de section"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def test_health():
    """Test 1 : Health check"""
    print_section("TEST 1 : Health Check")

    response = requests.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Service disponible")
        print(f"   Status: {data['status']}")
        print(f"   Sports mappings: {data['stats']['sports_mappings']}")
        print(f"   TipTypes mappings: {data['stats']['tip_types_mappings']}")
        return True
    else:
        print(f"❌ Service non disponible (status: {response.status_code})")
        return False


def test_unify_sport():
    """Test 2 : Unification de sports"""
    print_section("TEST 2 : Unification Sports")

    tests = [
        {"text": "calcio", "expected": "football"},
        {"text": "soccer", "expected": "football"},
        {"text": "fútbol", "expected": "football"},
        {"text": "basket-ball", "expected": "basketball"},
        {"text": "pallacanestro", "expected": "basketball"},
    ]

    success = 0
    for test in tests:
        response = requests.post(
            f"{BASE_URL}/unify",
            json={"text": test["text"], "type": "sport"}
        )

        if response.status_code == 200:
            result = response.json()
            if result["unified"] == test["expected"]:
                print(f"✅ {test['text']:20} → {result['unified']:15} (confidence: {result['confidence']:.2f})")
                success += 1
            else:
                print(f"❌ {test['text']:20} → {result['unified']:15} (attendu: {test['expected']})")
        else:
            print(f"❌ Erreur pour {test['text']} (status: {response.status_code})")

    print(f"\n📊 Résultat: {success}/{len(tests)} tests réussis")
    return success == len(tests)


def test_unify_tip_types():
    """Test 3 : Unification de tip types"""
    print_section("TEST 3 : Unification Tip Types")

    tests = [
        {"text": "1X2: 1", "expected": "home_win"},
        {"text": "résultat: domicile", "expected": "home_win"},
        {"text": "BTTS", "expected": "both_teams_score"},
        {"text": "plus de 2.5 buts", "expected": "over_2_5_goals"},
        {"text": "under 2.5", "expected": "under_2_5_goals"},
    ]

    success = 0
    for test in tests:
        response = requests.post(
            f"{BASE_URL}/unify",
            json={"text": test["text"], "type": "tip_type"}
        )

        if response.status_code == 200:
            result = response.json()
            if result["unified"] == test["expected"]:
                print(f"✅ {test['text']:25} → {result['unified']:25} (confidence: {result['confidence']:.2f})")
                success += 1
            else:
                print(f"⚠️  {test['text']:25} → {result['unified']:25} (attendu: {test['expected']}, confidence: {result['confidence']:.2f})")
        else:
            print(f"❌ Erreur pour {test['text']} (status: {response.status_code})")

    print(f"\n📊 Résultat: {success}/{len(tests)} tests réussis")
    return success == len(tests)


def test_bulk_unification():
    """Test 4 : Unification en batch"""
    print_section("TEST 4 : Unification Batch")

    pronostics = [
        {
            "id": "test_1",
            "sport": "calcio",
            "tipText": "1X2: 1",
            "match": "Monaco - PSG"
        },
        {
            "id": "test_2",
            "sport": "basket",
            "tipText": "over 2.5",
            "match": "Lakers - Celtics"
        },
        {
            "id": "test_3",
            "sport": "tennis",
            "tipText": "match winner: home",
            "match": "Nadal - Federer"
        }
    ]

    response = requests.post(
        f"{BASE_URL}/unify/bulk",
        json={"items": pronostics, "threshold": 0.7}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Batch processing réussi")
        print(f"   Total items: {result['total']}")

        for item in result["items"]:
            print(f"\n   {item['match']}")
            print(f"      Sport: {item['sport']} → {item['sport_unified']} (confidence: {item['sport_confidence']:.2f})")
            print(f"      Tip:   {item['tipText']} → {item['tipText_unified']} (confidence: {item['tipText_confidence']:.2f})")

            if item.get('sport_needs_review') or item.get('tipText_needs_review'):
                print(f"      ⚠️  Besoin de validation")

        return True
    else:
        print(f"❌ Erreur (status: {response.status_code})")
        return False


def test_add_mapping():
    """Test 5 : Ajouter un nouveau mapping"""
    print_section("TEST 5 : Ajout de mapping")

    # Ajouter un nouveau sport
    response = requests.post(
        f"{BASE_URL}/mapping/add",
        json={
            "original": "foot",
            "unified": "football",
            "type": "sport"
        }
    )

    if response.status_code == 200:
        print("✅ Mapping ajouté: foot → football")

        # Tester immédiatement
        test_response = requests.post(
            f"{BASE_URL}/unify",
            json={"text": "foot", "type": "sport"}
        )

        if test_response.status_code == 200:
            result = test_response.json()
            if result["unified"] == "football":
                print(f"✅ Vérification: foot → {result['unified']} (confidence: {result['confidence']:.2f})")
                return True
            else:
                print(f"❌ Vérification échouée: attendu 'football', reçu '{result['unified']}'")
        else:
            print(f"❌ Erreur de vérification (status: {test_response.status_code})")
    else:
        print(f"❌ Erreur d'ajout (status: {response.status_code})")

    return False


def test_get_all_mappings():
    """Test 6 : Récupérer tous les mappings"""
    print_section("TEST 6 : Récupération des mappings")

    # Sports
    response = requests.get(f"{BASE_URL}/mappings/sport")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sports mappings: {data['total']}")
        print(f"   Exemples: {', '.join([m['original'] for m in data['mappings'][:5]])}")
    else:
        print(f"❌ Erreur (status: {response.status_code})")
        return False

    # Tip Types
    response = requests.get(f"{BASE_URL}/mappings/tip_type")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Tip Types mappings: {data['total']}")
        print(f"   Exemples: {', '.join([m['original'] for m in data['mappings'][:5]])}")
        return True
    else:
        print(f"❌ Erreur (status: {response.status_code})")
        return False


def main():
    """Exécuter tous les tests"""
    print("\n" + "="*60)
    print("  🧪 TESTS DU SERVICE D'UNIFICATION")
    print("="*60)

    tests = [
        ("Health Check", test_health),
        ("Unification Sports", test_unify_sport),
        ("Unification Tip Types", test_unify_tip_types),
        ("Unification Batch", test_bulk_unification),
        ("Ajout mapping", test_add_mapping),
        ("Récupération mappings", test_get_all_mappings),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Erreur lors du test '{name}': {e}")
            results.append((name, False))

    # Résumé
    print_section("RÉSUMÉ DES TESTS")

    success_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {name}")

    print(f"\n📊 Score final: {success_count}/{total_count} tests réussis")

    if success_count == total_count:
        print("\n🎉 Tous les tests sont passés !")
        return True
    else:
        print(f"\n⚠️  {total_count - success_count} test(s) échoué(s)")
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrompus")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
