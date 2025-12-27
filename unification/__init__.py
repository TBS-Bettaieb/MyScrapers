"""
Module d'unification pour sports et tip types
Utilise Ollama + PostgreSQL avec pgvector pour la recherche sémantique
"""
import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import ollama
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

from .mappings import SPORTS_MAPPINGS, TIP_TYPES_MAPPINGS

logger = logging.getLogger(__name__)

# Configuration Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")

# Configuration PostgreSQL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "unification")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Connexion PostgreSQL globale
pg_conn = None


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

def get_db_connection():
    """Obtenir une connexion à la base de données PostgreSQL"""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def init_postgres():
    """Initialiser PostgreSQL et créer les tables avec pgvector"""
    global pg_conn

    try:
        # Se connecter à PostgreSQL
        pg_conn = get_db_connection()
        cursor = pg_conn.cursor()

        # Créer l'extension pgvector si elle n'existe pas
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Créer la table des mappings sports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sports_mappings (
                id SERIAL PRIMARY KEY,
                original TEXT NOT NULL,
                unified TEXT NOT NULL,
                embedding vector(768),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(original, unified)
            );
        """)

        # Créer la table des mappings tip types
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tip_types_mappings (
                id SERIAL PRIMARY KEY,
                original TEXT NOT NULL,
                unified TEXT NOT NULL,
                embedding vector(768),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(original, unified)
            );
        """)

        # Créer des index pour la recherche vectorielle
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS sports_embedding_idx
            ON sports_mappings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS tips_embedding_idx
            ON tip_types_mappings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        pg_conn.commit()

        # Compter les entrées
        cursor.execute("SELECT COUNT(*) FROM sports_mappings;")
        sports_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tip_types_mappings;")
        tips_count = cursor.fetchone()[0]

        logger.info(f"✅ PostgreSQL initialized")
        logger.info(f"   - Sports mappings: {sports_count}")
        logger.info(f"   - Tip types mappings: {tips_count}")

        cursor.close()

        return {
            "sports": sports_count,
            "tips": tips_count
        }
    except Exception as e:
        logger.error(f"❌ Error initializing PostgreSQL: {e}")
        raise


async def load_initial_mappings():
    """Charger les mappings de base si la base est vide"""
    global pg_conn

    try:
        cursor = pg_conn.cursor()

        # Vérifier si les tables sont vides
        cursor.execute("SELECT COUNT(*) FROM sports_mappings;")
        sports_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tip_types_mappings;")
        tips_count = cursor.fetchone()[0]

        if sports_count == 0:
            logger.info("📊 Loading initial sports mappings...")
            for mapping in SPORTS_MAPPINGS:
                try:
                    embedding = generate_embedding(mapping["original"])
                    cursor.execute("""
                        INSERT INTO sports_mappings (original, unified, embedding)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (original, unified) DO NOTHING;
                    """, (mapping["original"], mapping["unified"], embedding))
                except Exception as e:
                    logger.warning(f"   ⚠️  Error adding sport mapping {mapping['original']}: {e}")

            pg_conn.commit()
            cursor.execute("SELECT COUNT(*) FROM sports_mappings;")
            new_count = cursor.fetchone()[0]
            logger.info(f"   ✅ {new_count} sports mappings loaded")
        else:
            logger.info(f"   ℹ️  Sports mappings already exist ({sports_count} items)")

        if tips_count == 0:
            logger.info("🎯 Loading initial tip types mappings...")
            for mapping in TIP_TYPES_MAPPINGS:
                try:
                    embedding = generate_embedding(mapping["original"])
                    cursor.execute("""
                        INSERT INTO tip_types_mappings (original, unified, embedding)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (original, unified) DO NOTHING;
                    """, (mapping["original"], mapping["unified"], embedding))
                except Exception as e:
                    logger.warning(f"   ⚠️  Error adding tip mapping {mapping['original']}: {e}")

            pg_conn.commit()
            cursor.execute("SELECT COUNT(*) FROM tip_types_mappings;")
            new_count = cursor.fetchone()[0]
            logger.info(f"   ✅ {new_count} tip types mappings loaded")
        else:
            logger.info(f"   ℹ️  Tip types mappings already exist ({tips_count} items)")

        cursor.close()

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


def search_in_table(table_name: str, text: str, threshold: float):
    """Rechercher dans une table PostgreSQL avec pgvector"""
    global pg_conn

    try:
        embedding = generate_embedding(text)

        cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

        # Recherche par similarité cosinus (1 - distance cosinus = similarité)
        cursor.execute(f"""
            SELECT
                original,
                unified,
                1 - (embedding <=> %s::vector) as confidence
            FROM {table_name}
            ORDER BY embedding <=> %s::vector
            LIMIT 1;
        """, (embedding, embedding))

        result = cursor.fetchone()
        cursor.close()

        if not result:
            return {
                "unified": text,
                "confidence": 0.0,
                "needs_review": True,
                "original": text
            }

        confidence = float(result["confidence"])

        if confidence >= threshold:
            return {
                "unified": result["unified"],
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
        logger.error(f"Error searching in table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Router FastAPI ============

router = APIRouter()


@router.get("/health")
def health():
    """Health check détaillé"""
    global pg_conn

    try:
        # Tester Ollama
        client = ollama.Client(host=OLLAMA_URL)
        client.embeddings(model=OLLAMA_MODEL, prompt="test")

        # Tester PostgreSQL et compter les entrées
        cursor = pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sports_mappings;")
        sports_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tip_types_mappings;")
        tips_count = cursor.fetchone()[0]
        cursor.close()

        return {
            "status": "healthy",
            "ollama": "ok",
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL,
            "postgres": "ok",
            "postgres_host": POSTGRES_HOST,
            "postgres_db": POSTGRES_DB,
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
            "ollama_model": OLLAMA_MODEL,
            "postgres_host": POSTGRES_HOST,
            "postgres_db": POSTGRES_DB
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
    table_name = "sports_mappings" if request.type == "sport" else "tip_types_mappings"
    result = search_in_table(table_name, request.text, request.threshold)

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
            sport_result = search_in_table(
                "sports_mappings",
                item["sport"],
                request.threshold
            )
            unified_item["sport_unified"] = sport_result["unified"]
            unified_item["sport_confidence"] = sport_result["confidence"]
            unified_item["sport_needs_review"] = sport_result["needs_review"]

        # Unifier tipText si présent
        if "tipText" in item and item["tipText"]:
            tip_result = search_in_table(
                "tip_types_mappings",
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
    global pg_conn

    try:
        table_name = "sports_mappings" if request.type == "sport" else "tip_types_mappings"

        # Générer l'embedding
        embedding = generate_embedding(request.original)

        # Ajouter à PostgreSQL
        cursor = pg_conn.cursor()
        cursor.execute(f"""
            INSERT INTO {table_name} (original, unified, embedding)
            VALUES (%s, %s, %s)
            ON CONFLICT (original, unified) DO NOTHING;
        """, (request.original, request.unified, embedding))
        pg_conn.commit()
        cursor.close()

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
    global pg_conn

    added = 0
    errors = []

    cursor = pg_conn.cursor()

    for mapping in mappings:
        try:
            table_name = "sports_mappings" if mapping.type == "sport" else "tip_types_mappings"
            embedding = generate_embedding(mapping.original)

            cursor.execute(f"""
                INSERT INTO {table_name} (original, unified, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (original, unified) DO NOTHING;
            """, (mapping.original, mapping.unified, embedding))

            added += 1
        except Exception as e:
            errors.append({
                "mapping": mapping.dict(),
                "error": str(e)
            })

    pg_conn.commit()
    cursor.close()

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
    global pg_conn

    table_name = "sports_mappings" if type == "sport" else "tip_types_mappings"

    try:
        cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SELECT original, unified FROM {table_name};")
        results = cursor.fetchall()
        cursor.close()

        mappings = [{"original": row["original"], "unified": row["unified"]} for row in results]

        return {
            "type": type,
            "total": len(mappings),
            "mappings": mappings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Exporter le router
unification_router = router
