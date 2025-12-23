"""
Pronostic scrapers package
"""
from .freesupertips import scrape_freesupertips
from .footyaccumulators import scrape_footyaccumulators
from .utils import deduplicate_pronostics

__all__ = [
    "scrape_freesupertips",
    "scrape_footyaccumulators",
    "deduplicate_pronostics"
]
