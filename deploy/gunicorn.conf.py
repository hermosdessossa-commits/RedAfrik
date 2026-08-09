"""Configuration Gunicorn pour RedAfrik.

Lancement (en production, en tant qu'utilisateur du projet) :

    gunicorn -c deploy/gunicorn.conf.py config.wsgi

Ou via systemd (voir deploy/redafrik.service).
"""

import multiprocessing

# Chemin absolu du projet (adaptez si besoin)
# wsgi_app correspond au module WSGI de config/settings (DJANGO_SETTINGS_MODULE)
bind = "127.0.0.1:8001"

# Nombre de travailleurs : 2 x CPU + 1 (mais au moins 3)
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2

# Chaque travailleur est relancé après 1h de requêtes, afin de
# limiter l'accumulation de mémoire en cas de fuite.
max_requests = 1000
max_requests_jitter = 50

# Temps maximal pour traiter une requête (en secondes)
timeout = 60

# Droit du socket et nom de l'application système
# user = "redafrik"
# group = "redafrik"

# Limitation des fichiers en tête
limit_request_field_size = 8190
limit_request_line = 4094

# Journalisation
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Codage des logs
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'