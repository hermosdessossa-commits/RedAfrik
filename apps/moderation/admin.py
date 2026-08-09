"""Administration Django de l'app moderation (site RedAfrik)."""

from django.contrib.admin import ModelAdmin

from core.admin import site

from .models import Moderateur, Signalement


class ModerateurAdmin(ModelAdmin):
    list_display = ("utilisateur", "communaute", "role", "date_nomination")
    list_filter = ("role", "communaute")


class SignalementAdmin(ModelAdmin):
    list_display = ("id", "utilisateur", "post", "commentaire", "statut", "date_creation")
    list_filter = ("statut",)
    search_fields = ("raison", "utilisateur__username")


site.register(Moderateur, ModerateurAdmin)
site.register(Signalement, SignalementAdmin)