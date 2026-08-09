"""Modèles des votes : VotePost et VoteCommentaire."""

from django.conf import settings
from django.db import models


class _BaseVote(models.Model):
    """
    Base commune des votes : un utilisateur ne vote qu'une seule fois par
    contenu (contrainte unique_together), et peut modifier son vote
    (mise à jour de la valeur).
    """

    class Valeur(models.IntegerChoices):
        POSITIF = 1, "Vote positif"
        NEGATIF = -1, "Vote négatif"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="utilisateur",
    )
    valeur = models.IntegerField(
        "valeur du vote",
        choices=Valeur.choices,
        default=Valeur.POSITIF,
        help_text="+1 pour un vote positif, -1 pour un vote négatif.",
    )
    date_vote = models.DateTimeField("date du vote", auto_now_add=True)

    class Meta:
        abstract = True


class VotePost(_BaseVote):
    """Vote d'un utilisateur sur un post."""

    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name="post",
    )

    class Meta:
        unique_together = ("utilisateur", "post")
        verbose_name = "vote de post"
        verbose_name_plural = "votes de posts"
        ordering = ["-date_vote"]

    def __str__(self):
        return f"{self.utilisateur} {'+' if self.valeur > 0 else '-'} post {self.post_id}"


class VoteCommentaire(_BaseVote):
    """Vote d'un utilisateur sur un commentaire."""

    commentaire = models.ForeignKey(
        "comments.Commentaire",
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name="commentaire",
    )

    class Meta:
        unique_together = ("utilisateur", "commentaire")
        verbose_name = "vote de commentaire"
        verbose_name_plural = "votes de commentaires"
        ordering = ["-date_vote"]

    def __str__(self):
        return f"{self.utilisateur} {'+' if self.valeur > 0 else '-'} commentaire {self.commentaire_id}"
