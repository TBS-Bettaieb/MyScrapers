#!/bin/bash

# Script de déploiement pour serveur VPS avec Traefik
# À exécuter DIRECTEMENT sur le serveur après git clone/pull

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Déploiement Investing Calendar API${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "app.py" ] || [ ! -f "investing_scraper.py" ]; then
    echo -e "${RED}Erreur: Vous devez être dans le répertoire du projet${NC}"
    exit 1
fi

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker n'est pas installé. Installation...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}Docker installé${NC}"
fi

# Vérifier que Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose n'est pas installé. Installation...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installé${NC}"
fi

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Création du fichier .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Fichier .env créé${NC}"
    echo -e "${YELLOW}IMPORTANT: Modifiez .env avec votre domaine:${NC}"
    echo -e "${YELLOW}  nano .env${NC}"
    echo -e "${YELLOW}Puis relancez ce script${NC}\n"

    read -p "Voulez-vous éditer .env maintenant? (o/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        ${EDITOR:-nano} .env
    else
        exit 0
    fi
fi

# Charger les variables d'environnement
source .env

# Vérifier que le réseau Traefik existe
if ! docker network ls | grep -q "traefik"; then
    echo -e "${YELLOW}Création du réseau Traefik...${NC}"
    docker network create traefik
    echo -e "${GREEN}Réseau Traefik créé${NC}"
fi

# Créer le répertoire de logs
mkdir -p logs

# Arrêter l'ancienne version si elle existe
echo -e "${YELLOW}Arrêt de l'ancienne version...${NC}"
docker-compose down 2>/dev/null || true

# Build et démarrage
echo -e "${BLUE}Construction de l'image Docker...${NC}"
docker-compose build

echo -e "${BLUE}Démarrage de l'application...${NC}"
docker-compose up -d

# Attendre le démarrage
echo -e "${YELLOW}Attente du démarrage (10s)...${NC}"
sleep 10

# Vérifier l'état
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Application déployée avec succès!${NC}"
    echo -e "${GREEN}========================================${NC}\n"

    echo -e "${BLUE}Informations:${NC}"
    echo -e "  Domaine: ${DOMAIN:-Non configuré}"
    echo -e "  URL API: http://${DOMAIN:-localhost}/health"
    echo -e "  Documentation: http://${DOMAIN:-localhost}/docs"
    echo -e ""
    echo -e "${BLUE}Commandes utiles:${NC}"
    echo -e "  Logs:       docker-compose logs -f"
    echo -e "  Redémarrer: docker-compose restart"
    echo -e "  Arrêter:    docker-compose down"
    echo -e "  Statut:     docker-compose ps"
    echo -e "${GREEN}========================================${NC}\n"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Erreur lors du déploiement${NC}"
    echo -e "${RED}========================================${NC}\n"
    echo -e "Vérifiez les logs:"
    docker-compose logs
    exit 1
fi
