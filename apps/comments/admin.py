"""Administration Django de l'app comments (site RedAfrik)."""

from django.contrib.admin import ModelAdmin

from core.admin import site
from .models import Commentaire


class CommentaireAdmin(ModelAdmin):
    list_display = ("contenu", "auteur", "post", "score", "date_creation")
    search_fields = ("contenu", "auteur__username")


site.register(Commentaire, CommentaireAdmin)