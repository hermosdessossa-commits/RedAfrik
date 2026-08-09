"""Serializers de l'app communities."""

from django.db import transaction
from rest_framework import serializers

from apps.moderation.models import Moderateur
from apps.users.serializers import UtilisateurCompactSerializer
from .models import Abonnement, Communaute


class CommunauteSerializer(serializers.ModelSerializer):
    """
    Serializer des communautés.

    À la création, le créateur devient automatiquement administrateur
    de la communauté (création d'un enregistrement Moderateur).
    """

    createur = UtilisateurCompactSerializer(read_only=True)
    nombre_abonnes = serializers.SerializerMethodField()
    nombre_posts = serializers.SerializerMethodField()
    est_abonne = serializers.SerializerMethodField()
    est_moderateur = serializers.SerializerMethodField()
    est_administrateur = serializers.SerializerMethodField()
    role = serializers.CharField(source="mon_role", read_only=True, default=None)

    class Meta:
        model = Communaute
        fields = (
            "id",
            "nom",
            "description",
            "image_url",
            "createur",
            "date_creation",
            "nombre_abonnes",
            "nombre_posts",
            "est_abonne",
            "est_moderateur",
            "est_administrateur",
            "role",
        )
        read_only_fields = ("id", "createur", "date_creation")

    def _valeur_ou_zero(self, obj, champ):
        # Les compteurs sont annotés dans le queryset de la vue (efficacité) ;
        # en l'absence d'annotation, on retombe sur 0.
        return getattr(obj, champ, None) or 0

    def get_nombre_abonnes(self, obj) -> int:
        return self._valeur_ou_zero(obj, "nombre_abonnes")

    def get_nombre_posts(self, obj) -> int:
        return self._valeur_ou_zero(obj, "nombre_posts")

    def get_est_abonne(self, obj) -> bool:
        valeur = getattr(obj, "est_abonne", None)
        if valeur is not None:
            return valeur
        # Sans annotation (cas du POST de création), un abonnement ne peut pas
        # encore exister pour une communauté qui vient d'être créée.
        return False

    def _mon_role(self, obj):
        # Rôle annoté par la vue (efficace) ; en l'absence d'annotation
        # (réponse de création), interroge directement la table.
        role = getattr(obj, "mon_role", None)
        if role is not None:
            return role
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return (
            Moderateur.objects.filter(utilisateur=request.user, communaute=obj)
            .values_list("role", flat=True)
            .first()
        )

    def get_est_moderateur(self, obj) -> bool:
        return self._mon_role(obj) is not None

    def get_est_administrateur(self, obj) -> bool:
        return self._mon_role(obj) == Moderateur.Role.ADMINISTRATEUR

    def create(self, validated_data):
        """Crée la communauté et nomme son créateur administrateur (transaction)."""
        createur = self.context["request"].user
        with transaction.atomic():
            communaute = Communaute.objects.create(
                createur=createur, **validated_data
            )
            Moderateur.objects.create(
                utilisateur=createur,
                communaute=communaute,
                role=Moderateur.Role.ADMINISTRATEUR,
            )
        return communaute


class AbonnementSerializer(serializers.ModelSerializer):
    """Abonnement d'un utilisateur à une communauté."""

    communaute = serializers.SlugRelatedField(slug_field="nom", read_only=True)

    class Meta:
        model = Abonnement
        fields = ("id", "communaute", "date_abonnement")
        read_only_fields = fields
