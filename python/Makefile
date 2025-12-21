# Makefile pour l'API Investing Calendar

.PHONY: help install run dev docker-build docker-up docker-down docker-logs docker-restart docker-ps clean

# Variables
PORT ?= 8001

# Couleurs
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m

help: ## Afficher l'aide
	@echo "$(GREEN)Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Installer les dépendances Python
	@echo "$(YELLOW)Installation des dépendances...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dépendances installées$(NC)"

run: ## Démarrer l'application en local
	@echo "$(YELLOW)Démarrage de l'application...$(NC)"
	python app.py

dev: ## Démarrer en mode développement
	@echo "$(YELLOW)Démarrage en mode développement...$(NC)"
	uvicorn app:app --host 0.0.0.0 --port $(PORT) --reload

test: ## Tester l'API
	@echo "$(YELLOW)Test de l'API...$(NC)"
	curl -f http://localhost:$(PORT)/health || echo "Application non accessible"

docker-build: ## Construire l'image Docker
	@echo "$(YELLOW)Construction de l'image Docker...$(NC)"
	docker-compose build
	@echo "$(GREEN)Image construite$(NC)"

docker-up: ## Démarrer les conteneurs Docker
	@echo "$(YELLOW)Démarrage des conteneurs...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Conteneurs démarrés$(NC)"

docker-down: ## Arrêter les conteneurs Docker
	@echo "$(YELLOW)Arrêt des conteneurs...$(NC)"
	docker-compose down
	@echo "$(GREEN)Conteneurs arrêtés$(NC)"

docker-logs: ## Afficher les logs Docker
	docker-compose logs -f

docker-restart: ## Redémarrer les conteneurs Docker
	@echo "$(YELLOW)Redémarrage des conteneurs...$(NC)"
	docker-compose restart
	@echo "$(GREEN)Conteneurs redémarrés$(NC)"

docker-ps: ## Afficher l'état des conteneurs
	docker-compose ps

clean: ## Nettoyer les fichiers temporaires
	@echo "$(YELLOW)Nettoyage des fichiers temporaires...$(NC)"
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf logs/*.log
	@echo "$(GREEN)Nettoyage terminé$(NC)"

deploy: ## Déployer l'application (à exécuter sur le serveur)
	@echo "$(YELLOW)Déploiement de l'application...$(NC)"
	./deploy.sh

.DEFAULT_GOAL := help
