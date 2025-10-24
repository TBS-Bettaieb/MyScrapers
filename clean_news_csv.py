#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 NEWS CSV AUTO-CLEANER & OPTIMIZER pour MetaTrader 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ce script:
1. Nettoie et optimise votre fichier economic_events.csv
2. Crée automatiquement 4 versions optimisées
3. Les sauvegarde DIRECTEMENT dans Common\Files (partagé entre tous les terminaux)
4. Détecte automatiquement votre installation MT5

✨ NOUVEAU : Utilise le dossier Common\Files par défaut (accessible par tous les terminaux)

Version: 3.0 (Common Files)
Date: Novembre 2024
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Fichier d'entrée (dans le même dossier que ce script)
INPUT_FILE = "output/economic_events.csv"

# Noms des fichiers de sortie
OUTPUT_FILES = {
    'high': 'NewsCalendar_HighOnly.csv',
    'optimized': 'NewsCalendar_Optimized.csv',
    'usd': 'NewsCalendar_USD_Only.csv',
    'complete': 'NewsCalendar_Complete.csv'
}

# Paramètres de filtrage
IMPACTS_HIGH = ['High']
IMPACTS_MEDIUM_HIGH = ['High', 'Medium']
CURRENCIES_MAJOR = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD']

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS DE DÉTECTION MT5
# ═══════════════════════════════════════════════════════════════════════════

def find_mt5_directories():
    """
    Détecte automatiquement les dossiers MetaTrader 5 sur le système.
    PRIORITÉ : Common\Files (partagé entre tous les terminaux)
    
    Retourne une liste de chemins vers Files, avec Common\Files en premier
    """
    mt5_paths = []
    
    # Détection Windows
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            base_path = os.path.join(appdata, 'MetaQuotes', 'Terminal')
            
            # ⭐ PRIORITÉ 1 : Dossier Common\Files (partagé entre TOUS les terminaux)
            common_files = os.path.join(base_path, 'Common', 'Files')
            if os.path.exists(common_files):
                mt5_paths.append(common_files)
                print("   ✅ Dossier Common\\Files trouvé (partagé entre tous les terminaux)")
            
            # PRIORITÉ 2 : Dossiers spécifiques aux terminaux (fallback)
            if os.path.exists(base_path):
                for terminal_id in os.listdir(base_path):
                    # Ignorer le dossier Common (déjà ajouté)
                    if terminal_id == 'Common':
                        continue
                    
                    mql5_files = os.path.join(base_path, terminal_id, 'MQL5', 'Files')
                    if os.path.exists(mql5_files):
                        mt5_paths.append(mql5_files)
    
    # Détection Linux/Wine
    else:
        home = os.path.expanduser('~')
        
        # PRIORITÉ 1 : Dossier Common\Files
        base_wine_path = os.path.join(home, '.wine', 'drive_c', 'users')
        if os.path.exists(base_wine_path):
            for user_dir in os.listdir(base_wine_path):
                common_path = os.path.join(base_wine_path, user_dir, 'AppData', 
                                          'Roaming', 'MetaQuotes', 'Terminal', 'Common', 'Files')
                if os.path.exists(common_path):
                    mt5_paths.append(common_path)
                    print("   ✅ Dossier Common/Files trouvé (partagé)")
                    break
        
        # PRIORITÉ 2 : Autres emplacements
        wine_paths = [
            os.path.join(home, '.wine', 'drive_c', 'users', '*', 'AppData', 
                        'Roaming', 'MetaQuotes', 'Terminal'),
            os.path.join(home, '.wine', 'drive_c', 'Program Files', 'MetaTrader 5', 'MQL5', 'Files'),
            os.path.join(home, '.wine', 'drive_c', 'Program Files (x86)', 'MetaTrader 5', 'MQL5', 'Files')
        ]
        
        for pattern in wine_paths:
            for path in glob.glob(pattern):
                if 'Terminal' in path and 'Common' not in path:
                    try:
                        for terminal_id in os.listdir(path):
                            if terminal_id == 'Common':
                                continue
                            mql5_files = os.path.join(path, terminal_id, 'MQL5', 'Files')
                            if os.path.exists(mql5_files):
                                mt5_paths.append(mql5_files)
                    except (PermissionError, OSError):
                        continue
                elif os.path.exists(path) and 'Common' not in path:
                    mt5_paths.append(path)
    
    return mt5_paths

def select_mt5_directory(mt5_paths):
    """
    Permet à l'utilisateur de sélectionner le bon dossier MT5
    """
    if not mt5_paths:
        return None
    
    # Si Common\Files est le seul ou le premier, l'utiliser automatiquement
    if len(mt5_paths) == 1:
        return mt5_paths[0]
    
    # Si le premier est Common\Files, proposer de l'utiliser par défaut
    if 'Common' in mt5_paths[0]:
        print(f"\n💡 Dossier recommandé : {mt5_paths[0]}")
        print("   (Partagé entre tous les terminaux MT5)")
        
        if len(mt5_paths) > 1:
            use_common = input("\n👉 Utiliser ce dossier ? (O/n): ").strip().lower()
            if use_common in ['', 'o', 'y', 'oui', 'yes']:
                return mt5_paths[0]
    
    print("\n🔍 Plusieurs dossiers MetaTrader 5 disponibles:\n")
    for i, path in enumerate(mt5_paths, 1):
        if 'Common' in path:
            print(f"   {i}. {path} ⭐ [RECOMMANDÉ - Partagé]")
        else:
            print(f"   {i}. {path}")
    
    while True:
        try:
            choice = input(f"\n👉 Choisissez le dossier (1-{len(mt5_paths)}) [1]: ").strip()
            if choice == '':
                choice = '1'
            idx = int(choice) - 1
            if 0 <= idx < len(mt5_paths):
                return mt5_paths[idx]
            else:
                print("❌ Choix invalide, réessayez.")
        except ValueError:
            print("❌ Entrez un numéro valide.")
        except KeyboardInterrupt:
            print("\n\n❌ Opération annulée par l'utilisateur")
            sys.exit(1)

def get_mt5_output_directory():
    """
    Obtient le dossier de sortie MT5 (détection auto + fallback manuel)
    """
    print("\n" + "="*80)
    print("🔍 Recherche du dossier MetaTrader 5...")
    print("="*80)
    
    mt5_paths = find_mt5_directories()
    
    if mt5_paths:
        print(f"\n✅ {len(mt5_paths)} dossier(s) MT5 trouvé(s)!")
        selected_path = select_mt5_directory(mt5_paths)
        if selected_path:
            print(f"\n📁 Dossier sélectionné: {selected_path}")
            if 'Common' in selected_path:
                print("   ⭐ Ce dossier est partagé entre tous vos terminaux MT5")
            return selected_path
    
    # Fallback: demander le chemin manuellement
    print("\n⚠️  Aucune installation MT5 détectée automatiquement.")
    print("\n📝 Veuillez entrer le chemin complet vers le dossier Files")
    print("\n   Option 1 (Recommandé) - Common\\Files :")
    print("   C:\\Users\\VotreNom\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files")
    print("\n   Option 2 - Terminal spécifique :")
    print("   C:\\Users\\VotreNom\\AppData\\Roaming\\MetaQuotes\\Terminal\\[ID]\\MQL5\\Files")
    print("\n   (ou appuyez sur Entrée pour sauvegarder dans le dossier courant)")
    
    manual_path = input("\n👉 Chemin: ").strip()
    
    if manual_path and os.path.exists(manual_path):
        return manual_path
    elif manual_path:
        print(f"\n⚠️  Le chemin n'existe pas: {manual_path}")
        # Proposer de créer le dossier
        create = input("   Voulez-vous créer ce dossier ? (o/N): ").strip().lower()
        if create in ['o', 'y', 'oui', 'yes']:
            try:
                os.makedirs(manual_path, exist_ok=True)
                print(f"   ✅ Dossier créé: {manual_path}")
                return manual_path
            except Exception as e:
                print(f"   ❌ Impossible de créer le dossier: {e}")
        print("   Les fichiers seront sauvegardés dans le dossier courant.")
    
    return os.getcwd()

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS DE NETTOYAGE
# ═══════════════════════════════════════════════════════════════════════════

def load_and_clean_data(input_file):
    """
    Charge et nettoie le fichier CSV d'entrée
    """
    print(f"\n📂 Lecture du fichier: {input_file}")
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"❌ Fichier introuvable: {input_file}")
    
    df = pd.read_csv(input_file)
    print(f"✅ Chargé: {len(df)} lignes")
    
    # Statistiques avant nettoyage
    print(f"\n📊 Statistiques AVANT nettoyage:")
    print(f"   • Total événements: {len(df)}")
    print(f"   • Devises uniques: {df['Currency'].nunique()}")
    if 'Impact' in df.columns:
        print(f"   • Distribution Impact:")
        for impact, count in df['Impact'].value_counts().items():
            print(f"     - {impact}: {count}")
    
    # Nettoyage
    print(f"\n🧹 Nettoyage en cours...")
    initial_count = len(df)
    
    # 1. Supprimer doublons exacts
    df = df.drop_duplicates()
    dup_removed = initial_count - len(df)
    print(f"   ✅ Supprimé {dup_removed} doublons exacts")
    
    # 2. Supprimer lignes avec valeurs manquantes
    before = len(df)
    df = df.dropna(subset=['DateTime', 'Event', 'Currency', 'Impact'])
    print(f"   ✅ Supprimé {before - len(df)} lignes avec valeurs manquantes")
    
    # 3. Supprimer doublons par clé unique
    before = len(df)
    df = df.drop_duplicates(subset=['DateTime', 'Event', 'Currency'])
    print(f"   ✅ Supprimé {before - len(df)} doublons par clé unique")
    
    # 4. Valider dates
    print(f"\n📅 Validation des dates...")
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y-%m-%d %H:%M:%S')
    df = df.sort_values('DateTime')
    print(f"   ✅ Dates validées et triées")
    print(f"   📆 Période: {df['DateTime'].min()} → {df['DateTime'].max()}")
    
    return df

def create_version_high(df):
    """Crée la version HIGH only"""
    df_filtered = df[df['Impact'].isin(IMPACTS_HIGH)]
    df_filtered = df_filtered[df_filtered['Currency'].isin(CURRENCIES_MAJOR)]
    return format_output(df_filtered)

def create_version_optimized(df):
    """Crée la version optimisée (HIGH + MEDIUM)"""
    df_filtered = df[df['Impact'].isin(IMPACTS_MEDIUM_HIGH)]
    df_filtered = df_filtered[df_filtered['Currency'].isin(CURRENCIES_MAJOR)]
    return format_output(df_filtered)

def create_version_usd(df):
    """Crée la version USD only"""
    df_filtered = df[df['Impact'].isin(IMPACTS_MEDIUM_HIGH)]
    df_filtered = df_filtered[df_filtered['Currency'] == 'USD']
    return format_output(df_filtered)

def create_version_complete(df):
    """Crée la version complète"""
    df_filtered = df[df['Currency'].isin(CURRENCIES_MAJOR)]
    return format_output(df_filtered)

def format_output(df):
    """
    Formate le DataFrame au format MT5 (4 colonnes)
    """
    return pd.DataFrame({
        'DateTime': df['DateTime'].dt.strftime('%Y-%m-%d %H:%M'),
        'Currency': df['Currency'],
        'EventName': df['Event'],
        'Impact': df['Impact']
    })

# ═══════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """
    Fonction principale
    """
    print("="*80)
    print("📰 NEWS CSV AUTO-CLEANER & OPTIMIZER pour MetaTrader 5")
    print("   Version 3.0 - Common\\Files Priority")
    print("="*80)
    print(f"⏰ Démarré: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Obtenir le dossier de sortie MT5
        output_dir = get_mt5_output_directory()
        
        # 2. Charger et nettoyer les données
        script_dir = os.path.dirname(os.path.abspath(__file__))
        input_path = os.path.join(script_dir, INPUT_FILE)
        
        df_clean = load_and_clean_data(input_path)
        
        # 3. Créer les 4 versions
        print("\n" + "="*80)
        print("🔧 Création des 4 versions optimisées...")
        print("="*80)
        
        versions = {
            'high': {
                'data': create_version_high(df_clean),
                'desc': 'HIGH only (Ultra-Conservative)',
                'file': OUTPUT_FILES['high']
            },
            'optimized': {
                'data': create_version_optimized(df_clean),
                'desc': 'HIGH + MEDIUM (Recommandé)',
                'file': OUTPUT_FILES['optimized']
            },
            'usd': {
                'data': create_version_usd(df_clean),
                'desc': 'USD only (Focus USD)',
                'file': OUTPUT_FILES['usd']
            },
            'complete': {
                'data': create_version_complete(df_clean),
                'desc': 'Complete (Maximum protection)',
                'file': OUTPUT_FILES['complete']
            }
        }
        
        # 4. Sauvegarder les fichiers
        print("\n💾 Sauvegarde des fichiers dans:")
        print(f"   📁 {output_dir}")
        if 'Common' in output_dir:
            print("   ⭐ Dossier Common - Accessible par TOUS vos terminaux MT5")
        print()
        
        saved_files = []
        for key, version in versions.items():
            output_path = os.path.join(output_dir, version['file'])
            version['data'].to_csv(output_path, index=False)
            
            print(f"   ✅ {version['file']}")
            print(f"      • {len(version['data'])} événements")
            print(f"      • {version['desc']}")
            
            saved_files.append(output_path)
        
        # 5. Afficher le résumé
        print("\n" + "="*80)
        print("✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS!")
        print("="*80)
        
        print(f"\n📊 Résumé:")
        print(f"   • Fichier source: {INPUT_FILE}")
        print(f"   • Événements d'origine: {len(df_clean)} (après nettoyage)")
        print(f"   • Versions créées: 4")
        print(f"   • Dossier de sortie: {output_dir}")
        
        if 'Common' in output_dir:
            print(f"\n   ⭐ AVANTAGE : Dossier Common\\Files")
            print(f"      → Accessible depuis TOUS vos comptes MT5")
            print(f"      → Plus besoin de copier dans chaque terminal")
            print(f"      → Survit aux réinstallations de MT5")
        
        print(f"\n📈 Statistiques par version:")
        for key, version in versions.items():
            impact_dist = version['data']['Impact'].value_counts()
            currency_dist = version['data']['Currency'].value_counts()
            
            print(f"\n   📄 {version['file']} ({len(version['data'])} événements)")
            print(f"      Impact: {', '.join([f'{imp}={count}' for imp, count in impact_dist.items()])}")
            print(f"      Top 3 devises: {', '.join([f'{cur}={count}' for cur, count in currency_dist.head(3).items()])}")
        
        print("\n" + "="*80)
        print("🚀 PROCHAINES ÉTAPES:")
        print("="*80)
        print("\n1. Les fichiers sont dans votre dossier MT5/Files/")
        if 'Common' in output_dir:
            print("   ⭐ Dans Common\\Files → Accessibles par TOUS vos terminaux !")
        print("2. Ouvrez MetaTrader 5 (n'importe quel compte)")
        print("3. Configurez votre EA:")
        print(f'   NewsCSVFile = "{OUTPUT_FILES["optimized"]}";  // Recommandé')
        print("4. Lancez un backtest!")
        
        print("\n💡 Conseil: Utilisez NewsCalendar_Optimized.csv pour commencer")
        print("="*80)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ ERREUR: {e}")
        print(f"\n💡 Assurez-vous que '{INPUT_FILE}' est dans le même dossier que ce script.")
        return 1
        
    except KeyboardInterrupt:
        print("\n\n❌ Opération annulée par l'utilisateur")
        return 1
        
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())