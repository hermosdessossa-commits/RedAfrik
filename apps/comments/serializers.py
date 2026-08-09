"""Serializers de l'app comments, avec construction de l'arborescence."""

from typing import Optional

from rest_framework import serializers

from apps.posts.models import Post
from apps.users.serializers import UtilisateurCompactSerializer
from .models import Commentaire


class CommentaireSerializer(serializers.ModelSerializer):
    """
    Serializer des commentaires.

    Les réponses sont imbriquées récursivement dans « reponses ». Pour
    éviter les requêtes N+1, la vue construit en une seule requête un
    dictionnaire parent -> enfants, transmis via le contexte « arbre ».
    """

    auteur = UtilisateurCompactSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())
    commentaire_parent = serializers.PrimaryKeyRelatedField(
        queryset=Commentaire.objects.all(), allow_null=True, required=False
    )
    score = serializers.IntegerField(read_only=True)
    vote_actuel = serializers.SerializerMethodField()
    reponses = serializers.SerializerMethodField()

    class Meta:
        model = Commentaire
        fields = (
            "id",
            "contenu",
            "auteur",
            "post",
            "commentaire_parent",
            "score",
            "vote_actuel",
            "date_creation",
            "reponses",
        )
        read_only_fields = ("id", "auteur", "score", "date_creation")

    def validate(self, attrs):
        """Le post est immuable ; le parent doit appartenir au même post."""
        # Un commentaire ne change jamais de post : le déplacer casserait
        # la cohérence de l'arborescence et du filtre « ?post= ».
        if self.instance is not None and "post" in attrs:
            raise serializers.ValidationError(
                {"post": "Le post d'un commentaire ne peut pas être modifié."}
            )
        post = attrs.get("post") or (self.instance.post if self.instance else None)
        parent = attrs.get("commentaire_parent")
        if parent and post and parent.post_id != post.id:
            raise serializers.ValidationError(
                {"commentaire_parent": "Le commentaire parent doit appartenir au même post."}
            )
        return attrs

    def get_vote_actuel(self, obj) -> Optional[int]:
        return getattr(obj, "vote_actuel", None)

    def get_reponses(self, obj) -> list:
        arbre = self.context.get("arbre")
        if arbre is None:
            return []
        enfants = arbre.get(obj.id, [])
        return CommentaireSerializer(
            enfants, many=True, context=self.context
        ).data
