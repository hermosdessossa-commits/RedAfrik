"""App des votes : votes sur les posts et les commentaires."""

from django.apps import AppConfig


class VotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.votes"
    verbose_name = "Votes"

    def ready(self):
        # Enregistre les signaux de mise à jour des scores et du karma
        from . import signals  # noqa: F401
