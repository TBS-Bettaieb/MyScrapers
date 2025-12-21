#!/bin/bash

# Script de test de l'API Investing Calendar
# Teste tous les endpoints pour v\u00e9rifier le bon fonctionnement

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL=${1:-"http://localhost:8001"}
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Fonction pour afficher les r\u00e9sultats
print_result() {
    local test_name=$1
    local result=$2
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}\u2713${NC} ${test_name}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}\u2717${NC} ${test_name}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Fonction pour tester un endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-"GET"}
    local data=${4:-""}

    echo -e "${BLUE}Test:${NC} ${name}"

    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${API_URL}${url}")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}${url}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ]; then
        print_result "$name" 0
        echo -e "${BLUE}R\u00e9ponse:${NC} $(echo $body | head -c 200)..."
        echo ""
        return 0
    else
        print_result "$name" 1
        echo -e "${RED}Code HTTP:${NC} $http_code"
        echo -e "${RED}R\u00e9ponse:${NC} $body"
        echo ""
        return 1
    fi
}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Tests de l'API Investing Calendar${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "URL: ${API_URL}"
echo -e ""

# Test 1: Endpoint racine
test_endpoint "Endpoint racine (/)" "/" "GET"

# Test 2: Health check
test_endpoint "Health check (/health)" "/health" "GET"

# Test 3: Scraping GET simple
test_endpoint "Scraping GET simple" "/scrape/investing?date_from=2025-01-01&date_to=2025-01-02" "GET"

# Test 4: Scraping GET avec timezone
test_endpoint "Scraping GET avec timezone" "/scrape/investing?date_from=2025-01-01&date_to=2025-01-02&timezone=58" "GET"

# Test 5: Scraping POST simple
test_endpoint "Scraping POST simple" "/scrape/investing" "POST" '{
    "date_from": "2025-01-01",
    "date_to": "2025-01-02"
}'

# Test 6: Scraping POST avec filtres
test_endpoint "Scraping POST avec filtres" "/scrape/investing" "POST" '{
    "date_from": "2025-01-01",
    "date_to": "2025-01-02",
    "timezone": 58,
    "importance": [2, 3]
}'

# Test 7: Documentation Swagger
echo -e "${BLUE}Test:${NC} Documentation Swagger"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/docs")
if [ "$http_code" -eq 200 ]; then
    print_result "Documentation Swagger (/docs)" 0
else
    print_result "Documentation Swagger (/docs)" 1
fi
echo ""

# Test 8: Documentation ReDoc
echo -e "${BLUE}Test:${NC} Documentation ReDoc"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/redoc")
if [ "$http_code" -eq 200 ]; then
    print_result "Documentation ReDoc (/redoc)" 0
else
    print_result "Documentation ReDoc (/redoc)" 1
fi
echo ""

# Test 9: OpenAPI JSON
echo -e "${BLUE}Test:${NC} OpenAPI JSON"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/openapi.json")
if [ "$http_code" -eq 200 ]; then
    print_result "OpenAPI JSON (/openapi.json)" 0
else
    print_result "OpenAPI JSON (/openapi.json)" 1
fi
echo ""

# R\u00e9sum\u00e9
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}R\u00e9sum\u00e9 des tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Total: ${TOTAL_TESTS} tests"
echo -e "${GREEN}R\u00e9ussis: ${PASSED_TESTS}${NC}"
echo -e "${RED}\u00c9chou\u00e9s: ${FAILED_TESTS}${NC}"
echo -e ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}Tous les tests sont pass\u00e9s avec succ\u00e8s!${NC}"
    exit 0
else
    echo -e "${RED}Certains tests ont \u00e9chou\u00e9!${NC}"
    exit 1
fi
