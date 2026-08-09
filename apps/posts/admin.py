"""Administration Django de l'app posts (site RedAfrik)."""

from django.contrib.admin import ModelAdmin

from core.admin import site
from .models import Post


class PostAdmin(ModelAdmin):
    list_display = ("titre", "auteur", "communaute", "score", "date_creation")
    list_filter = ("communaute",)
    search_fields = ("titre", "contenu", "auteur__username")


site.register(Post, PostAdmin)