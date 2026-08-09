"""App frontend : interface web responsive servie par Django.

Application mono-page (SPA) en JavaScript vanilla, sans aucune ressource
externe (aucun CDN, aucun tracker). Elle consomme l'API RedAfrik.
"""

from django.apps import AppConfig


class FrontendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "frontend"
    verbose_name = "Interface web"
