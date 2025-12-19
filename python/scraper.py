"""
Script de scraping web utilisant Crawl4AI
Permet d'extraire le contenu d'une page web en format markdown
"""
import asyncio
import sys
from typing import Dict, Optional
from crawl4ai import AsyncWebCrawler


async def scrape_url(url: str) -> Dict[str, any]:
    """
    Scrape une URL et retourne le contenu en format dictionnaire
    
    Args:
        url: L'URL de la page à scraper
    
    Returns:
        Dictionnaire contenant le résultat du scraping avec:
        - success: bool
        - markdown: str (contenu en markdown)
        - url: str
        - content_length: int
        - error_message: Optional[str]
    """
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            
            if result.success:
                return {
                    "success": True,
                    "markdown": result.markdown,
                    "url": url,
                    "content_length": len(result.markdown),
                    "error_message": None
                }
            else:
                return {
                    "success": False,
                    "markdown": None,
                    "url": url,
                    "content_length": 0,
                    "error_message": result.error_message
                }
                
    except Exception as e:
        return {
            "success": False,
            "markdown": None,
            "url": url,
            "content_length": 0,
            "error_message": str(e)
        }


async def scrape_url_for_cli(url: str) -> None:
    """
    Scrape une URL et affiche le contenu en markdown (pour CLI)
    
    Args:
        url: L'URL de la page à scraper
    """
    print(f"Scraping de l'URL : {url}")
    print("-" * 50)
    
    result = await scrape_url(url)
    
    if result["success"]:
        print("\n=== CONTENU MARKDOWN ===\n")
        print(result["markdown"])
        print("\n" + "=" * 50)
        print(f"\n✓ Scraping réussi !")
        print(f"  - Longueur du contenu : {result['content_length']} caractères")
    else:
        print(f"✗ Erreur lors du scraping : {result['error_message']}")
        sys.exit(1)


def main():
    """Fonction principale"""
    # URL par défaut si aucune URL n'est fournie en argument
    default_url = "https://www.example.com"
    
    # Récupérer l'URL depuis les arguments de ligne de commande
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = default_url
        print(f"Aucune URL fournie, utilisation de l'URL par défaut : {url}\n")
    
    # Exécuter le scraping
    asyncio.run(scrape_url_for_cli(url))


if __name__ == "__main__":
    main()

