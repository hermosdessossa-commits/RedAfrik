"""
Configuration Django du projet RedAfrik.

La base de données (PostgreSQL), l'authentification JWT et Django REST
Framework sont configurés ici. Les valeurs sensibles sont lues depuis le
fichier .env (voir .env.example) via django-environ.
"""

from datetime import timedelta
from pathlib import Path

import environ

# Racine du projet (dossier contenant manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Variables d'environnement ----------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

# --- Sécurité ----------------------------------------------------------------
# Valeur par défaut réservée au développement : à remplacer via .env en production.
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-redafrik-developpement-uniquement",
)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# En production, tout passe par HTTPS et les cookies sont sécurisés.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

# Protection contre le clickjacking
X_FRAME_OPTIONS = "DENY"

# Politique de sécurité du contenu : scripts et styles uniquement locaux
# (aucun CDN, aucun tracker), les images externes (avatars, couvertures)
# étant autorisées. Seule exception : cdn.jsdelivr.net, nécessaire aux
# assets de l'interface Swagger (drf-spectacular).
# Format django-csp (variables CSP_*) : loin du legacy CONTENT_SECURITY_POLICY,
# ignoré par django-csp >= 3.8.
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "https://cdn.jsdelivr.net"]
CSP_STYLE_SRC = ["'self'", "https://cdn.jsdelivr.net"]
# Les attributs style="" (avatars, mises en page ponctuelles) sont
# autorisés, mais pas les blocs <style> ni les feuilles externes.
CSP_STYLE_SRC_ATTR = ["'unsafe-inline'"]
CSP_IMG_SRC = ["'self'", "data:", "https:"]
CSP_FONT_SRC = ["'self'"]
CSP_CONNECT_SRC = ["'self'"]
CSP_FRAME_ANCESTORS = ["'none'"]
CSP_BASE_URI = ["'self'"]
CSP_FORM_ACTION = ["'self'"]

# --- Applications -------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    # Politique de sécurité du contenu (en-têtes HTTP CSP)
    "csp",
    # Documentation OpenAPI (schéma + Swagger UI)
    "drf_spectacular",
    # Nécessaire pour la révocation (blacklist) des jetons de rafraîchissement
    "rest_framework_simplejwt.token_blacklist",
]

PROJECT_APPS = [
    "core",
    "apps.users",
    "apps.communities",
    "apps.posts",
    "apps.comments",
    "apps.votes",
    "apps.moderation",
    "frontend",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS au plus tôt pour que les en-têtes soient ajoutés à toutes les réponses
    "corsheaders.middleware.CorsMiddleware",
    # En-têtes de sécurité du contenu (CSP)
    "csp.middleware.CSPMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Journal des actions (IP + géolocalisation) : dernier, pour capter
    # toutes les réponses (et les exceptions converties en 500 en amont)
    "core.middleware.JournalisationMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de données PostgreSQL -----------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env("DB_NAME", default="redafrik"),
        "USER": env("DB_USER", default="redafrik"),
        "PASSWORD": env("DB_PASSWORD", default="redafrik"),
        "HOST": env("DB_HOST", default="localhost"),
        # Instance PostgreSQL locale du projet (.pgdata) : port 5433
        "PORT": env("DB_PORT", default="5433"),
        # Durée de vie des connexions réutilisées : utile en production
        "CONN_MAX_AGE": 60,
    }
}

# Modèle utilisateur personnalisé (voir apps/users/models.py)
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --- Internationalisation -------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- E-mails transactionnels ------------------------------------------------------
# En développement : les e-mails sont imprimés dans la console.
# En production : SMTP configuré via le .env (EMAIL_HOST, EMAIL_PORT,
# EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL).
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="RedAfrik <no-reply@redafrik.app>")

# --- Fichiers statiques et médias ------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# URL publique du frontend (liens embarqués dans les e-mails transactionnels)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:8000")

# --- Journal des actions (traçabilité IP + géolocalisation) --------------------
# Chaque requête HTTP est consignée (utilisateur, méthode, chemin, statut, IP,
# user-agent, géolocalisation). Les traces sont purgées après
# JOURNAL_RETENTION_JOURS jours (commande « purge_journal », voir README).
JOURNAL_ACTIONS_ENABLED = env.bool("JOURNAL_ACTIONS_ENABLED", default=True)
JOURNAL_RETENTION_JOURS = env.int("JOURNAL_RETENTION_JOURS", default=90)
# Seules ces adresses de proxy sont autorisées à transmettre l'IP réelle du
# client via X-Forwarded-For (anti-spoofing).
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=[])
# Base GeoLite2 (MaxMind) pour la géolocalisation — facultative, non versionnée
GEOIP_DB_PATH = env(
    "GEOIP_DB_PATH", default=str(BASE_DIR / "data" / "GeoLite2-City.mmdb")
)

# --- Journalisation applicative (logs structurés JSON) ------------------------
# En production, adressez LOG_FILE_PATH vers /var/log (rotation quotidienne) ;
# en développement les lignes JSON partent sur stdout (capturables par journald).
LOG_FILE_PATH = env("LOG_FILE_PATH", default="")
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="WARNING")

# Le handler « fichier » (rotation quotidienne, rotation 14 jours) n'existe
# qu'en production, quand LOG_FILE_PATH pointe vers un emplacement valide.
_HANDLERS = {"console": {"class": "logging.StreamHandler", "formatter": "json"}}
if LOG_FILE_PATH:
    _HANDLERS["fichier"] = {
        "class": "logging.handlers.TimedRotatingFileHandler",
        "filename": LOG_FILE_PATH,
        "when": "midnight",
        "backupCount": 14,
        "formatter": "json",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "core.logging.FormateurJson"},
    },
    "handlers": _HANDLERS,
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {
            "handlers": list(_HANDLERS),
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "redafrik": {
            "handlers": list(_HANDLERS),
            "level": "INFO",
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---------------------------------------------------------
REST_FRAMEWORK = {
    # Authentification JWT par en-tête Authorization: Bearer <token>
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Lecture publique, écriture réservée aux utilisateurs authentifiés
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.PaginationStandard",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    # Schéma OpenAPI généré automatiquement par drf-spectacular
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Normalisation des erreurs API (format homogène {"erreur": ...})
    "EXCEPTION_HANDLER": "core.exceptions.redafrik_exception_handler",
    # Limitation du débit des requêtes (protection contre le brute-force)
    # : à adapter en production selon le trafic attendu.
    "DEFAULT_THROTTLE_RATES": {
        "anonymous": "60/minute",
        "user": "300/minute",
        # Auth : débit volontairement bas (anti brute-force sur les mots de passe)
        "inscription": "5/minute",
        "connexion": "10/minute",
        "creation": "30/minute",
    },
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# --- JWT (djangorestframework-simplejwt) --------------------------------------------
SIMPLE_JWT = {
    # Jeton d'accès court : limite l'exposition en cas de fuite
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # À chaque refresh, un nouveau jeton de rafraîchissement est émis
    "ROTATE_REFRESH_TOKENS": True,
    # et l'ancien est placé en liste noire (déconnexion possible)
    "BLACKLIST_AFTER_ROTATION": True,
    # Met à jour last_login à chaque connexion
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- CORS (utile pour le futur frontend) -----------------------------------------------
# En production, ne JAMAIS tout autoriser : lister les origines du frontend.
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = False

# --- Documentation OpenAPI (drf-spectacular) ---------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "RedAfrik API",
    "DESCRIPTION": (
        "Plateforme communautaire de la diaspora africaine, inspirée de Reddit. "
        "Communautés thématiques, publications, votes et modération."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "authentification", "description": "Inscription, connexion, rafraîchissement et déconnexion JWT"},
        {"name": "utilisateurs", "description": "Profils publics et profil personnel"},
        {"name": "communautes", "description": "Communautés thématiques et abonnements"},
        {"name": "posts", "description": "Publications, tri et votes"},
        {"name": "commentaires", "description": "Commentaires imbriqués et votes"},
        {"name": "moderation", "description": "Modérateurs et signalements de contenu"},
    ],
}
