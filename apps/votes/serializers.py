"""Serializers de l'app votes (utilisés par les actions « voter »)."""

from rest_framework import serializers

from .models import VoteCommentaire, VotePost

VALEURS_VOTE = (1, -1)


class VotePostSerializer(serializers.ModelSerializer):
    """Représentation d'un vote de post."""

    class Meta:
        model = VotePost
        fields = ("id", "post", "valeur", "date_vote")
        read_only_fields = ("id", "date_vote")

    def validate_valeur(self, valeur):
        if valeur not in VALEURS_VOTE:
            raise serializers.ValidationError("La valeur du vote doit être 1 ou -1.")
        return valeur


class VoteCommentaireSerializer(serializers.ModelSerializer):
    """Représentation d'un vote de commentaire."""

    class Meta:
        model = VoteCommentaire
        fields = ("id", "commentaire", "valeur", "date_vote")
        read_only_fields = ("id", "date_vote")

    def validate_valeur(self, valeur):
        if valeur not in VALEURS_VOTE:
            raise serializers.ValidationError("La valeur du vote doit être 1 ou -1.")
        return valeur
