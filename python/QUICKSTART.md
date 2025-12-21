# Démarrage Rapide

Déployer l'API Investing Calendar en 3 commandes.

## Prérequis

- Serveur VPS avec Traefik
- Git installé
- Accès SSH

## Installation

```bash
# 1. Cloner le repository
cd /opt
git clone https://github.com/VOTRE_USER/JTrading-News-Manager.git
cd JTrading-News-Manager/python

# 2. Configurer
cp .env.example .env
nano .env  # Modifier DOMAIN=investing-api.votre-domaine.com

# 3. Déployer
chmod +x deploy.sh
./deploy.sh
```

**C'est tout !** L'API est accessible sur `http://investing-api.votre-domaine.com`

## Mise à Jour

```bash
cd /opt/JTrading-News-Manager/python
git pull
./deploy.sh
```

## Commandes Utiles

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

## URLs

- API: `http://investing-api.votre-domaine.com`
- Health: `http://investing-api.votre-domaine.com/health`
- Docs: `http://investing-api.votre-domaine.com/docs`

## Documentation Complète

Voir `DEPLOYMENT.md` pour plus de détails.
