"""App transversale : permissions et pagination partagées par toutes les apps."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Noyau commun"
