"""Modèle Post : une publication au sein d'une communauté."""

from django.conf import settings
from django.db import models


class Post(models.Model):
    """
    Publication dans une communauté.

    Un post doit contenir au moins une des trois formes de contenu :
    texte (contenu), lien externe (url_externe) ou image (image_url).
    """

    titre = models.CharField("titre", max_length=300)
    contenu = models.TextField(
        "contenu",
        blank=True,
        help_text="Contenu texte du post (vide si le post est un lien ou une image).",
    )
    url_externe = models.URLField("lien externe", blank=True)
    image_url = models.URLField("URL de l'image", blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name="auteur",
    )
    communaute = models.ForeignKey(
        "communities.Communaute",
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name="communauté",
    )
    score = models.IntegerField(
        "score",
        default=0,
        help_text="Somme des votes positifs et négatifs (mise à jour par signaux).",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_modification = models.DateTimeField("date de modification", auto_now=True)

    class Meta:
        verbose_name = "publication"
        verbose_name_plural = "publications"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.titre
