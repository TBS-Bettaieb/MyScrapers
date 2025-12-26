"""
Script pour initialiser la base ChromaDB avec les mappings de base
À exécuter une seule fois au démarrage
"""
import requests
import json

# URL du service d'unification
BASE_URL = "http://localhost:8002"


def init_mappings():
    """Initialiser les mappings de base"""

    # Mappings des sports
    sports_mappings = [
        {"original": "calcio", "unified": "football", "type": "sport"},
        {"original": "soccer", "unified": "football", "type": "sport"},
        {"original": "football", "unified": "football", "type": "sport"},
        {"original": "fútbol", "unified": "football", "type": "sport"},
        {"original": "futebol", "unified": "football", "type": "sport"},

        {"original": "basket", "unified": "basketball", "type": "sport"},
        {"original": "basketball", "unified": "basketball", "type": "sport"},
        {"original": "pallacanestro", "unified": "basketball", "type": "sport"},
        {"original": "basket-ball", "unified": "basketball", "type": "sport"},

        {"original": "tennis", "unified": "tennis", "type": "sport"},

        {"original": "hockey", "unified": "hockey", "type": "sport"},
        {"original": "hockey sur glace", "unified": "hockey", "type": "sport"},

        {"original": "rugby", "unified": "rugby", "type": "sport"},

        {"original": "handball", "unified": "handball", "type": "sport"},
        {"original": "hand", "unified": "handball", "type": "sport"},
    ]

    # Mappings des tip types
    tip_mappings = [
        # Match Result
        {"original": "1x2", "unified": "match_result", "type": "tip_type"},
        {"original": "1X2", "unified": "match_result", "type": "tip_type"},
        {"original": "risultato", "unified": "match_result", "type": "tip_type"},
        {"original": "résultat", "unified": "match_result", "type": "tip_type"},
        {"original": "match result", "unified": "match_result", "type": "tip_type"},
        {"original": "match winner", "unified": "match_result", "type": "tip_type"},

        # Home Win
        {"original": "1x2: 1", "unified": "home_win", "type": "tip_type"},
        {"original": "1X2: 1", "unified": "home_win", "type": "tip_type"},
        {"original": "risultato: 1", "unified": "home_win", "type": "tip_type"},
        {"original": "résultat: 1", "unified": "home_win", "type": "tip_type"},
        {"original": "résultat: domicile", "unified": "home_win", "type": "tip_type"},
        {"original": "match result: home", "unified": "home_win", "type": "tip_type"},
        {"original": "match winner: home", "unified": "home_win", "type": "tip_type"},
        {"original": "victoire domicile", "unified": "home_win", "type": "tip_type"},

        # Draw
        {"original": "1x2: x", "unified": "draw", "type": "tip_type"},
        {"original": "1X2: X", "unified": "draw", "type": "tip_type"},
        {"original": "risultato: x", "unified": "draw", "type": "tip_type"},
        {"original": "résultat: nul", "unified": "draw", "type": "tip_type"},
        {"original": "match result: draw", "unified": "draw", "type": "tip_type"},
        {"original": "nul", "unified": "draw", "type": "tip_type"},

        # Away Win
        {"original": "1x2: 2", "unified": "away_win", "type": "tip_type"},
        {"original": "1X2: 2", "unified": "away_win", "type": "tip_type"},
        {"original": "risultato: 2", "unified": "away_win", "type": "tip_type"},
        {"original": "résultat: 2", "unified": "away_win", "type": "tip_type"},
        {"original": "résultat: extérieur", "unified": "away_win", "type": "tip_type"},
        {"original": "match result: away", "unified": "away_win", "type": "tip_type"},
        {"original": "match winner: away", "unified": "away_win", "type": "tip_type"},
        {"original": "victoire extérieur", "unified": "away_win", "type": "tip_type"},

        # Both Teams to Score
        {"original": "btts", "unified": "both_teams_score", "type": "tip_type"},
        {"original": "both teams to score", "unified": "both_teams_score", "type": "tip_type"},
        {"original": "goal/goal", "unified": "both_teams_score", "type": "tip_type"},
        {"original": "gol/gol", "unified": "both_teams_score", "type": "tip_type"},
        {"original": "les deux équipes marquent", "unified": "both_teams_score", "type": "tip_type"},
        {"original": "btts: yes", "unified": "both_teams_score_yes", "type": "tip_type"},
        {"original": "btts: no", "unified": "both_teams_score_no", "type": "tip_type"},

        # Over/Under Goals
        {"original": "over 2.5", "unified": "over_2_5_goals", "type": "tip_type"},
        {"original": "over 2,5", "unified": "over_2_5_goals", "type": "tip_type"},
        {"original": "plus de 2.5 buts", "unified": "over_2_5_goals", "type": "tip_type"},
        {"original": "più di 2.5 gol", "unified": "over_2_5_goals", "type": "tip_type"},

        {"original": "under 2.5", "unified": "under_2_5_goals", "type": "tip_type"},
        {"original": "under 2,5", "unified": "under_2_5_goals", "type": "tip_type"},
        {"original": "moins de 2.5 buts", "unified": "under_2_5_goals", "type": "tip_type"},
        {"original": "meno di 2.5 gol", "unified": "under_2_5_goals", "type": "tip_type"},

        {"original": "over 1.5", "unified": "over_1_5_goals", "type": "tip_type"},
        {"original": "under 1.5", "unified": "under_1_5_goals", "type": "tip_type"},
        {"original": "over 3.5", "unified": "over_3_5_goals", "type": "tip_type"},
        {"original": "under 3.5", "unified": "under_3_5_goals", "type": "tip_type"},

        # Double Chance
        {"original": "double chance", "unified": "double_chance", "type": "tip_type"},
        {"original": "doppia chance", "unified": "double_chance", "type": "tip_type"},
        {"original": "double chance: 1x", "unified": "double_chance_1x", "type": "tip_type"},
        {"original": "double chance: 12", "unified": "double_chance_12", "type": "tip_type"},
        {"original": "double chance: x2", "unified": "double_chance_x2", "type": "tip_type"},
    ]

    # Envoyer les mappings au service
    print("🚀 Initialisation des mappings...")

    print("\n📊 Sports...")
    response = requests.post(
        f"{BASE_URL}/mapping/bulk-add",
        json=sports_mappings
    )
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['added']} sports mappings ajoutés")
        if result['errors']:
            print(f"⚠️  {len(result['errors'])} erreurs")
    else:
        print(f"❌ Erreur: {response.status_code}")

    print("\n🎯 Tip Types...")
    response = requests.post(
        f"{BASE_URL}/mapping/bulk-add",
        json=tip_mappings
    )
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['added']} tip types mappings ajoutés")
        if result['errors']:
            print(f"⚠️  {len(result['errors'])} erreurs")
    else:
        print(f"❌ Erreur: {response.status_code}")

    print("\n✅ Initialisation terminée!")


def test_unification():
    """Tester quelques unifications"""
    print("\n🧪 Tests d'unification...")

    tests = [
        {"text": "calcio", "type": "sport"},
        {"text": "fútbol", "type": "sport"},
        {"text": "basket-ball", "type": "sport"},
        {"text": "1X2: 1", "type": "tip_type"},
        {"text": "BTTS", "type": "tip_type"},
        {"text": "plus de 2.5 buts", "type": "tip_type"},
    ]

    for test in tests:
        response = requests.post(
            f"{BASE_URL}/unify",
            json=test
        )
        if response.status_code == 200:
            result = response.json()
            print(f"  {test['text']:25} → {result['unified']:20} (confidence: {result['confidence']:.2f})")
        else:
            print(f"  ❌ Erreur pour {test['text']}")


if __name__ == "__main__":
    import time

    print("⏳ Attente du démarrage du service (5s)...")
    time.sleep(5)

    # Vérifier que le service est disponible
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Service disponible\n")
            init_mappings()
            test_unification()
        else:
            print("❌ Service non disponible")
    except Exception as e:
        print(f"❌ Impossible de se connecter au service: {e}")
        print("Assurez-vous que le service est démarré (python main.py)")
