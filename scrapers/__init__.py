"""
Scrapers package for MyScrapers
"""
from .investing_scraper import scrape_economic_calendar
from .pronostic import scrape_freesupertips, scrape_footyaccumulators

__all__ = [
    "scrape_economic_calendar",
    "scrape_freesupertips",
    "scrape_footyaccumulators"
]
