# Configuration Serveur de Production

Ce document décrit la configuration actuelle du serveur de production.

## 🏗️ Architecture du Serveur

Le serveur utilise un fichier Docker Compose centralisé dans `/root/docker-compose.yml` qui orchestre tous les services :

```
/root/
├── docker-compose.yml          # Configuration principale (Traefik + n8n + investing-api)
├── .env                        # Variables d'environnement globales
└── investing-com-scraper/
    └── JTrading-News-Manager/
        └── MyScrapers/         # Code source de l'API
```

## 📍 Informations du Serveur

- **Adresse** : root@31.97.53.244
- **Domaine principal** : srv842470.hstgr.cloud
- **URL API** : https://myscrapers.srv842470.hstgr.cloud

## 🐳 Services Docker

### Traefik (Reverse Proxy)
- Ports : 80 (HTTP), 443 (HTTPS)
- Certificats SSL : Let's Encrypt automatique
- Certresolver : mytlschallenge

### n8n (Workflow Automation)
- URL : https://n8n.srv842470.hstgr.cloud

### investing-api (Cette API)
- URL : https://myscrapers.srv842470.hstgr.cloud
- Container : investing-calendar-api
- Workers : 4
- Port interne : 8001

## 🔄 Workflow de Mise à Jour

### 1. Développer en local
```bash
# Modifier le code localement
git add .
git commit -m "Description des modifications"
git push origin main
```

### 2. Déployer sur le serveur
```bash
# Se connecter au serveur
ssh root@31.97.53.244

# Mettre à jour le code
cd /root/investing-com-scraper/MyScrapers
git pull

# Rebuilder et redémarrer le service
cd /root
docker-compose up -d --build investing-api
```

### 3. Vérifier le déploiement
```bash
# Vérifier les logs
docker logs investing-calendar-api --tail=50

# Tester l'API
curl https://myscrapers.srv842470.hstgr.cloud/health
```

## 🔐 Configuration SSL/TLS

Le certificat SSL est automatiquement géré par Traefik via Let's Encrypt :
- **Émetteur** : Let's Encrypt (R12)
- **Domaine** : myscrapers.srv842470.hstgr.cloud
- **Méthode** : TLS Challenge
- **Renouvellement** : Automatique

## 📝 Variables d'Environnement

Le fichier `/root/.env` contient les variables globales :
```env
DOMAIN_NAME=srv842470.hstgr.cloud
SUBDOMAIN=n8n
GENERIC_TIMEZONE=Europe/Berlin
SSL_EMAIL=user@srv842470.hstgr.cloud
```

Les variables spécifiques à l'API sont définies dans `/root/docker-compose.yml` :
```yaml
environment:
  - HOST=0.0.0.0
  - PORT=8001
  - WORKERS=4
  - LOG_LEVEL=INFO
  - DEFAULT_TIMEZONE=55
```

## 🛠️ Commandes Utiles

```bash
# Voir tous les services
cd /root && docker-compose ps

# Voir les logs de l'API
docker logs investing-calendar-api -f

# Redémarrer l'API
cd /root && docker-compose restart investing-api

# Voir les logs de Traefik
docker logs root_traefik_1 --tail=100

# Vérifier le certificat SSL
curl -vI https://myscrapers.srv842470.hstgr.cloud 2>&1 | grep -E 'subject|issuer'
```

## 🔒 Backup

Avant toute modification importante du docker-compose.yml :
```bash
cp /root/docker-compose.yml /root/docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)
```

## 📚 Documentation

- **QUICKSTART.md** : Guide de démarrage rapide
- **DEPLOYMENT.md** : Guide complet de déploiement
- **README_DEPLOY.md** : Vue d'ensemble du déploiement
- **README_SERVER.md** : Ce fichier (configuration serveur)
