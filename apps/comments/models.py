"""Modèle Commentaire : commentaires imbriqués attachés à un post."""

from django.conf import settings
from django.db import models


class Commentaire(models.Model):
    """
    Commentaire sur un post, ou réponse à un autre commentaire.

    L'imbrication est réalisée par la clé étrangère auto-référencée
    « commentaire_parent » (null pour un commentaire racine).
    """

    contenu = models.TextField("contenu")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commentaires",
        verbose_name="auteur",
    )
    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="commentaires",
        verbose_name="post",
    )
    commentaire_parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="reponses",
        null=True,
        blank=True,
        verbose_name="commentaire parent",
        help_text="Commentaire auquel cette réponse est attachée (null = racine).",
    )
    score = models.IntegerField(
        "score",
        default=0,
        help_text="Somme des votes (mise à jour par signaux).",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"
        ordering = ("date_creation",)

    def __str__(self):
        return self.contenu[:50]
