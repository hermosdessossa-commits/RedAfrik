"""
Paramètres dédiés aux tests de bout en bout (Playwright).

Héritent de la configuration de test (throttling désactivé, HTTP sans TLS)
mais utilisent une base PostgreSQL dédiée `redafrik_e2e` afin de ne pas
polluer la base de développement.

Lancement :
    createdb -p 5433 -U redafrik -h localhost redafrik_e2e
    python manage.py migrate --settings=config.settings_e2e
    python manage.py runserver 127.0.0.1:8787 --settings=config.settings_e2e
"""

import os

from .settings_test import *  # noqa: F401,F403

DATABASES["default"]["NAME"] = os.environ.get("DB_NAME_E2E", "redafrik_e2e")