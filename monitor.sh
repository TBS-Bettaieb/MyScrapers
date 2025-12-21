#!/bin/bash

# Script de monitoring pour l'API Investing Calendar
# V\u00e9rifie l'\u00e9tat de l'application et envoie des alertes si n\u00e9cessaire

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_DIR="/opt/investing-calendar-api"
API_URL="http://localhost:8001"
LOG_FILE="/var/log/investing-api-monitor.log"
ALERT_EMAIL=${ALERT_EMAIL:-""}

# Seuils d'alerte
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85

# Fonction de logging
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# Fonction d'alerte
send_alert() {
    local message=$1
    log_message "ALERT: $message"

    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Alert: Investing Calendar API" $ALERT_EMAIL 2>/dev/null || \
            log_message "Erreur lors de l'envoi de l'email d'alerte"
    fi
}

# V\u00e9rifier si l'application r\u00e9pond
check_health() {
    log_message "V\u00e9rification de la sant\u00e9 de l'application..."

    if curl -sf ${API_URL}/health > /dev/null 2>&1; then
        log_message "Application OK - Health check pass\u00e9"
        return 0
    else
        send_alert "L'application ne r\u00e9pond pas au health check"
        return 1
    fi
}

# V\u00e9rifier le statut Docker
check_docker() {
    log_message "V\u00e9rification du statut Docker..."

    cd ${APP_DIR}
    if docker-compose ps | grep -q "Up"; then
        log_message "Conteneurs Docker OK"
        return 0
    else
        send_alert "Les conteneurs Docker ne sont pas actifs"
        return 1
    fi
}

# V\u00e9rifier l'utilisation CPU
check_cpu() {
    log_message "V\u00e9rification de l'utilisation CPU..."

    cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" investing-calendar-api | sed 's/%//' | cut -d'.' -f1)

    if [ -z "$cpu_usage" ]; then
        log_message "Impossible de r\u00e9cup\u00e9rer l'utilisation CPU"
        return 1
    fi

    log_message "Utilisation CPU: ${cpu_usage}%"

    if [ "$cpu_usage" -gt "$CPU_THRESHOLD" ]; then
        send_alert "Utilisation CPU \u00e9lev\u00e9e: ${cpu_usage}% (seuil: ${CPU_THRESHOLD}%)"
        return 1
    fi

    return 0
}

# V\u00e9rifier l'utilisation m\u00e9moire
check_memory() {
    log_message "V\u00e9rification de l'utilisation m\u00e9moire..."

    mem_usage=$(docker stats --no-stream --format "{{.MemPerc}}" investing-calendar-api | sed 's/%//' | cut -d'.' -f1)

    if [ -z "$mem_usage" ]; then
        log_message "Impossible de r\u00e9cup\u00e9rer l'utilisation m\u00e9moire"
        return 1
    fi

    log_message "Utilisation m\u00e9moire: ${mem_usage}%"

    if [ "$mem_usage" -gt "$MEMORY_THRESHOLD" ]; then
        send_alert "Utilisation m\u00e9moire \u00e9lev\u00e9e: ${mem_usage}% (seuil: ${MEMORY_THRESHOLD}%)"
        return 1
    fi

    return 0
}

# V\u00e9rifier l'espace disque
check_disk() {
    log_message "V\u00e9rification de l'espace disque..."

    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    log_message "Utilisation disque: ${disk_usage}%"

    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        send_alert "Espace disque faible: ${disk_usage}% (seuil: ${DISK_THRESHOLD}%)"
        return 1
    fi

    return 0
}

# V\u00e9rifier les logs d'erreur
check_logs() {
    log_message "V\u00e9rification des logs d'erreur..."

    cd ${APP_DIR}
    error_count=$(docker-compose logs --tail=100 | grep -i "error" | wc -l)

    log_message "Erreurs dans les logs (100 derni\u00e8res lignes): ${error_count}"

    if [ "$error_count" -gt 10 ]; then
        send_alert "Nombre \u00e9lev\u00e9 d'erreurs dans les logs: ${error_count}"
        return 1
    fi

    return 0
}

# Fonction de red\u00e9marrage automatique
auto_restart() {
    log_message "Tentative de red\u00e9marrage automatique..."

    cd ${APP_DIR}
    docker-compose restart

    sleep 10

    if check_health; then
        log_message "Red\u00e9marrage r\u00e9ussi"
        send_alert "L'application a \u00e9t\u00e9 red\u00e9marr\u00e9e automatiquement"
        return 0
    else
        send_alert "Le red\u00e9marrage automatique a \u00e9chou\u00e9"
        return 1
    fi
}

# Afficher le r\u00e9sum\u00e9
print_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}R\u00e9sum\u00e9 du monitoring${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Date: $(date)"
    echo -e "Application: ${APP_NAME:-Investing Calendar API}"
    echo -e "URL: ${API_URL}"
    echo -e ""
    echo -e "Statut global: ${status_global}"
    echo -e "${GREEN}========================================${NC}"
}

# Menu principal
main() {
    log_message "D\u00e9but du monitoring..."

    local checks_passed=0
    local checks_failed=0

    # Ex\u00e9cuter tous les checks
    check_health && ((checks_passed++)) || ((checks_failed++))
    check_docker && ((checks_passed++)) || ((checks_failed++))
    check_cpu && ((checks_passed++)) || ((checks_failed++))
    check_memory && ((checks_passed++)) || ((checks_failed++))
    check_disk && ((checks_passed++)) || ((checks_failed++))
    check_logs && ((checks_passed++)) || ((checks_failed++))

    # R\u00e9sum\u00e9
    log_message "Checks r\u00e9ussis: ${checks_passed}"
    log_message "Checks \u00e9chou\u00e9s: ${checks_failed}"

    # Si le health check a \u00e9chou\u00e9, tenter un red\u00e9marrage
    if ! check_health; then
        log_message "Health check \u00e9chou\u00e9, tentative de red\u00e9marrage..."
        auto_restart
    fi

    # Statut global
    if [ "$checks_failed" -eq 0 ]; then
        status_global="${GREEN}OK${NC}"
        log_message "Tous les checks sont OK"
    elif [ "$checks_failed" -le 2 ]; then
        status_global="${YELLOW}WARNING${NC}"
        log_message "Certains checks ont \u00e9chou\u00e9 (warnings)"
    else
        status_global="${RED}CRITICAL${NC}"
        log_message "Plusieurs checks ont \u00e9chou\u00e9 (critique)"
    fi

    print_summary

    log_message "Fin du monitoring"
}

# Ex\u00e9cuter le monitoring
main "$@"
