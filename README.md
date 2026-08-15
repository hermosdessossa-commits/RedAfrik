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

- python3 ≥ 3.12
- PostgreSQL 18 (binaires `initdb`, `pg_ctl`, `psql`)
- `curl` (facultatif, pour tester l'API)

## Installation

```bash
# 1. Environnement virtuel et dépendances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Base de données locale (dossier .pgdata, port 5433)
cp .env.example .env            # puis ajustez .env si besoin
initdb -D .pgdata -U redafrik --auth=scram-sha-256 --pwfile=<(echo redafrik)

# 3. Démarrer PostgreSQL (une seule fois) — choix A : service systemd
#    (démarrage automatique au login, plus rien à faire ensuite)
scripts/installer_pg_service.sh

#    — ou choix B : démarrage manuel à chaque session
pg_ctl -D .pgdata -l .pgdata/server.log -o "-p 5433 -k /tmp" start

# 4. Migrations + serveur
python manage.py migrate
python manage.py runserver
```

L'application est alors disponible sur http://localhost:8000/ (frontend),
l'API sur http://localhost:8000/api/ et la documentation interactive
(Swagger UI) sur http://localhost:8000/api/docs/.

### Démarrage rapide (développement)

Tout en une commande : démarre l'instance PostgreSQL locale si nécessaire,
attend qu'elle réponde, applique les migrations si demandé, puis lance le
serveur de développement.

```bash
scripts/dev.sh            # PostgreSQL local + serveur Django
scripts/dev.sh --migrate  # + application des migrations
```

### Réinitialiser la base

```bash
pg_ctl -D .pgdata stop
rm -rf .pgdata
initdb -D .pgdata -U redafrik --auth=scram-sha-256 --pwfile=<(echo redafrik)
pg_ctl -D .pgdata -l .pgdata/server.log -o "-p 5433 -k /tmp" start
python3 manage.py migrate
```

## Lancer les tests

```bash
python3 manage.py test tests --settings=config.settings_test
```

66 tests d'intégration : authentification, communautés, publications,
commentaires, votes (scores et karma), modération, sécurité du compte
(anti force brute, vérification d'e-mail, réinitialisation), journal des
actions (IP + géolocalisation) et uploads d'images.

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
| Auth | `POST auth/inscription/`, `POST auth/connexion/`, `POST auth/refresh/`, `POST auth/deconnexion/`, `POST auth/verifier-email/`, `POST auth/verifier-email/{jeton}/`, `POST auth/reinitialiser-mdp/`, `POST auth/reinitialiser-mdp/confirmer/` |
| Utilisateurs | `GET utilisateurs/`, `GET utilisateurs/{id}/`, `GET utilisateurs/moi/`, `GET/PATCH utilisateurs/profil/`, `POST utilisateurs/mdp/`, `DELETE utilisateurs/supprimer-compte/`, `GET utilisateurs/abonnements/` |
| Communautés | `GET/POST communautes/`, `GET/PATCH/DELETE communautes/{nom}/`, `POST/DELETE communautes/{nom}/abonner/`, `GET communautes/tendances/` |
| Publications | `GET/POST posts/` (`?communaute=`, `?auteur=`, `?tri=populaire`, `?search=`), `GET/PATCH/DELETE posts/{id}/`, `POST/DELETE posts/{id}/vote/` |
| Commentaires | `GET/POST commentaires/` (`?post=`), `PATCH/DELETE commentaires/{id}/`, `POST/DELETE commentaires/{id}/vote/` |
| Modération | `GET/POST moderateurs/`, `PATCH/DELETE moderateurs/{id}/`, `POST signalements/`, `GET signalements/?communaute=`, `POST signalements/{id}/traiter/`, `DELETE signalements/{id}/` |
| Administration | `GET actions/`, `GET sante/` |

L'index complet est renvoyé par `GET /api/` et les exemples par dossier
`docs/API_EXAMPLES.md`.

## Journal des actions (IP + géolocalisation)

Chaque requête HTTP est consignée en base (`JournalAction`) : utilisateur
(jeton JWT), méthode, chemin, statut, adresse IP, user-agent et, si la base
est présente, géolocalisation (pays, région, ville, coordonnées).

- **Consultation** : `GET /api/actions/` (staff uniquement — l'IP est
  masquée pour les non-superutilisateurs), filtres `?utilisateur=`,
  `?methode=`, `?chemin=`, `?du=`, `?au=` ; le back-office est accessible
  dans l'admin.
- **Sécurité** : l'IP n'est déduite de `X-Forwarded-For` que si le client
  direct figure dans `TRUSTED_PROXY_IPS` (anti-spoofing).
- **Géolocalisation** : base [GeoLite2 City](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
  (compte MaxMind gratuit), placée au chemin `GEOIP_DB_PATH`
  (défaut `data/GeoLite2-City.mmdb`, hors git). Sans base, le champ vaut
  `null` ; IP privées et locales jamais géolocalisées.
- **Conformité** : les traces sont conservées `JOURNAL_RETENTION_JOURS`
  jours (90 par défaut) puis purgées :

  ```bash
  python3 manage.py purge_journal          # rétention configurée
  python3 manage.py purge_journal --jours=30  # rétention forcée
  ```

  Planifiez cette purge quotidiennement en production (cron/systemd) ;
  annoncez la collecte dans la politique de confidentialité (droit
  d'accès et d'effacement — la suppression d'un compte supprime ses liens
  dans le journal, `SET_NULL`).

### Logs structurés

Les logs applicatifs sont émis au format JSON (une ligne par événement,
avec IP/utilisateur/chemin sur les actions). En développement ils partent
sur stdout ; en production, pointez `LOG_FILE_PATH` vers un fichier
(rotation quotidienne, 14 copies) ou dirigez stdout vers journald.

### Sauvegardes de la base

```bash
scripts/sauvegarde_bd.sh   # pg_dump compressé dans backups/ (30 jours)
```

Cron suggéré : `30 2 * * * /chemin/redafrik/scripts/sauvegarde_bd.sh`.

## Déploiement

Le dossier `deploy/` contient la configuration de production (sans Docker) :

- `deploy/gunicorn.conf.py` — config du serveur WSGI Gunicorn (bind
  `127.0.0.1:8001`, workers = 2×CPU+1, relance périodique des process)
- `deploy/redafrik.service` — unité systemd (`gunicorn -c deploy/gunicorn.conf.py
  config.wsgi`) avec redémarrage automatique
- `deploy/redafrik-pg.service` — unité systemd **utilisateur** pour l'instance
  PostgreSQL locale `.pgdata` (installée par `scripts/installer_pg_service.sh`,
  démarrage automatique au login, redémarrage après panne)
- `deploy/nginx.conf` — reverse proxy Nginx : fichiers statiques en cache,
  proxy vers Gunicorn, prêt pour HTTPS (certificat Let's Encrypt)

Fichiers statiques : `python3 manage.py collectstatic --noinput --settings=config.settings`
puis `nginx -t && systemctl reload nginx`.

En production, mettez `DJANGO_DEBUG=false` et `DJANGO_ALLOWED_HOSTS=votre-domaine`
dans `.env` (les en-têtes de sécurité, HSTS et sûrs cookies, s'activent
automatiquement ; voir `config/settings.py`).

### Déploiement Vercel (frontend) + Render (API)

Depuis la racine du dépôt, `git push origin main` déclenche deux déploiements :
la SPA sur Vercel et l'API Django sur Render (avec PostgreSQL managé). La SPA
et l'API sont sur des domaines différents ; le frontend appelle l'API grâce à
la variable `REDAFRIK_API_URL` (le fichier `config.js` généré par le build).

**1. L'API sur Render** — importez le dépôt avec *New > Blueprint* (fichier
`render.yaml` fourni). Renseignez ensuite dans *Environment* :
`ALLOWED_HOSTS` (ex. `api.redafrik.onrender.com`), `CORS_ALLOWED_ORIGINS`
(ex. `https://redafrik.vercel.app`), `FRONTEND_URL`, et éventuellement
`EMAIL_BACKEND`/SMTP + `DJANGO_LOG_LEVEL=INFO`. Les variables liées à la base
et au secret sont générées automatiquement (PostgreSQL Render ; Neon est
possible en fournissant `DATABASE_URL` manuellement). Le healthcheck
`/api/sante/` valide le service, et le disque attaché
(`/var/lib/redafrik/media`) conserve les uploads entre redéploiements.

**2. Le frontend sur Vercel** — importez le même dépôt. Le framework est
désactivé (`framework: null` dans `vercel.json`) : le build
(`scripts/vercel_build.sh`) assemble `public/` et y injecte
`REDAFRIK_API_URL` (variable d'environnement Vercel, ex.
`https://api.redafrik.onrender.com/api/`). Sans cette variable, l'API locale
`/api/` est utilisée (démo sans backend). Le `vercel.json` gère le
fallback SPA (`/c/...`, `/#/...`) et un cache long pour `static/`.

**3. Point d'attention en production**

- **CORS** : en production, ne laissez jamais `CORS_ALLOW_ALL_ORIGINS=True` ;
  listez l'origine exacte du frontend dans `CORS_ALLOWED_ORIGINS`.
- **Journal des actions** : l'adresse IP n'est déduite de `X-Forwarded-For`
  que si le client direct figure dans `TRUSTED_PROXY_IPS` — sur Render, fixez
  cette liste aux IP du proxy (ou acceptez des IP internes) puis purgez le
  journal quotidiennement (`python3 manage.py purge_journal` via le cron de
  Render).
- **E-mails** : définissez `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
  et les variables SMTP (vérification d'e-mail, réinitialisation de mot de passe).
- **Médias** : le disque de Render (`MEDIA_ROOT`) suffit pour démarrer ;
  pour un volume important, migrez vers un stockage objet (Cloudinary/S3)
  via `django-storages`.

### Tests d'intégration (CI)

Les tests s'exécutent dans GitHub Actions (`.github/workflows/ci.yml`) avec une
instance PostgreSQL 18 éphémère — même commande qu'en local :

```bash
python3 manage.py test tests --settings=config.settings_test
coverage run --source=apps,config,core manage.py test tests --settings=config.settings_test
coverage report --fail-under=65
```

### Jeu de données de démonstration

```bash
python3 manage.py seed            # crée une communauté + utilisateurs + posts
python3 manage.py seed --reset    # vide la base d'abord
```

### Tests de bout en bout (Playwright)

```bash
npm install                       # installe Playwright (une fois)
npx playwright install chromium   # télécharge le navigateur (~120 Mo, une fois)
npm run test:e2e                  # démarre un serveur dédié (base redafrik_e2e) puis lance les tests
```

Accessible aussi en local : `npm run test:e2e -- --headed` pour suivre
l'exécution visuellement.
