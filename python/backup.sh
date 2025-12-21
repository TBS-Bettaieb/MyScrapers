#!/bin/bash

# Script de sauvegarde pour l'API Investing Calendar
# Sauvegarde la configuration, les logs et les donn\u00e9es

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_DIR="/opt/investing-calendar-api"
BACKUP_DIR="/backup/investing-api"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="investing-api-backup-${DATE}"
RETENTION_DAYS=30

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Sauvegarde - Investing Calendar API${NC}"
echo -e "${GREEN}========================================${NC}"

# Cr\u00e9er le r\u00e9pertoire de sauvegarde
echo -e "${YELLOW}Cr\u00e9ation du r\u00e9pertoire de sauvegarde...${NC}"
mkdir -p ${BACKUP_DIR}

# Sauvegarder la configuration
echo -e "${YELLOW}Sauvegarde de la configuration...${NC}"
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-config.tar.gz \
    -C ${APP_DIR} \
    .env \
    docker-compose.yml \
    2>/dev/null || echo "Certains fichiers de configuration n'existent pas"

# Sauvegarder les logs
echo -e "${YELLOW}Sauvegarde des logs...${NC}"
if [ -d "${APP_DIR}/logs" ]; then
    tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-logs.tar.gz \
        -C ${APP_DIR} \
        logs/
else
    echo "Aucun log \u00e0 sauvegarder"
fi

# Cr\u00e9er une sauvegarde compl\u00e8te
echo -e "${YELLOW}Sauvegarde compl\u00e8te de l'application...${NC}"
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}-full.tar.gz \
    -C /opt \
    investing-calendar-api/ \
    --exclude='investing-calendar-api/__pycache__' \
    --exclude='investing-calendar-api/logs/*.log'

# Nettoyer les anciennes sauvegardes
echo -e "${YELLOW}Nettoyage des anciennes sauvegardes (>${RETENTION_DAYS} jours)...${NC}"
find ${BACKUP_DIR} -name "investing-api-backup-*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# Afficher le r\u00e9sum\u00e9
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Sauvegarde termin\u00e9e${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "R\u00e9pertoire: ${BACKUP_DIR}"
echo -e "Fichiers:"
ls -lh ${BACKUP_DIR}/${BACKUP_NAME}-*.tar.gz 2>/dev/null || echo "Aucune sauvegarde cr\u00e9\u00e9e"
echo -e "${GREEN}========================================${NC}"
