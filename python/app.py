"""
API REST pour le scraping web avec Crawl4AI
Utilise FastAPI pour créer une API REST asynchrone
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from scraper import scrape_url
from investing_scraper import scrape_economic_calendar

# Créer l'application FastAPI
app = FastAPI(
    title="Crawl4AI Scraper API",
    description="API REST pour scraper des pages web avec Crawl4AI",
    version="1.0.0"
)


class ScrapeRequest(BaseModel):
    """Modèle de requête pour le scraping"""
    url: HttpUrl
    description: Optional[str] = "URL de la page à scraper"


class ScrapeResponse(BaseModel):
    """Modèle de réponse pour le scraping"""
    success: bool
    url: str
    markdown: Optional[str] = None
    content_length: int
    error_message: Optional[str] = None


class InvestingEvent(BaseModel):
    """Modèle pour un événement économique"""
    time: str
    country: str
    event: str
    actual: str
    forecast: str
    previous: str
    impact: str


class InvestingScrapeRequest(BaseModel):
    """Modèle de requête pour le scraping investing.com"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    countries: Optional[List[int]] = None
    categories: Optional[List[str]] = None
    importance: Optional[List[int]] = None
    timezone: Optional[int] = 58
    time_filter: Optional[str] = "timeOnly"


class InvestingScrapeResponse(BaseModel):
    """Modèle de réponse pour le scraping investing.com"""
    success: bool
    events: List[InvestingEvent]
    date_range: dict
    total_events: int
    error_message: Optional[str] = None


@app.get("/")
async def root():
    """Endpoint racine avec informations sur l'API"""
    return {
        "message": "Crawl4AI Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "GET /scrape": "Scraper une URL via query parameter",
            "POST /scrape": "Scraper une URL via body JSON",
            "GET /scrape/investing": "Scraper le calendrier économique investing.com (GET)",
            "POST /scrape/investing": "Scraper le calendrier économique investing.com (POST)",
            "GET /health": "Vérifier l'état de l'API",
            "GET /docs": "Documentation interactive (Swagger UI)"
        }
    }


@app.get("/health")
async def health():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    return {"status": "healthy", "service": "Crawl4AI Scraper API"}


@app.get("/scrape", response_model=ScrapeResponse)
async def scrape_get(url: str = Query(..., description="URL de la page à scraper")):
    """
    Scraper une page web via GET
    
    Args:
        url: URL de la page à scraper (query parameter)
    
    Returns:
        ScrapeResponse avec le contenu scrapé en markdown
    """
    try:
        result = await scrape_url(url)
        
        if result["success"]:
            return ScrapeResponse(**result)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {result['error_message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_post(request: ScrapeRequest):
    """
    Scraper une page web via POST
    
    Args:
        request: ScrapeRequest contenant l'URL à scraper
    
    Returns:
        ScrapeResponse avec le contenu scrapé en markdown
    """
    try:
        # Convertir HttpUrl en string
        url_str = str(request.url)
        result = await scrape_url(url_str)
        
        if result["success"]:
            return ScrapeResponse(**result)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {result['error_message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@app.get("/scrape/investing", response_model=InvestingScrapeResponse)
async def scrape_investing_get(
    date_from: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    timezone: Optional[int] = Query(58, description="ID du fuseau horaire"),
    time_filter: Optional[str] = Query("timeOnly", description="Filtre temporel")
):
    """
    Scraper le calendrier économique d'investing.com via GET
    
    Args:
        date_from: Date de début au format YYYY-MM-DD
        date_to: Date de fin au format YYYY-MM-DD
        timezone: ID du fuseau horaire (défaut: 58 pour GMT+1)
        time_filter: Filtre temporel (défaut: timeOnly)
    
    Returns:
        InvestingScrapeResponse avec les événements économiques
    """
    try:
        result = await scrape_economic_calendar(
            date_from=date_from,
            date_to=date_to,
            timezone=timezone,
            time_filter=time_filter
        )
        
        if result["success"]:
            # Convertir les événements en modèles Pydantic
            events = [InvestingEvent(**event) for event in result["events"]]
            return InvestingScrapeResponse(
                success=True,
                events=events,
                date_range=result["date_range"],
                total_events=result["total_events"],
                error_message=None
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {result.get('error_message', 'Erreur inconnue')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@app.post("/scrape/investing", response_model=InvestingScrapeResponse)
async def scrape_investing_post(request: InvestingScrapeRequest):
    """
    Scraper le calendrier économique d'investing.com via POST
    
    Args:
        request: InvestingScrapeRequest contenant les filtres de scraping
    
    Returns:
        InvestingScrapeResponse avec les événements économiques
    """
    try:
        result = await scrape_economic_calendar(
            date_from=request.date_from,
            date_to=request.date_to,
            countries=request.countries,
            categories=request.categories,
            importance=request.importance,
            timezone=request.timezone,
            time_filter=request.time_filter
        )
        
        if result["success"]:
            # Convertir les événements en modèles Pydantic
            events = [InvestingEvent(**event) for event in result["events"]]
            return InvestingScrapeResponse(
                success=True,
                events=events,
                date_range=result["date_range"],
                total_events=result["total_events"],
                error_message=None
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {result.get('error_message', 'Erreur inconnue')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

