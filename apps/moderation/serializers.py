"""Serializers de l'app moderation."""

from rest_framework import serializers

from apps.comments.models import Commentaire
from apps.communities.models import Communaute
from apps.posts.models import Post
from apps.users.models import User
from apps.users.serializers import UtilisateurCompactSerializer

from .models import Moderateur, Signalement


class ModerateurSerializer(serializers.ModelSerializer):
    """Nomination d'un modérateur : utilisateur, communauté et rôle."""

    utilisateur = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    utilisateur_detail = UtilisateurCompactSerializer(
        source="utilisateur", read_only=True
    )
    communaute = serializers.SlugRelatedField(
        slug_field="nom", queryset=Communaute.objects.all()
    )

    class Meta:
        model = Moderateur
        fields = (
            "id",
            "utilisateur",
            "utilisateur_detail",
            "communaute",
            "role",
            "date_nomination",
        )
        read_only_fields = ("id", "date_nomination")

    def validate(self, attrs):
        """Un utilisateur ne peut avoir qu'un seul rôle par communauté."""
        if self.instance is None or "utilisateur" in attrs or "communaute" in attrs:
            utilisateur = attrs.get("utilisateur") or getattr(
                self.instance, "utilisateur", None
            )
            communaute = attrs.get("communaute") or getattr(
                self.instance, "communaute", None
            )
            if utilisateur and communaute and Moderateur.objects.filter(
                utilisateur=utilisateur, communaute=communaute
            ).exclude(pk=getattr(self.instance, "pk", None)).exists():
                raise serializers.ValidationError(
                    "Cet utilisateur a déjà un rôle dans cette communauté."
                )
        return attrs


class SignalementSerializer(serializers.ModelSerializer):
    """
    Signalement de contenu.

    Le statut est en lecture seule ici : il ne peut être modifié que par
    un modérateur de la communauté via l'action « traiter ».
    """

    utilisateur = UtilisateurCompactSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), allow_null=True, required=False
    )
    commentaire = serializers.PrimaryKeyRelatedField(
        queryset=Commentaire.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Signalement
        fields = (
            "id",
            "utilisateur",
            "post",
            "commentaire",
            "raison",
            "date_creation",
            "statut",
        )
        read_only_fields = ("id", "utilisateur", "date_creation", "statut")

    def validate(self, attrs):
        """Un signalement doit cibler au moins un post ou un commentaire."""
        if not (attrs.get("post") or attrs.get("commentaire")):
            raise serializers.ValidationError(
                "Un signalement doit cibler un post ou un commentaire."
            )
        return attrs
