# RedAfrik

Plateforme communautaire de la diaspora africaine, inspirée de Reddit :
communautés thématiques, publications (texte, lien, image), commentaires
imbriqués, votes, karma et modération.

- **Backend** : Django 5 + Django REST Framework (JWT, OpenAPI/Swagger)
- **Base de données** : PostgreSQL (instance locale du projet, port 5433)
- **Frontend** : SPA en JavaScript vanilla (aucune dépendance, aucun tracker),
  servie par Django sur la racine `/`

---

## Prérequis

- Python ≥ 3.12
- PostgreSQL 18 (binaires `initdb`, `pg_ctl`, `psql`)
- `curl` (facultatif, pour tester l'API)

## Installation

```bash
# 1. Environnement virtuel et dépendances
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Base de données locale (dossier .pgdata, port 5433)
cp .env.example .env            # puis ajustez .env si besoin
initdb -D .pgdata -U redafrik --auth=scram-sha-256 --pwfile=<(echo redafrik)

# 3. Démarrer PostgreSQL (à refaire après chaque redémarrage)
pg_ctl -D .pgdata -l .pgdata/server.log -o "-p 5433 -k /tmp" start

# 4. Migrations + serveur
python manage.py migrate
python manage.py runserver
```

L'application est alors disponible sur http://localhost:8000/ (frontend),
l'API sur http://localhost:8000/api/ et la documentation interactive
(Swagger UI) sur http://localhost:8000/api/docs/.

### Réinitialiser la base

```bash
pg_ctl -D .pgdata stop
rm -rf .pgdata
initdb -D .pgdata -U redafrik --auth=scram-sha-256 --pwfile=<(echo redafrik)
pg_ctl -D .pgdata -l .pgdata/server.log -o "-p 5433 -k /tmp" start
python manage.py migrate
```

## Lancer les tests

```bash
python manage.py test tests --settings=config.settings_test
```

29 tests d'intégration : authentification, communautés, publications,
commentaires, votes (scores et karma), modération et cas limites.

## Structure

```
apps/
  users/        Inscription, connexion JWT, profils, classement
  communities/  Communautés, abonnements, tendances
  posts/        Publications, tri (récents/populaire), votes
  comments/     Commentaires imbriqués, votes
  votes/        Modèles VotePost/VoteCommentaire + signaux (score, karma)
  moderation/   Modérateurs par communauté, signalements
core/           Permissions, pagination, index de l'API, erreurs normalisées
frontend/       SPA (index.html, app.js, style.css)
docs/           Exemples de requêtes API (curl)
tests/          Suite d'intégration
config/         Settings (dont settings_test.py) et routage global
```

## Principaux endpoints (préfixe `/api/`)

| Domaine | Routes |
|---|---|
| Auth | `POST auth/inscription/`, `POST auth/connexion/`, `POST auth/refresh/`, `POST auth/deconnexion/` |
| Utilisateurs | `GET utilisateurs/`, `GET utilisateurs/{id}/`, `GET utilisateurs/moi/`, `GET/PATCH utilisateurs/profil/`, `GET utilisateurs/abonnements/` |
| Communautés | `GET/POST communautes/`, `GET/PATCH/DELETE communautes/{nom}/`, `POST/DELETE communautes/{nom}/abonner/`, `GET communautes/tendances/` |
| Publications | `GET/POST posts/` (`?communaute=`, `?auteur=`, `?tri=populaire`, `?search=`), `GET/PATCH/DELETE posts/{id}/`, `POST/DELETE posts/{id}/vote/` |
| Commentaires | `GET/POST commentaires/` (`?post=`), `PATCH/DELETE commentaires/{id}/`, `POST/DELETE commentaires/{id}/vote/` |
| Modération | `GET/POST moderateurs/`, `PATCH/DELETE moderateurs/{id}/`, `POST signalements/`, `GET signalements/?communaute=`, `POST signalements/{id}/traiter/` |

L'index complet est renvoyé par `GET /api/` et les exemples par dossier
`docs/API_EXAMPLES.md`.

## Déploiement

Le dossier `deploy/` contient la configuration de production (sans Docker) :

- `deploy/gunicorn.conf.py` — config du serveur WSGI Gunicorn (bind
  `127.0.0.1:8001`, workers = 2×CPU+1, relance périodique des process)
- `deploy/redafrik.service` — unité systemd (`gunicorn -c deploy/gunicorn.conf.py
  config.wsgi`) avec redémarrage automatique
- `deploy/nginx.conf` — reverse proxy Nginx : fichiers statiques en cache,
  proxy vers Gunicorn, prêt pour HTTPS (certificat Let's Encrypt)

Fichiers statiques : `python manage.py collectstatic --noinput --settings=config.settings`
puis `nginx -t && systemctl reload nginx`.

En production, mettez `DJANGO_DEBUG=false` et `DJANGO_ALLOWED_HOSTS=votre-domaine`
dans `.env` (les en-têtes de sécurité, HSTS et sûrs cookies, s'activent
automatiquement ; voir `config/settings.py`).

### Tests d'intégration (CI)

Les tests s'exécutent dans GitHub Actions (`.github/workflows/ci.yml`) avec une
instance PostgreSQL 18 éphémère — même commande qu'en local :

```bash
python manage.py test tests --settings=config.settings_test
coverage run --source=apps,config,core manage.py test tests --settings=config.settings_test
coverage report --fail-under=65
```

### Jeu de données de démonstration

```bash
python manage.py seed            # crée une communauté + utilisateurs + posts
python manage.py seed --reset    # vide la base d'abord
```

### Tests de bout en bout (Playwright)

```bash
npm install                       # installe Playwright (une fois)
npx playwright install chromium   # télécharge le navigateur (~120 Mo, une fois)
npm run test:e2e                  # démarre un serveur dédié (base redafrik_e2e) puis lance les tests
```

Accessible aussi en local : `npm run test:e2e -- --headed` pour suivre
l'exécution visuellement.
