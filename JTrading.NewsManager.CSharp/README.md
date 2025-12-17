# JTrading News Manager - Version C# .NET 8

Migration complète du projet Python vers C# .NET 8 Console Application.

## Structure du projet

```
JTrading-News-Manager/
├── JTrading.NewsManager.CSharp/      # Dossier du projet C#
│   ├── src/
│   │   ├── Models/
│   │   │   └── EconomicEvent.cs          # Modèle de données
│   │   ├── Services/
│   │   │   ├── InvestingComScraper.cs    # Scraper Investing.com
│   │   │   ├── SymbolMapper.cs           # Mapping devises -> paires trading
│   │   │   ├── CsvExporter.cs            # Export CSV
│   │   │   ├── PipelineRunner.cs         # Pipeline principal
│   │   │   └── NewsScheduler.cs          # Scheduler quotidien
│   │   ├── Configuration/
│   │   │   ├── AppConfig.cs              # Classes de configuration
│   │   │   └── ConfigLoader.cs           # Chargeur de configuration
│   │   ├── Logging/
│   │   │   └── FileLoggerProvider.cs     # Logger fichier
│   │   ├── Program.cs                    # Point d'entrée principal
│   │   └── SchedulerProgram.cs           # Point d'entrée scheduler
│   ├── JTrading-News-Manager.sln     # Solution Visual Studio
│   ├── JTrading.NewsManager.csproj   # Fichier projet .NET
│   └── README.md                      # Ce fichier
├── config/                            # Config partagée (référencée depuis C#)
│   └── config.json
├── output/                            # Output partagé
└── logs/                              # Logs partagés
```

## Dépendances NuGet

- `HtmlAgilityPack` (1.11.69) - Parsing HTML
- `CsvHelper` (33.0.1) - Lecture/écriture CSV
- `Microsoft.Extensions.Logging` (8.0.0) - Logging
- `Microsoft.Extensions.Logging.Console` (8.0.0) - Console logging
- `System.CommandLine` (2.0.0-beta4) - Arguments CLI
- `Microsoft.Extensions.Http` (8.0.0) - HTTP client

## Installation

1. **Prérequis** : .NET 8 SDK installé

2. **Naviguer dans le dossier du projet** :
   ```bash
   cd JTrading.NewsManager.CSharp
   ```

3. **Restaurer les packages NuGet** :
   ```bash
   dotnet restore
   ```

4. **Compiler le projet** :
   ```bash
   dotnet build
   ```

## Utilisation

### Exécution principale

#### Mode Daily (une seule date)
```bash
# Depuis le dossier JTrading.NewsManager.CSharp
# Scrape aujourd'hui
dotnet run -- --mode daily

# Scrape une date spécifique
dotnet run -- --mode daily --date 2025-01-15
```

#### Mode Range (plage de dates)
```bash
# Mode range avec config par défaut
dotnet run -- --mode range

# Mode test (1 mois seulement)
dotnet run -- --test

# Scrape seulement, sans exporter
dotnet run -- --scrape-only
```

### Scheduler (exécution quotidienne)

```bash
# Depuis le dossier JTrading.NewsManager.CSharp
# Démarrer le scheduler (exécution quotidienne à l'heure configurée)
dotnet run --project src/SchedulerProgram.cs -- 

# Exécuter une fois immédiatement
dotnet run --project src/SchedulerProgram.cs -- --run-once

# Avec config personnalisée (chemin relatif au dossier parent)
dotnet run --project src/SchedulerProgram.cs -- --config ../config/config.json
```

## Configuration

Le fichier `config/config.json` utilise le même format que la version Python :

```json
{
  "scheduler": {
    "run_time": "06:00",
    "timezone": "local"
  },
  "output": {
    "csv_path": "output/economic_events.csv"
  },
  "symbol_mapping": {
    "auto_mapping": {
      "USD": ["EURUSD", "GBPUSD", "USDJPY", ...],
      ...
    },
    "custom_overrides": {
      "CNY": ["USDCNH", "EURCNH"]
    }
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "investing_com": {
    "enabled": true,
    "default_mode": "range",
    "months_back": 11,
    "months_forward": 0,
    "base_url": "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
    "countries": [25, 32, 6, 37, ...],
    "timezone": 55,
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

## Comparaison avec la version Python

| Fonctionnalité | Python | C# |
|----------------|--------|-----|
| Scraping Investing.com | ✅ | ✅ |
| Parsing HTML/JSON | BeautifulSoup | HtmlAgilityPack |
| Export CSV | pandas | CsvHelper |
| Mapping symboles | ✅ | ✅ |
| Déduplication | pandas | LINQ |
| Scheduler | schedule | Timer |
| Logging | logging | Microsoft.Extensions.Logging |
| Configuration | JSON | JSON (même format) |

## Architecture

### Pipeline de traitement

1. **InvestingComScraper** : Scrape les événements depuis l'API Investing.com
2. **SymbolMapper** : Mappe les devises aux paires de trading affectées
3. **CsvExporter** : Exporte les événements vers CSV avec déduplication
4. **PipelineRunner** : Orchestre le pipeline complet

### Modes d'exécution

- **Daily** : Scrape une seule date, append au CSV existant
- **Range** : Scrape une plage de dates, merge avec déduplication

## Notes de migration

- Toutes les opérations HTTP sont async (HttpClient)
- Le parsing HTML utilise HtmlAgilityPack au lieu de BeautifulSoup
- La déduplication utilise LINQ au lieu de pandas
- Le logging utilise Microsoft.Extensions.Logging
- La configuration utilise System.Text.Json

## Compatibilité

- Le format CSV généré est identique à la version Python
- Le format de configuration JSON est identique
- Les logs ont le même format

