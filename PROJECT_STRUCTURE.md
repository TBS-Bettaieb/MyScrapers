# Project Structure

## Overview

This project has been reorganized into a clean, modular structure following Python best practices.

## Directory Structure

```
MyScrapers/
├── app.py                      # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose configuration
│
├── scrapers/                   # Scrapers package
│   ├── __init__.py
│   ├── investing_scraper.py    # Investing.com calendar scraper
│   └── pronostic/              # Sports betting tips scrapers
│       ├── __init__.py
│       ├── freesupertips.py    # FreeSupertips scraper
│       ├── footyaccumulators.py # FootyAccumulators scraper
│       └── utils.py            # Shared utilities (deduplication, etc.)
│
├── models/                     # Data models
│   ├── __init__.py
│   └── pronostic.py            # Pronostic dataclasses (Pronostic, PronosticResponse)
│
├── tests/                      # Test files
│   ├── __init__.py
│   └── test_pronostic_models.py # Unit tests for pronostic models
│
├── docs/                       # Documentation
│   └── pronostic_models.md     # Documentation for pronostic models
│
├── deployment/                 # Deployment files
│   ├── deploy.sh
│   ├── backup.sh
│   └── monitor.sh
│
└── examples/                   # Example usage
    └── pronosticsExemples/
```

## Key Components

### 1. Scrapers (`scrapers/`)

All web scraping logic is organized by data source:

- **`investing_scraper.py`**: Scrapes economic calendar from Investing.com
- **`pronostic/`**: Sports betting tips scrapers
  - `freesupertips.py`: FreeSupertips scraper
  - `footyaccumulators.py`: FootyAccumulators scraper
  - `utils.py`: Shared utilities (deduplication logic)

**Usage:**
```python
from scrapers.investing_scraper import scrape_economic_calendar
from scrapers.pronostic import scrape_freesupertips, scrape_footyaccumulators

# Use the scrapers
result = await scrape_freesupertips(max_tips=10, debug_mode=True)
```

### 2. Models (`models/`)

Dataclasses for type-safe data structures:

- **`pronostic.py`**: Contains `Pronostic` and `PronosticResponse` dataclasses

**Usage:**
```python
from models import Pronostic, PronosticResponse

# Create a typed pronostic
prono = Pronostic(
    match="Team A vs Team B",
    tipText="Team A to Win",
    odds=1.85
)

# Create a response
response = PronosticResponse.success_response(
    pronostics=[prono],
    source="FreeSupertips"
)
```

### 3. Tests (`tests/`)

Unit tests for the project:

- **`test_pronostic_models.py`**: Tests for pronostic models

**Run tests:**
```bash
python tests/test_pronostic_models.py
```

### 4. Documentation (`docs/`)

Project documentation:

- **`pronostic_models.md`**: Complete guide for using pronostic models

## API Endpoints

The FastAPI application (`app.py`) exposes the following endpoints:

### Economic Calendar
- `GET /scrape/investing` - Scrape Investing.com economic calendar

### Sports Betting Tips
- `GET /scrape/freesupertips` - Scrape FreeSupertips
- `GET /scrape/footyaccumulators` - Scrape FootyAccumulators

### Health
- `GET /health` - API health check
- `GET /` - API information

## Development

### Running locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

### Running with Docker
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

## Benefits of This Structure

1. **Modularity**: Each scraper is in its own file, easy to maintain
2. **Type Safety**: Dataclasses provide type checking and validation
3. **Testability**: Separate tests directory with unit tests
4. **Documentation**: Centralized documentation in docs/
5. **Clean Imports**: Well-organized packages with clear namespaces
6. **Scalability**: Easy to add new scrapers or models

## Migration Notes

### Old Structure → New Structure

- `investing_scraper.py` → `scrapers/investing_scraper.py`
- `pronostic_scraper.py` → Split into:
  - `scrapers/pronostic/freesupertips.py`
  - `scrapers/pronostic/footyaccumulators.py`
  - `scrapers/pronostic/utils.py`
- `models.py` → `models/pronostic.py`
- `test_models.py` → `tests/test_pronostic_models.py`
- `MODELS_README.md` → `docs/pronostic_models.md`

### Import Changes

**Old:**
```python
from investing_scraper import scrape_economic_calendar
from pronostic_scraper import scrape_freesupertips
from models import Pronostic
```

**New:**
```python
from scrapers.investing_scraper import scrape_economic_calendar
from scrapers.pronostic import scrape_freesupertips
from models import Pronostic
```
