# Déploiement - Investing Calendar API

Déploiement avec Git + Docker Compose + Traefik.

## 🚀 Architecture de Déploiement

L'API est déployée sur le serveur VPS via le fichier Docker Compose principal dans `/root/docker-compose.yml` qui contient :
- **Traefik** : Reverse proxy avec SSL automatique (Let's Encrypt)
- **n8n** : Automation workflow
- **investing-api** : Cette API

## 📍 URLs de Production

L'API est accessible publiquement via HTTPS :

- **API** : https://myscrapers.srv842470.hstgr.cloud
- **Health Check** : https://myscrapers.srv842470.hstgr.cloud/health
- **Documentation Swagger** : https://myscrapers.srv842470.hstgr.cloud/docs
- **ReDoc** : https://myscrapers.srv842470.hstgr.cloud/redoc

## 🔄 Mise à Jour du Code

```bash
# Sur le serveur
ssh root@31.97.53.244
cd /root/investing-com-scraper/MyScrapers
git pull
cd /root
docker-compose up -d --build investing-api
```

## 🔧 Commandes Utiles

```bash
# Voir les logs
docker logs investing-calendar-api -f

# Redémarrer l'API
cd /root && docker-compose restart investing-api

# Voir l'état des services
cd /root && docker-compose ps

# Rebuild complet
cd /root && docker-compose up -d --build investing-api
```

## 💻 Développement Local

Pour tester localement :

```bash
# Cloner le repo
git clone https://github.com/VOTRE_USER/MyScrapers.git
cd MyScrapers

# Lancer avec Docker Compose
docker-compose up --build

# Ou lancer directement avec Python
pip install -r requirements.txt
python app.py
```

L'API sera accessible sur : http://localhost:8001

## 📖 Documentation Complète

Voir `DEPLOYMENT.md` pour plus de détails sur la configuration.
