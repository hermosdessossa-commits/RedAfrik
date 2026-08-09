"""
Paramètres dédiés aux tests.

Héritent de la configuration de production mais désactivent le throttling
(limitation de débit) afin que les suites de tests ne soient pas ralenties
ni interrompues par les limites de connexion.

Lancement : python manage.py test tests --settings=config.settings_test
"""

from .settings import *  # noqa: F401,F403

# Les tests s'exécutent en HTTP sans TLS : on désactive la redirection
# HTTPS forcée (sinon chaque requête reçoit un 301) et les réglages HSTS.
DEBUG = True
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Limites de débit quasi illimitées pendant les tests (les scopes doivent
# rester définis pour ScopedRateThrottle, mais sans jamais gêner la suite).
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anonymous": "100000/minute",
    "user": "100000/minute",
    "inscription": "100000/minute",
    "connexion": "100000/minute",
    "creation": "100000/minute",
}
