"""Serializers de l'app users : inscription et profils."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class InscriptionSerializer(serializers.ModelSerializer):
    """Inscription d'un nouvel utilisateur (mot de passe écrit uniquement)."""

    mot_de_passe = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    mot_de_passe_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "mot_de_passe", "mot_de_passe_confirmation")

    def validate(self, attrs):
        if attrs["mot_de_passe"] != attrs["mot_de_passe_confirmation"]:
            raise serializers.ValidationError(
                {"mot_de_passe_confirmation": "Les mots de passe ne correspondent pas."}
            )
        return attrs

    def create(self, validated_data):
        # create_user hashe le mot de passe avec l'algorithme natif de Django
        mot_de_passe = validated_data.pop("mot_de_passe")
        validated_data.pop("mot_de_passe_confirmation")
        return User.objects.create_user(password=mot_de_passe, **validated_data)


class UtilisateurCompactSerializer(serializers.ModelSerializer):
    """Représentation légère d'un utilisateur, embarquée dans les autres ressources."""

    class Meta:
        model = User
        fields = ("id", "username", "avatar_url", "karma")
        read_only_fields = fields


class UtilisateurSerializer(serializers.ModelSerializer):
    """Profil complet d'un utilisateur, avec ses statistiques communautaires."""

    nombre_posts = serializers.SerializerMethodField()
    nombre_commentaires = serializers.SerializerMethodField()
    nombre_abonnements = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "bio",
            "avatar_url",
            "karma",
            "date_creation",
            "nombre_posts",
            "nombre_commentaires",
            "nombre_abonnements",
        )
        read_only_fields = ("id", "email", "karma", "date_creation")

    def _annotee_ou_comptee(self, obj, champ):
        """Privilégie l'annotation faite en base, sinon compte à la volée."""
        valeur = getattr(obj, champ, None)
        if valeur is not None:
            return valeur
        return getattr(obj, champ.replace("nombre_", "").replace("_", "")).count()

    def get_nombre_posts(self, obj) -> int:
        return self._annotee_ou_comptee(obj, "nombre_posts")

    def get_nombre_commentaires(self, obj) -> int:
        return self._annotee_ou_comptee(obj, "nombre_commentaires")

    def get_nombre_abonnements(self, obj) -> int:
        return self._annotee_ou_comptee(obj, "nombre_abonnements")


class ProfilSerializer(serializers.ModelSerializer):
    """Mise à jour du profil personnel (bio et avatar uniquement)."""

    class Meta:
        model = User
        fields = ("bio", "avatar_url")
