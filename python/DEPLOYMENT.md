# Guide de Déploiement

Guide simple pour déployer l'API Investing Calendar sur un serveur VPS avec Traefik.

## Prérequis

- Serveur VPS Linux (Ubuntu/Debian)
- Traefik déjà installé et configuré
- Git installé sur le serveur
- Accès SSH au serveur

## Déploiement Initial

### 1. Sur le serveur, cloner le repository

```bash
ssh user@votre-serveur

cd /opt  # ou tout autre répertoire de votre choix
git clone https://github.com/VOTRE_USER/JTrading-News-Manager.git
cd JTrading-News-Manager/python
```

### 2. Configurer l'environnement

```bash
# Copier le template de configuration
cp .env.example .env

# Éditer la configuration
nano .env
```

**Modifiez au minimum :**
```env
DOMAIN=investing-api.votre-domaine.com
PORT=8001
WORKERS=4
```

### 3. Déployer

```bash
# Rendre le script exécutable
chmod +x deploy.sh

# Lancer le déploiement
./deploy.sh
```

**C'est tout !** L'application est déployée et accessible via Traefik.

## Mise à Jour

Pour mettre à jour l'application après des modifications :

```bash
cd /opt/JTrading-News-Manager/python

# Récupérer les dernières modifications
git pull

# Redéployer
./deploy.sh
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
DEFAULT_TIMEZONE=58

# Domaine pour Traefik
DOMAIN=investing-api.votre-domaine.com
```

### Configuration Traefik

Le fichier `docker-compose.yml` contient les labels Traefik :

**HTTP (par défaut) :**
```yaml
- "traefik.http.routers.investing-api.rule=Host(`${DOMAIN}`)"
- "traefik.http.routers.investing-api.entrypoints=web"
```

**Pour activer HTTPS :**

Décommentez ces lignes dans `docker-compose.yml` :
```yaml
# HTTPS
- "traefik.http.routers.investing-api-secure.rule=Host(`${DOMAIN}`)"
- "traefik.http.routers.investing-api-secure.entrypoints=websecure"
- "traefik.http.routers.investing-api-secure.tls=true"
- "traefik.http.routers.investing-api-secure.tls.certresolver=letsencrypt"

# Redirection HTTP vers HTTPS
- "traefik.http.routers.investing-api.middlewares=redirect-to-https"
- "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
```

Puis redéployez :
```bash
./deploy.sh
```

## Commandes Utiles

### Gestion de l'application

```bash
cd /opt/JTrading-News-Manager/python

# Voir les logs en temps réel
docker-compose logs -f

# Redémarrer l'application
docker-compose restart

# Arrêter l'application
docker-compose down

# Démarrer l'application
docker-compose up -d

# Voir l'état des conteneurs
docker-compose ps

# Voir l'utilisation des ressources
docker stats investing-calendar-api
```

### Gestion Git

```bash
# Vérifier les modifications distantes
git fetch

# Voir les différences
git diff origin/main

# Récupérer les modifications
git pull

# Voir l'historique
git log --oneline -10

# Changer de branche
git checkout autre-branche
```

## Tests

### Test local (sur le serveur)

```bash
# Health check
curl http://localhost:8001/health

# Documentation
curl http://localhost:8001/
```

### Test via Traefik (depuis n'importe où)

```bash
# Health check
curl http://investing-api.votre-domaine.com/health

# Ou dans le navigateur
http://investing-api.votre-domaine.com/docs
```

### Script de test complet

```bash
./test-api.sh http://investing-api.votre-domaine.com
```

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
*/5 * * * * /opt/JTrading-News-Manager/python/monitor.sh
```

### Sauvegarde

Le script `backup.sh` sauvegarde la configuration et les logs :

```bash
./backup.sh
```

Pour automatiser (cron) :
```bash
# Sauvegarde quotidienne à 2h du matin
0 2 * * * /opt/JTrading-News-Manager/python/backup.sh
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

Après déploiement, l'API est accessible sur :

- **API** : http://investing-api.votre-domaine.com
- **Health** : http://investing-api.votre-domaine.com/health
- **Swagger** : http://investing-api.votre-domaine.com/docs
- **ReDoc** : http://investing-api.votre-domaine.com/redoc

## Structure du Projet

```
JTrading-News-Manager/python/
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
cd /opt/JTrading-News-Manager/python

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
