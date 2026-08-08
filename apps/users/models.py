"""Modèle utilisateur de RedAfrik : extension d'AbstractUser avec profil et karma."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur de la plateforme.

    Hérite de AbstractUser (username, email, password, groups, permissions...)
    et ajoute le profil communautaire : bio, avatar, karma et date d'inscription.
    """

    email = models.EmailField("adresse e-mail", unique=True)
    bio = models.TextField("biographie", blank=True)
    avatar_url = models.URLField("URL de l'avatar", blank=True)
    karma = models.IntegerField(
        "karma",
        default=0,
        help_text=(
            "Points de réputation : somme des scores des posts et des "
            "commentaires publiés par l'utilisateur (mise à jour par signaux)."
        ),
    )
    date_creation = models.DateTimeField("date d'inscription", auto_now_add=True)

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-karma", "username"]

    def __str__(self):
        return self.username
