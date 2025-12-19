"""
API REST pour le scraping web avec Crawl4AI
Utilise FastAPI pour créer une API REST asynchrone
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from scraper import scrape_url

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


@app.get("/")
async def root():
    """Endpoint racine avec informations sur l'API"""
    return {
        "message": "Crawl4AI Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "GET /scrape": "Scraper une URL via query parameter",
            "POST /scrape": "Scraper une URL via body JSON",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

