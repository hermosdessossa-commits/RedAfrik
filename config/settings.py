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
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS au plus tôt pour que les en-têtes soient ajoutés à toutes les réponses
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        "PORT": env("DB_PORT", default="5432"),
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

# --- Fichiers statiques et médias ------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

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
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

# --- JWT (djangorestframework-simplejwt) --------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    # À chaque refresh, un nouveau jeton de rafraîchissement est émis
    "ROTATE_REFRESH_TOKENS": True,
    # et l'ancien est placé en liste noire (déconnexion possible)
    "BLACKLIST_AFTER_ROTATION": True,
    # Met à jour date_joined/last_login à chaque connexion
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- CORS (utile pour le futur frontend) -----------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")
