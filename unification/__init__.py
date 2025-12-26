"""
Module d'unification pour sports et tip types
Utilise Ollama + ChromaDB pour la recherche sémantique
"""
import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import ollama
import chromadb
from pathlib import Path

from .mappings import SPORTS_MAPPINGS, TIP_TYPES_MAPPINGS

logger = logging.getLogger(__name__)

# Configuration Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")

# Configuration ChromaDB
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "./chroma_db"))

# Collections globales (initialisées au startup)
sports_collection = None
tips_collection = None
chroma_client = None


# ============ Modèles Pydantic ============

class UnificationRequest(BaseModel):
    text: str
    type: str  # "sport" ou "tip_type"
    threshold: Optional[float] = 0.7


class UnificationResponse(BaseModel):
    original: str
    unified: str
    confidence: float
    needs_review: bool


class MappingRequest(BaseModel):
    original: str
    unified: str
    type: str  # "sport" ou "tip_type"


class BulkUnificationRequest(BaseModel):
    items: List[dict]  # [{"sport": "calcio", "tipText": "1X2: 1"}]
    threshold: Optional[float] = 0.7


# ============ Fonctions d'initialisation ============

def init_chromadb():
    """Initialiser ChromaDB et créer les collections"""
    global chroma_client, sports_collection, tips_collection

    try:
        # Créer le répertoire si nécessaire
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        # Initialiser le client ChromaDB
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        # Créer les collections
        sports_collection = chroma_client.get_or_create_collection("sports")
        tips_collection = chroma_client.get_or_create_collection("tip_types")

        logger.info(f"✅ ChromaDB initialized at {CHROMA_PATH}")
        logger.info(f"   - Sports mappings: {sports_collection.count()}")
        logger.info(f"   - Tip types mappings: {tips_collection.count()}")

        return {
            "sports": sports_collection,
            "tips": tips_collection
        }
    except Exception as e:
        logger.error(f"❌ Error initializing ChromaDB: {e}")
        raise


async def load_initial_mappings():
    """Charger les mappings de base si ChromaDB est vide"""
    global sports_collection, tips_collection

    try:
        # Vérifier si les collections sont vides
        sports_count = sports_collection.count()
        tips_count = tips_collection.count()

        if sports_count == 0:
            logger.info("📊 Loading initial sports mappings...")
            for mapping in SPORTS_MAPPINGS:
                try:
                    embedding = generate_embedding(mapping["original"])
                    sports_collection.add(
                        embeddings=[embedding],
                        documents=[mapping["original"]],
                        metadatas=[{"unified": mapping["unified"]}],
                        ids=[f"{mapping['original'].lower()}_{mapping['unified']}"]
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️  Error adding sport mapping {mapping['original']}: {e}")
            logger.info(f"   ✅ {sports_collection.count()} sports mappings loaded")
        else:
            logger.info(f"   ℹ️  Sports mappings already exist ({sports_count} items)")

        if tips_count == 0:
            logger.info("🎯 Loading initial tip types mappings...")
            for mapping in TIP_TYPES_MAPPINGS:
                try:
                    embedding = generate_embedding(mapping["original"])
                    tips_collection.add(
                        embeddings=[embedding],
                        documents=[mapping["original"]],
                        metadatas=[{"unified": mapping["unified"]}],
                        ids=[f"{mapping['original'].lower()}_{mapping['unified']}"]
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️  Error adding tip mapping {mapping['original']}: {e}")
            logger.info(f"   ✅ {tips_collection.count()} tip types mappings loaded")
        else:
            logger.info(f"   ℹ️  Tip types mappings already exist ({tips_count} items)")

    except Exception as e:
        logger.error(f"❌ Error loading initial mappings: {e}")
        raise


# ============ Fonctions d'aide ============

def generate_embedding(text: str) -> list:
    """Générer un embedding avec Ollama"""
    try:
        # Configurer le client Ollama avec l'URL personnalisée
        client = ollama.Client(host=OLLAMA_URL)
        result = client.embeddings(model=OLLAMA_MODEL, prompt=text.lower())
        return result["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ollama server not reachable at {OLLAMA_URL}. Error: {str(e)}"
        )


def search_in_collection(collection, text: str, threshold: float):
    """Rechercher dans une collection ChromaDB"""
    try:
        embedding = generate_embedding(text)

        results = collection.query(
            query_embeddings=[embedding],
            n_results=1
        )

        if not results["metadatas"][0]:
            return {
                "unified": text,
                "confidence": 0.0,
                "needs_review": True,
                "original": text
            }

        distance = results["distances"][0][0]
        confidence = 1 - distance

        if confidence >= threshold:
            return {
                "unified": results["metadatas"][0][0]["unified"],
                "confidence": round(confidence, 3),
                "needs_review": False,
                "original": text
            }
        else:
            return {
                "unified": text,
                "confidence": round(confidence, 3),
                "needs_review": True,
                "original": text
            }
    except Exception as e:
        logger.error(f"Error searching in collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Router FastAPI ============

router = APIRouter()


@router.get("/health")
def health():
    """Health check détaillé"""
    try:
        # Tester Ollama
        client = ollama.Client(host=OLLAMA_URL)
        client.embeddings(model=OLLAMA_MODEL, prompt="test")

        # Compter les entrées
        sports_count = sports_collection.count() if sports_collection else 0
        tips_count = tips_collection.count() if tips_collection else 0

        return {
            "status": "healthy",
            "ollama": "ok",
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL,
            "chromadb": "ok",
            "chromadb_path": str(CHROMA_PATH),
            "stats": {
                "sports_mappings": sports_count,
                "tip_types_mappings": tips_count
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL
        }


@router.post("/", response_model=UnificationResponse)
def unify_single(request: UnificationRequest):
    """
    Unifier un seul texte (sport ou tip_type)

    Example:
        POST /unify
        {
            "text": "calcio",
            "type": "sport",
            "threshold": 0.7
        }
    """
    collection = sports_collection if request.type == "sport" else tips_collection
    result = search_in_collection(collection, request.text, request.threshold)

    return UnificationResponse(**result)


@router.post("/bulk")
def unify_bulk(request: BulkUnificationRequest):
    """
    Unifier plusieurs pronostics en batch

    Example:
        POST /unify/bulk
        {
            "items": [
                {"sport": "calcio", "tipText": "1X2: 1"},
                {"sport": "soccer", "tipText": "BTTS"}
            ],
            "threshold": 0.7
        }
    """
    results = []

    for item in request.items:
        unified_item = item.copy()

        # Unifier sport si présent
        if "sport" in item and item["sport"]:
            sport_result = search_in_collection(
                sports_collection,
                item["sport"],
                request.threshold
            )
            unified_item["sport_unified"] = sport_result["unified"]
            unified_item["sport_confidence"] = sport_result["confidence"]
            unified_item["sport_needs_review"] = sport_result["needs_review"]

        # Unifier tipText si présent
        if "tipText" in item and item["tipText"]:
            tip_result = search_in_collection(
                tips_collection,
                item["tipText"],
                request.threshold
            )
            unified_item["tipText_unified"] = tip_result["unified"]
            unified_item["tipText_confidence"] = tip_result["confidence"]
            unified_item["tipText_needs_review"] = tip_result["needs_review"]

        results.append(unified_item)

    return {
        "success": True,
        "total": len(results),
        "items": results
    }


@router.post("/mapping/add")
def add_mapping(request: MappingRequest):
    """
    Ajouter un nouveau mapping à la base

    Example:
        POST /unify/mapping/add
        {
            "original": "calcio",
            "unified": "football",
            "type": "sport"
        }
    """
    try:
        collection = sports_collection if request.type == "sport" else tips_collection

        # Générer l'embedding
        embedding = generate_embedding(request.original)

        # Ajouter à ChromaDB
        collection.add(
            embeddings=[embedding],
            documents=[request.original],
            metadatas=[{"unified": request.unified}],
            ids=[f"{request.original.lower()}_{request.unified}"]
        )

        return {
            "success": True,
            "message": f"Mapping added: {request.original} -> {request.unified}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mapping/bulk-add")
def add_bulk_mappings(mappings: List[MappingRequest]):
    """
    Ajouter plusieurs mappings en batch

    Example:
        POST /unify/mapping/bulk-add
        [
            {"original": "calcio", "unified": "football", "type": "sport"},
            {"original": "soccer", "unified": "football", "type": "sport"}
        ]
    """
    added = 0
    errors = []

    for mapping in mappings:
        try:
            collection = sports_collection if mapping.type == "sport" else tips_collection
            embedding = generate_embedding(mapping.original)

            collection.add(
                embeddings=[embedding],
                documents=[mapping.original],
                metadatas=[{"unified": mapping.unified}],
                ids=[f"{mapping.original.lower()}_{mapping.unified}"]
            )
            added += 1
        except Exception as e:
            errors.append({
                "mapping": mapping.dict(),
                "error": str(e)
            })

    return {
        "success": True,
        "added": added,
        "errors": errors
    }


@router.get("/mappings/{type}")
def get_mappings(type: str):
    """
    Récupérer tous les mappings d'un type

    Example:
        GET /unify/mappings/sport
    """
    collection = sports_collection if type == "sport" else tips_collection

    try:
        # ChromaDB get all
        results = collection.get()

        mappings = []
        for i, doc in enumerate(results["documents"]):
            mappings.append({
                "original": doc,
                "unified": results["metadatas"][i]["unified"]
            })

        return {
            "type": type,
            "total": len(mappings),
            "mappings": mappings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Exporter le router
unification_router = router
