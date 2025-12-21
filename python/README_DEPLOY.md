# Déploiement - Investing Calendar API

Déploiement simple avec Git + Traefik.

## 🚀 Déploiement Rapide

### Sur le serveur VPS :

```bash
# 1. Cloner
cd /opt
git clone https://github.com/VOTRE_USER/JTrading-News-Manager.git
cd JTrading-News-Manager/python

# 2. Configurer
cp .env.example .env
nano .env  # Modifier DOMAIN

# 3. Déployer
chmod +x deploy.sh
./deploy.sh
```

**C'est tout !** L'API est en ligne.

## 🔄 Mise à Jour

```bash
cd /opt/JTrading-News-Manager/python
git pull
./deploy.sh
```

## 📁 Fichiers

- **deploy.sh** - Script de déploiement
- **docker-compose.yml** - Configuration Docker avec Traefik
- **.env.example** - Template de configuration
- **backup.sh** - Sauvegarde
- **monitor.sh** - Monitoring
- **test-api.sh** - Tests

## 📖 Documentation

- **QUICKSTART.md** - Guide ultra-rapide
- **DEPLOYMENT.md** - Guide complet
- **README.md** - Documentation de l'API

## 🔧 Commandes

```bash
# Logs
docker-compose logs -f

# Redémarrer
docker-compose restart

# Arrêter
docker-compose down

# Statut
docker-compose ps
```

## 🌐 URLs

- API: `http://investing-api.votre-domaine.com`
- Health: `http://investing-api.votre-domaine.com/health`
- Docs: `http://investing-api.votre-domaine.com/docs`

---

**Pour démarrer :** Voir `QUICKSTART.md`
