-- Script d'initialisation PostgreSQL pour le service d'unification
-- Ce script crée la base de données et les tables nécessaires avec l'extension pgvector

-- Créer la base de données (à exécuter en tant que superutilisateur)
-- CREATE DATABASE unification;

-- Se connecter à la base de données unification
-- \c unification

-- Créer l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Créer la table des mappings sports
CREATE TABLE IF NOT EXISTS sports_mappings (
    id SERIAL PRIMARY KEY,
    original TEXT NOT NULL,
    unified TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(original, unified)
);

-- Créer la table des mappings tip types
CREATE TABLE IF NOT EXISTS tip_types_mappings (
    id SERIAL PRIMARY KEY,
    original TEXT NOT NULL,
    unified TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(original, unified)
);

-- Créer des index pour la recherche vectorielle
-- Note: Les index ivfflat nécessitent au moins 100 vecteurs pour être créés
-- Ils seront créés automatiquement par l'application au démarrage
CREATE INDEX IF NOT EXISTS sports_embedding_idx
ON sports_mappings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS tips_embedding_idx
ON tip_types_mappings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Afficher les tables créées
\dt

-- Afficher les extensions installées
\dx
