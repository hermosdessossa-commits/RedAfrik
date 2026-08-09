"""Purge des actions journalisées au-delà de la durée de conservation.

Respecte la politique de confidentialité : par défaut, supprime les traces
plus anciennes que JOURNAL_RETENTION_JOURS (90 jours).

Usage : python manage.py purge_journal [--jours=90]
À planifier quotidiennement en production (cron ou systemd timer).
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import JournalAction


class Command(BaseCommand):
    help = "Supprime les actions journalisées plus anciennes que la rétention."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jours",
            type=int,
            default=None,
            help="Nombre de jours de conservation (défaut : JOURNAL_RETENTION_JOURS).",
        )

    def handle(self, *args, **options):
        jours = options["jours"] or getattr(settings, "JOURNAL_RETENTION_JOURS", 90)
        limite = timezone.now() - timedelta(days=jours)
        supprimees, _ = JournalAction.objects.filter(
            date_creation__lt=limite
        ).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"{supprimees} action(s) purgée(s) "
                f"(conservation : {jours} jour(s))."
            )
        )