"""
API REST pour le scraping du calendrier économique investing.com et des pronostics sportifs
Utilise FastAPI pour créer une API REST asynchrone
"""
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Optional, List, Dict, Any
from investing_scraper import scrape_economic_calendar
from pronostic_scraper import scrape_footyaccumulators, scrape_freesupertips

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title="MyScrapers API",
    description="API REST pour scraper le calendrier économique d'investing.com et les pronostics sportifs",
    version="1.1.0"
)


class InvestingEvent(BaseModel):
    """Modèle pour un événement économique"""
    time: str = ""
    datetime: Optional[str] = None
    parsed_datetime: Optional[str] = None
    day: Optional[str] = None
    country: str = ""
    country_code: Optional[str] = None
    event: str = ""
    event_url: Optional[str] = None
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    impact: str = ""
    event_id: Optional[str] = None


class InvestingScrapeRequest(BaseModel):
    """Modèle de requête pour le scraping investing.com"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    countries: Optional[List[int]] = None
    categories: Optional[List[str]] = None
    importance: Optional[List[int]] = None
    timezone: Optional[int] = 55
    time_filter: Optional[str] = "timeOnly"


class InvestingHoliday(BaseModel):
    """Modèle pour un jour férié"""
    type: str = "holiday"
    time: str = ""
    day: Optional[str] = None
    country: str = ""
    event: str = ""
    impact: str = "Holiday"


class InvestingScrapeResponse(BaseModel):
    """Modèle de réponse pour le scraping investing.com"""
    success: bool
    events: List[InvestingEvent]
    holidays: List[InvestingHoliday]
    date_range: dict
    total_events: int
    total_holidays: int
    error_message: Optional[str] = None


@app.get("/")
async def root():
    """Endpoint racine avec informations sur l'API"""
    return {
        "message": "MyScrapers API - Economic Calendar & Sports Betting Tips",
        "version": "1.1.0",
        "endpoints": {
            "GET /scrape/investing": "Scraper le calendrier économique investing.com (GET)",
            "POST /scrape/investing": "Scraper le calendrier économique investing.com (POST)",
            "GET /scrape/footyaccumulators": "Scraper les pronostics FootyAccumulators",
            "GET /scrape/freesupertips": "Scraper les pronostics FreeSupertips",
            "GET /health": "Vérifier l'état de l'API",
            "GET /docs": "Documentation interactive (Swagger UI)"
        }
    }


@app.get("/health")
async def health():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    return {"status": "healthy", "service": "MyScrapers API"}


@app.get("/scrape/investing", response_model=InvestingScrapeResponse)
async def scrape_investing_get(
    date_from: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    timezone: Optional[int] = Query(55, description="ID du fuseau horaire"),
    time_filter: Optional[str] = Query("timeOnly", description="Filtre temporel")
):
    """
    Scraper le calendrier économique d'investing.com via GET
    
    Args:
        date_from: Date de début au format YYYY-MM-DD
        date_to: Date de fin au format YYYY-MM-DD
        timezone: ID du fuseau horaire (défaut: 55 pour UTC)
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
        
        logger.info(f"Scraping result: success={result.get('success')}, total_events={result.get('total_events', 0)}")
        
        if result["success"]:
            # Séparer les événements économiques des jours fériés
            events = []
            holidays = []

            for event in result["events"]:
                try:
                    # Vérifier si c'est un jour férié
                    if event.get("type") == "holiday" or event.get("impact") == "Holiday":
                        # C'est un jour férié
                        holiday_data = {
                            "type": "holiday",
                            "time": event.get("time", ""),
                            "day": event.get("day"),
                            "country": event.get("country", ""),
                            "event": event.get("event", ""),
                            "impact": "Holiday"
                        }
                        holidays.append(InvestingHoliday(**holiday_data))
                    else:
                        # C'est un événement économique
                        event_data = {
                            "time": event.get("time", ""),
                            "datetime": event.get("datetime"),
                            "parsed_datetime": event.get("parsed_datetime"),
                            "day": event.get("day"),
                            "country": event.get("country", ""),
                            "country_code": event.get("country_code"),
                            "event": event.get("event", ""),
                            "event_url": event.get("event_url"),
                            "actual": event.get("actual", ""),
                            "forecast": event.get("forecast", ""),
                            "previous": event.get("previous", ""),
                            "impact": event.get("impact", ""),
                            "event_id": event.get("event_id")
                        }
                        events.append(InvestingEvent(**event_data))
                except ValidationError as e:
                    logger.error(f"Erreur de validation pour l'événement: {event}, erreur: {e}")
                    # Continuer avec les autres événements même si un échoue
                    continue
                except Exception as e:
                    logger.error(f"Erreur lors de la conversion de l'événement: {event}, erreur: {str(e)}")
                    continue

            if not events and not holidays:
                raise HTTPException(
                    status_code=400,
                    detail="Aucun événement ou jour férié valide n'a pu être converti"
                )

            return InvestingScrapeResponse(
                success=True,
                events=events,
                holidays=holidays,
                date_range=result["date_range"],
                total_events=len(events),
                total_holidays=len(holidays),
                error_message=None
            )
        else:
            error_msg = result.get('error_message', 'Erreur inconnue')
            logger.error(f"Scraping échoué: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {error_msg}"
            )
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Erreur de validation Pydantic: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Erreur de validation des données: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur serveur: {str(e)}", exc_info=True)
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
            # Séparer les événements économiques des jours fériés
            events = []
            holidays = []

            for event in result["events"]:
                try:
                    # Vérifier si c'est un jour férié
                    if event.get("type") == "holiday" or event.get("impact") == "Holiday":
                        # C'est un jour férié
                        holiday_data = {
                            "type": "holiday",
                            "time": event.get("time", ""),
                            "day": event.get("day"),
                            "country": event.get("country", ""),
                            "event": event.get("event", ""),
                            "impact": "Holiday"
                        }
                        holidays.append(InvestingHoliday(**holiday_data))
                    else:
                        # C'est un événement économique
                        events.append(InvestingEvent(**event))
                except ValidationError as e:
                    logger.error(f"Erreur de validation pour l'événement: {event}, erreur: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Erreur lors de la conversion de l'événement: {event}, erreur: {str(e)}")
                    continue

            return InvestingScrapeResponse(
                success=True,
                events=events,
                holidays=holidays,
                date_range=result["date_range"],
                total_events=len(events),
                total_holidays=len(holidays),
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


# =============================================================================
# ENDPOINTS POUR PRONOSTICS SPORTIFS
# =============================================================================

class PronosticTip(BaseModel):
    """Modèle pour un pronostic sportif simplifié"""
    match: Optional[str] = None
    dateTime: Optional[str] = None
    competition: Optional[str] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None
    tipTitle: str
    tipType: Optional[str] = None
    tipText: Optional[str] = None
    reasonTip: Optional[str] = None
    odds: Optional[float] = None
    confidence: Optional[str] = None

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "match": "Arsenal vs Chelsea",
                "reasonTip": "Arsenal have won their last 3 matches..."
            }
        }
    }


class PronosticResponse(BaseModel):
    """Modèle de réponse pour les pronostics sportifs"""
    success: bool
    pronostics: List[PronosticTip]
    total_pronostics: int
    error_message: Optional[str] = None


@app.get("/scrape/footyaccumulators")
async def scrape_footyaccumulators_endpoint(
    max_tips: Optional[int] = Query(None, description="Nombre maximum de pronostics à récupérer"),
    debug: Optional[bool] = Query(False, description="Active les logs détaillés")
):
    """
    Scraper les pronostics de FootyAccumulators

    Args:
        max_tips: Nombre maximum de pronostics à récupérer (None = tous)
        debug: Active les logs détaillés

    Returns:
        PronosticResponse avec la liste des pronostics
    """
    try:
        result = await scrape_footyaccumulators(
            max_tips=max_tips,
            debug_mode=debug
        )

        logger.info(f"FootyAccumulators scraping: success={result.get('success')}, total={result.get('total_pronostics', 0)}")

        if result["success"]:
            # Retourner directement le dictionnaire pour éviter la sérialisation Pydantic
            return JSONResponse(content={
                "success": True,
                "pronostics": result["pronostics"],
                "total_pronostics": result["total_pronostics"],
                "error_message": None
            })
        else:
            error_msg = result.get('error_message', 'Erreur inconnue')
            logger.error(f"FootyAccumulators scraping échoué: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {error_msg}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur serveur FootyAccumulators: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@app.get("/scrape/freesupertips")
async def scrape_freesupertips_endpoint(
    max_tips: Optional[int] = Query(None, description="Nombre maximum de pronostics à récupérer"),
    debug: Optional[bool] = Query(False, description="Active les logs détaillés")
):
    """
    Scraper les pronostics de FreeSupertips

    Args:
        max_tips: Nombre maximum de pronostics à récupérer (None = tous)
        debug: Active les logs détaillés

    Returns:
        PronosticResponse avec la liste des pronostics
    """
    try:
        result = await scrape_freesupertips(
            max_tips=max_tips,
            debug_mode=debug
        )

        logger.info(f"FreeSupertips scraping: success={result.get('success')}, total={result.get('total_pronostics', 0)}")

        if result["success"]:
            # Retourner directement le dictionnaire pour éviter la sérialisation Pydantic
            return JSONResponse(content={
                "success": True,
                "pronostics": result["pronostics"],
                "total_pronostics": result["total_pronostics"],
                "error_message": None
            })
        else:
            error_msg = result.get('error_message', 'Erreur inconnue')
            logger.error(f"FreeSupertips scraping échoué: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors du scraping: {error_msg}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur serveur FreeSupertips: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

