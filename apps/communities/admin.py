"""Administration Django de l'app communities (site RedAfrik)."""

from django.contrib.admin import ModelAdmin

from core.admin import site

from .models import Abonnement, Communaute


class CommunauteAdmin(ModelAdmin):
    list_display = ("nom", "createur", "date_creation")
    search_fields = ("nom", "description")
    prepopulated_fields = {"nom": ("nom",)}  # noqa: RUF012


class AbonnementAdmin(ModelAdmin):
    list_display = ("utilisateur", "communaute", "date_abonnement")
    search_fields = ("utilisateur__username", "communaute__nom")


site.register(Communaute, CommunauteAdmin)
site.register(Abonnement, AbonnementAdmin)