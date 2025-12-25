"""
Pronostic scrapers package
"""
from .freesupertips import scrape_freesupertips
from .footyaccumulators import scrape_footyaccumulators
from .assopoker import scrape_assopoker
from .utils import deduplicate_pronostics

__all__ = [
    "scrape_freesupertips",
    "scrape_footyaccumulators",
    "scrape_assopoker",
    "deduplicate_pronostics"
]
