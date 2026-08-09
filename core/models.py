"""Modèle du noyau : journal des actions (IP + géolocalisation).

Conformément à la politique de confidentialité, les traces sont
conservées 90 jours (JOURNAL_RETENTION_JOURS) puis purgées par la
commande « python manage.py purge_journal ».
"""

from django.conf import settings
from django.db import models


class JournalAction(models.Model):
    """
    Trace d'une requête HTTP : qui (utilisateur, si identifié), quoi
    (méthode, chemin), résultat (statut) et depuis où (adresse IP et
    géolocalisation dérivée de la base GeoLite2, si disponible).
    """

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_actions",
        verbose_name="utilisateur",
        help_text="Utilisateur identifié par son jeton JWT (null si anonyme).",
    )
    methode = models.CharField("méthode HTTP", max_length=10)
    chemin = models.CharField("chemin", max_length=300, db_index=True)
    statut = models.IntegerField("statut HTTP")
    adresse_ip = models.GenericIPAddressField(
        "adresse IP", null=True, blank=True, db_index=True
    )
    agent = models.CharField(
        "user-agent", max_length=400, blank=True, default=""
    )
    geolocalisation = models.JSONField(
        "géolocalisation",
        null=True,
        blank=True,
        help_text="Dérivée de la base GeoLite2 (pays, ville, coordonnées).",
    )
    date_creation = models.DateTimeField(
        "date", auto_now_add=True, db_index=True
    )

    class Meta:
        verbose_name = "action journalisée"
        verbose_name_plural = "actions journalisées"
        ordering = ("-date_creation",)
        indexes = (models.Index(fields=["utilisateur", "-date_creation"]),)

    def __str__(self):
        return f"{self.methode} {self.chemin} → {self.statut}"