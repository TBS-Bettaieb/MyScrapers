# Démarrage Rapide

Guide rapide pour l'API Investing Calendar.

## 🌐 API en Production

L'API est déjà déployée et accessible publiquement :

- **URL** : https://investing-api.srv842470.hstgr.cloud
- **Health** : https://investing-api.srv842470.hstgr.cloud/health
- **Docs** : https://investing-api.srv842470.hstgr.cloud/docs

## 🔄 Mise à Jour du Code

```bash
# Se connecter au serveur
ssh root@31.97.53.244

# Mettre à jour le code
cd /root/investing-com-scraper/JTrading-News-Manager/python
git pull

# Rebuilder le service
cd /root
docker-compose up -d --build investing-api
```

## 💻 Développement Local

```bash
# Cloner le repository
git clone https://github.com/VOTRE_USER/JTrading-News-Manager.git
cd JTrading-News-Manager/python

# Option 1: Avec Docker
docker-compose up --build

# Option 2: Avec Python directement
pip install -r requirements.txt
python app.py
```

L'API locale sera accessible sur : http://localhost:8001

## 🔧 Commandes Utiles

```bash
# Voir les logs
docker logs investing-calendar-api -f

# Redémarrer l'API
cd /root && docker-compose restart investing-api

# Statut des services
cd /root && docker-compose ps
```

## 📖 Documentation Complète

Voir `DEPLOYMENT.md` pour le guide complet de déploiement.
