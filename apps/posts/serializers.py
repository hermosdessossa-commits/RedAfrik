"""Serializers de l'app posts."""


from rest_framework import serializers

from apps.communities.models import Communaute
from apps.users.serializers import UtilisateurCompactSerializer
from core.fields import ImageImporteeField

from .models import Post


class PostSerializer(serializers.ModelSerializer):
    """
    Serializer des publications.

    - « communaute » s'écrit par son nom (slug), comme sur Reddit (r/nom).
    - Le vote de l'utilisateur connecté est exposé dans « vote_actuel ».
    """

    auteur = UtilisateurCompactSerializer(read_only=True)
    communaute = serializers.SlugRelatedField(
        slug_field="nom", queryset=Communaute.objects.all()
    )
    image = ImageImporteeField(required=False, allow_null=True)
    score = serializers.IntegerField(read_only=True)
    vote_actuel = serializers.SerializerMethodField()
    nombre_commentaires = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "titre",
            "contenu",
            "url_externe",
            "image_url",
            "image",
            "auteur",
            "communaute",
            "score",
            "nombre_commentaires",
            "vote_actuel",
            "date_creation",
            "date_modification",
        )
        read_only_fields = ("id", "auteur", "score", "date_creation", "date_modification")

    def validate(self, attrs):
        """Un post créé doit contenir au moins du texte, un lien ou une image.

        La règle ne s'applique qu'à la création : modifier le titre d'un post
        existant (ou un autre champ) ne doit pas exiger de nouveau contenu.
        """
        if self.instance is None:
            has_contenu = any(
                attrs.get(champ)
                for champ in ("contenu", "url_externe", "image_url", "image")
            )
            if not has_contenu:
                raise serializers.ValidationError(
                    "Un post doit contenir au moins du texte, un lien externe ou une image."
                )
        return attrs

    def get_vote_actuel(self, obj) -> int | None:
        # Valeur annotée en base par la vue (aucune requête supplémentaire)
        return getattr(obj, "vote_actuel", None)

    def get_nombre_commentaires(self, obj) -> int:
        return getattr(obj, "nombre_commentaires", None) or 0
