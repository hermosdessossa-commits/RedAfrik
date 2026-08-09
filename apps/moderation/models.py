"""Modèles de la modération : Moderateur et Signalement."""

from django.conf import settings
from django.db import models


class Moderateur(models.Model):
    """
    Rôle d'un utilisateur au sein d'une communauté.

    Le créateur d'une communauté y est automatiquement administrateur
    (voir CommunauteSerializer.create). Un utilisateur n'a qu'un seul
    rôle par communauté (unique_together).
    """

    class Role(models.TextChoices):
        MODERATEUR = "moderateur", "Modérateur"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roles_moderation",
        verbose_name="utilisateur",
    )
    communaute = models.ForeignKey(
        "communities.Communaute",
        on_delete=models.CASCADE,
        related_name="moderateurs",
        verbose_name="communauté",
    )
    role = models.CharField(
        "rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.MODERATEUR,
    )
    date_nomination = models.DateTimeField("date de nomination", auto_now_add=True)

    class Meta:
        unique_together = ("utilisateur", "communaute")
        verbose_name = "modérateur"
        verbose_name_plural = "modérateurs"
        ordering = ["date_nomination"]

    def __str__(self):
        return f"{self.utilisateur} ({self.get_role_display()}) r/{self.communaute.nom}"


class Signalement(models.Model):
    """
    Signalement d'un contenu inapproprié par un utilisateur.

    Un signalement cible soit un post, soit un commentaire. Il est traité
    par les modérateurs de la communauté concernée (statut : en attente,
    résolu ou rejeté).
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        RESOLU = "resolu", "Résolu"
        REJETE = "rejete", "Rejeté"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signalements",
        verbose_name="signalé par",
    )
    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="signalements",
        null=True,
        blank=True,
        verbose_name="post signalé",
    )
    commentaire = models.ForeignKey(
        "comments.Commentaire",
        on_delete=models.CASCADE,
        related_name="signalements",
        null=True,
        blank=True,
        verbose_name="commentaire signalé",
    )
    raison = models.TextField("raison du signalement")
    date_creation = models.DateTimeField("date du signalement", auto_now_add=True)
    statut = models.CharField(
        "statut",
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )

    class Meta:
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
        ordering = ["-date_creation"]

    def __str__(self):
        cible = self.post or self.commentaire
        return f"Signalement #{self.pk} ({self.get_statut_display()}) -> {cible}"

    def communaute_cible(self):
        """Communauté du contenu signalé, ou None si la cible a été supprimée."""
        cible = self.post or self.commentaire
        return cible.communaute if cible else None
