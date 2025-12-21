# Guide de Déploiement

Guide pour déployer l'API Investing Calendar sur un serveur VPS avec Docker Compose et Traefik.

## 🏗️ Architecture

Le serveur utilise un fichier Docker Compose principal (`/root/docker-compose.yml`) qui orchestre :
- **Traefik** : Reverse proxy avec SSL automatique via Let's Encrypt
- **n8n** : Workflow automation
- **investing-api** : Cette API (Investing Calendar)

## 📍 Configuration Actuelle

- **Serveur** : root@31.97.53.244
- **Domaine** : srv842470.hstgr.cloud
- **URL API** : https://investing-api.srv842470.hstgr.cloud
- **Emplacement code** : /root/investing-com-scraper/MyScrapers
- **Docker Compose** : /root/docker-compose.yml

## 🚀 Déploiement Initial

Le déploiement initial a déjà été effectué. L'API est configurée dans `/root/docker-compose.yml` avec :

```yaml
investing-api:
  build:
    context: /root/investing-com-scraper/MyScrapers
    dockerfile: Dockerfile
  container_name: investing-calendar-api
  restart: always
  labels:
    - traefik.enable=true
    - traefik.http.routers.investing-api.rule=Host(`investing-api.${DOMAIN_NAME}`)
    - traefik.http.routers.investing-api.tls=true
    - traefik.http.routers.investing-api.entrypoints=web,websecure
    - traefik.http.routers.investing-api.tls.certresolver=mytlschallenge
    - traefik.http.services.investing-api.loadbalancer.server.port=8001
  environment:
    - HOST=0.0.0.0
    - PORT=8001
    - WORKERS=4
    - LOG_LEVEL=INFO
    - DEFAULT_TIMEZONE=55
  volumes:
    - /root/investing-com-scraper/MyScrapers/logs:/app/logs
```

## 🔄 Mise à Jour de l'Application

Pour mettre à jour l'API après des modifications du code :

```bash
# 1. Se connecter au serveur
ssh root@31.97.53.244

# 2. Aller dans le répertoire du code
cd /root/investing-com-scraper/MyScrapers

# 3. Récupérer les dernières modifications
git pull

# 4. Rebuilder et redémarrer le service
cd /root
docker-compose up -d --build investing-api
```

## Configuration

### Fichier .env

```env
# Application
APP_NAME=investing-calendar-api
APP_VERSION=1.0.0
ENVIRONMENT=production

# Serveur
HOST=0.0.0.0
PORT=8001
WORKERS=4

# Logs
LOG_LEVEL=INFO

# Timezone
DEFAULT_TIMEZONE=55

# Domaine pour Traefik
DOMAIN=investing-api.votre-domaine.com
```

### Variables d'Environnement

Le fichier `.env` dans `/root/` contient la configuration globale :

```env
DOMAIN_NAME=srv842470.hstgr.cloud
SUBDOMAIN=n8n
GENERIC_TIMEZONE=Europe/Berlin
SSL_EMAIL=user@srv842470.hstgr.cloud
```

L'API utilise le domaine : `investing-api.${DOMAIN_NAME}` → `investing-api.srv842470.hstgr.cloud`

### Configuration SSL/HTTPS

Le certificat SSL est automatiquement généré et renouvelé par Let's Encrypt via Traefik :
- **Certresolver** : mytlschallenge
- **Méthode** : TLS Challenge
- **Renouvellement** : Automatique

## Commandes Utiles

### Gestion de l'application

```bash
# Voir les logs en temps réel
docker logs investing-calendar-api -f

# Voir les dernières 100 lignes
docker logs investing-calendar-api --tail=100

# Redémarrer l'application
cd /root && docker-compose restart investing-api

# Voir l'état de tous les services
cd /root && docker-compose ps

# Rebuilder après modification du code
cd /root && docker-compose up -d --build investing-api

# Voir l'utilisation des ressources
docker stats investing-calendar-api
```

### Gestion Git

```bash
cd /root/investing-com-scraper/MyScrapers

# Vérifier l'état local
git status

# Voir les modifications distantes
git fetch

# Voir les différences
git diff origin/main

# Récupérer les modifications
git pull

# Voir l'historique
git log --oneline -10
```

## Tests

### Test local (sur le serveur)

```bash
# Health check interne
docker exec investing-calendar-api curl -f http://localhost:8001/health

# Test via localhost
curl -H 'Host: investing-api.srv842470.hstgr.cloud' https://localhost/health
```

### Test public (depuis n'importe où)

```bash
# Health check
curl https://investing-api.srv842470.hstgr.cloud/health

# Test complet
curl https://investing-api.srv842470.hstgr.cloud/docs
```

### Accès via navigateur

- **Health** : https://investing-api.srv842470.hstgr.cloud/health
- **Swagger UI** : https://investing-api.srv842470.hstgr.cloud/docs
- **ReDoc** : https://investing-api.srv842470.hstgr.cloud/redoc

## Monitoring et Maintenance

### Voir les logs

```bash
# Logs de l'application
docker-compose logs -f

# Dernières 100 lignes
docker-compose logs --tail=100

# Logs d'un service spécifique
docker-compose logs -f investing-api
```

### Monitoring automatique

Le script `monitor.sh` vérifie l'état de l'application :

```bash
./monitor.sh
```

Pour automatiser (cron) :
```bash
sudo crontab -e

# Ajouter :
*/5 * * * * /root/investing-com-scraper/MyScrapers/monitor.sh
```

### Sauvegarde

Le script `backup.sh` sauvegarde la configuration et les logs :

```bash
./backup.sh
```

Pour automatiser (cron) :
```bash
# Sauvegarde quotidienne à 2h du matin
0 2 * * * /root/investing-com-scraper/MyScrapers/backup.sh
```

## Dépannage

### L'application ne démarre pas

```bash
# Voir les logs
docker-compose logs

# Vérifier Docker
systemctl status docker

# Vérifier le réseau Traefik
docker network ls | grep traefik

# Recréer le réseau si nécessaire
docker network create traefik
```

### Traefik ne route pas vers l'application

```bash
# Vérifier les labels du conteneur
docker inspect investing-calendar-api | grep traefik

# Vérifier que le conteneur est sur le bon réseau
docker inspect investing-calendar-api | grep -A 5 Networks

# Vérifier les logs de Traefik
docker logs traefik
```

### Erreur "port already in use"

```bash
# Modifier le port dans .env
nano .env
# PORT=8002

# Redéployer
./deploy.sh
```

### Erreur de permissions

```bash
# Donner les permissions au script
chmod +x deploy.sh

# Si problème avec Docker
sudo usermod -aG docker $USER
# Puis se déconnecter et reconnecter
```

## URLs d'Accès

L'API est accessible publiquement via HTTPS :

- **API** : https://investing-api.srv842470.hstgr.cloud
- **Health** : https://investing-api.srv842470.hstgr.cloud/health
- **Swagger** : https://investing-api.srv842470.hstgr.cloud/docs
- **ReDoc** : https://investing-api.srv842470.hstgr.cloud/redoc

## Structure du Projet

```
MyScrapers/
├── app.py                      # Application FastAPI
├── investing_scraper.py        # Module de scraping
├── requirements.txt            # Dépendances Python
├── Dockerfile                  # Image Docker
├── docker-compose.yml          # Configuration Docker avec Traefik
├── .env.example               # Template de configuration
├── .env                       # Configuration (créé lors du déploiement)
├── deploy.sh                  # Script de déploiement
├── backup.sh                  # Script de sauvegarde
├── monitor.sh                 # Script de monitoring
├── test-api.sh               # Script de tests
└── logs/                      # Logs (créé automatiquement)
```

## Workflow de Développement

### Développement local

```bash
# Faire vos modifications
git add .
git commit -m "Description des modifications"
git push origin main
```

### Déploiement sur le serveur

```bash
# Se connecter au serveur
ssh user@serveur

# Aller dans le répertoire
cd /root/investing-com-scraper/MyScrapers

# Récupérer les modifications
git pull

# Redéployer
./deploy.sh
```

## Sécurité

### Fichiers à ne PAS commiter

Le `.gitignore` contient déjà :
```
.env
logs/
*.log
__pycache__/
build/
release/
backup/
```

### Protection de .env

Le fichier `.env` contient des informations sensibles et ne doit jamais être commité.
Utilisez `.env.example` comme template.

## Support

Pour plus d'informations :

1. Vérifier les logs : `docker-compose logs`
2. Vérifier Traefik : `docker logs traefik`
3. Tester l'API : `./test-api.sh http://votre-domaine.com`
4. Générer un rapport : `./generate-report.sh` (si disponible)

---

**Créé le 21 décembre 2025**
