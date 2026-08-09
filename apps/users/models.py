"""Modèle utilisateur de RedAfrik : extension d'AbstractUser avec profil et karma."""

import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from core.validateurs import valider_image_upload


class User(AbstractUser):
    """
    Utilisateur de la plateforme.

    Hérite de AbstractUser (username, email, password, groups, permissions...)
    et ajoute le profil communautaire : bio, avatar, karma et date d'inscription.
    """

    email = models.EmailField("adresse e-mail", unique=True)
    bio = models.TextField("biographie", blank=True)
    avatar_url = models.URLField("URL de l'avatar", blank=True)
    avatar = models.ImageField(
        "avatar",
        upload_to="avatars/",
        blank=True,
        validators=[valider_image_upload],
        help_text="Avatar importé (JPG, PNG, GIF, WebP, 5 Mo max).",
    )
    email_verifie = models.BooleanField(
        "e-mail vérifié",
        default=False,
        help_text="Passe à True après validation du lien envoyé par e-mail.",
    )
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
        ordering = ("-karma", "username")

    def __str__(self):
        return self.username


class JetonSecurite(models.Model):
    """
    Jeton à usage unique, haché en base (la valeur claire n'est connue que
    de l'e-mail), pour la vérification d'adresse et la réinitialisation.
    """

    BUTS = (
        ("verification", "Vérification d'e-mail"),
        ("reset_mot_de_passe", "Réinitialisation du mot de passe"),
    )

    utilisateur = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="jetons_securite"
    )
    but = models.CharField("but", max_length=30, choices=BUTS)
    jeton_hache = models.CharField("jeton haché (SHA-256)", max_length=64)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    expire_le = models.DateTimeField("expire le")

    class Meta:
        verbose_name = "jeton de sécurité"
        verbose_name_plural = "jetons de sécurité"
        indexes = (models.Index(fields=["but", "utilisateur"]),)

    @classmethod
    def creer(cls, utilisateur, but, duree: int):
        """Crée un jeton et retourne sa valeur claire (pour l'e-mail)."""
        valeur = secrets.token_urlsafe(32)
        return cls.objects.create(
            utilisateur=utilisateur,
            but=but,
            jeton_hache=cls._hacher(valeur),
            expire_le=timezone.now() + timezone.timedelta(hours=duree),
        ), valeur

    @classmethod
    def _hacher(cls, valeur: str) -> str:
        import hashlib

        return hashlib.sha256(valeur.encode()).hexdigest()

    def est_valide(self) -> bool:
        return self.expire_le > timezone.now()

    def verifier(self, valeur: str) -> bool:
        """Vrai si la valeur claire correspond et que le jeton est utilisable."""
        import hashlib

        if hashlib.sha256(valeur.encode()).hexdigest() != self.jeton_hache:
            return False
        if not self.est_valide():
            return False
        self.delete()
        return True


class EchecConnexion(models.Model):
    """
    Trace des échecs de connexion (par nom d'utilisateur et par adresse IP)
    pour verrouiller temporairement les comptes attaqués par force brute.
    """

    clef = models.CharField("clé de verrouillage (username ou IP)", max_length=64)
    horodatage = models.DateTimeField("horodatage", auto_now_add=True)

    class Meta:
        verbose_name = "échec de connexion"
        verbose_name_plural = "échecs de connexion"
        indexes = (models.Index(fields=["clef", "horodatage"]),)

    def __str__(self):
        return f"{self.clef} — {self.horodatage}"
