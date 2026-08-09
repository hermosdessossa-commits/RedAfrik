"""Vue d'accueil : sert la single page application du frontend."""

from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Sert index.html pour toutes les routes de l'interface (SPA)."""

    template_name = "frontend/index.html"
