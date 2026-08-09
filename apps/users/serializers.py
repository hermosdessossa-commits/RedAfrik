"""Serializers de l'app users : inscription, profils et sécurité du compte."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from core.fields import ImageImporteeField

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

    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "avatar_url", "avatar", "karma")
        read_only_fields = fields


class UtilisateurSerializer(serializers.ModelSerializer):
    """Profil complet d'un utilisateur, avec ses statistiques communautaires."""

    nombre_posts = serializers.SerializerMethodField()
    nombre_commentaires = serializers.SerializerMethodField()
    nombre_abonnements = serializers.SerializerMethodField()
    email_verifie = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "bio",
            "avatar_url",
            "avatar",
            "email_verifie",
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


class UtilisateurPublicSerializer(UtilisateurSerializer):
    """
    Profil public : ne divulgue ni l'adresse e-mail ni le statut de
    vérification (données personnelles réservées à leur propriétaire).
    """

    class Meta(UtilisateurSerializer.Meta):
        fields = (
            "id",
            "username",
            "bio",
            "avatar_url",
            "avatar",
            "karma",
            "date_creation",
            "nombre_posts",
            "nombre_commentaires",
            "nombre_abonnements",
        )


class ProfilSerializer(serializers.ModelSerializer):
    """
    Mise à jour du profil personnel : bio, avatar, nom d'utilisateur et
    adresse e-mail (les changements d'identifiant restent libres tant que
    l'unicité est respectée).
    """

    email = serializers.EmailField(required=False)
    email_verifie = serializers.BooleanField(read_only=True)
    avatar = ImageImporteeField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ("username", "email", "bio", "avatar_url", "avatar", "email_verifie")

    def validate_username(self, valeur):
        if (
            valeur
            and User.objects.filter(username=valeur).exclude(pk=self.instance.pk).exists()
        ):
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return valeur

    def validate_email(self, valeur):
        if (
            valeur
            and User.objects.filter(email=valeur).exclude(pk=self.instance.pk).exists()
        ):
            raise serializers.ValidationError(
                "Cette adresse e-mail est déjà utilisée par un autre compte."
            )
        return valeur

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        # Un changement d'adresse invalide la vérification précédente.
        if "email" in self.validated_data:
            instance.email_verifie = False
            instance.save(update_fields=["email_verifie"])
        return instance


class ChangementMotDePasseSerializer(serializers.Serializer):
    """Changement du mot de passe d'un compte déjà connecté."""

    ancien_mot_de_passe = serializers.CharField(write_only=True)
    nouveau_mot_de_passe = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    confirmation = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["nouveau_mot_de_passe"] != attrs["confirmation"]:
            raise serializers.ValidationError(
                {"confirmation": "Les nouveaux mots de passe ne correspondent pas."}
            )
        return attrs


class DemandeResetSerializer(serializers.Serializer):
    """Demande d'un lien de réinitialisation par e-mail."""

    email = serializers.EmailField()


class ConfirmationResetSerializer(serializers.Serializer):
    """Validation du lien : nouveau mot de passe + jeton reçu par e-mail."""

    jeton = serializers.CharField(write_only=True)
    nouveau_mot_de_passe = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    confirmation = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["nouveau_mot_de_passe"] != attrs["confirmation"]:
            raise serializers.ValidationError(
                {"confirmation": "Les nouveaux mots de passe ne correspondent pas."}
            )
        return attrs


class SuppressionCompteSerializer(serializers.Serializer):
    """Confirmation de la suppression définitive du compte."""

    mot_de_passe = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if not self.instance.check_password(attrs["mot_de_passe"]):
            raise serializers.ValidationError(
                {"mot_de_passe": "Le mot de passe est incorrect."}
            )
        return attrs
