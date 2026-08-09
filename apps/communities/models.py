"""Modèles des communautés : Communaute et Abonnement."""

from django.conf import settings
from django.db import models

from core.validateurs import valider_image_upload


class Communaute(models.Model):
    """
    Communauté thématique (équivalent d'un subreddit).

    Le champ « nom » est un slug unique utilisé comme identifiant
    dans les URL (ex : r/tech-afrique).
    """

    nom = models.SlugField(
        "nom",
        max_length=50,
        unique=True,
        help_text="Identifiant unique de la communauté (ex : tech-afrique).",
    )
    description = models.TextField("description", blank=True)
    image_url = models.URLField("URL de l'image de couverture", blank=True)
    banniere = models.ImageField(
        "bannière",
        upload_to="communautes/",
        blank=True,
        validators=[valider_image_upload],
        help_text="Bannière importée (JPG, PNG, GIF, WebP, 5 Mo max).",
    )
    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communautes_crees",
        verbose_name="créateur",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "communauté"
        verbose_name_plural = "communautés"
        ordering = ("-date_creation",)

    def __str__(self):
        return f"r/{self.nom}"


class Abonnement(models.Model):
    """Abonnement d'un utilisateur à une communauté (unique par couple)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="abonnements",
        verbose_name="utilisateur",
    )
    communaute = models.ForeignKey(
        Communaute,
        on_delete=models.CASCADE,
        related_name="abonnements",
        verbose_name="communauté",
    )
    date_abonnement = models.DateTimeField("date d'abonnement", auto_now_add=True)

    class Meta:
        # Un utilisateur ne peut être abonné qu'une seule fois à une communauté
        unique_together = ("utilisateur", "communaute")
        verbose_name = "abonnement"
        ordering = ("-date_abonnement",)

    def __str__(self):
        return f"{self.utilisateur} -> r/{self.communaute.nom}"
