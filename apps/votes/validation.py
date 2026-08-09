"""Validation partagée des votes (posts et commentaires)."""

from rest_framework.exceptions import ValidationError


def valider_valeur_vote(request) -> int:
    """Extrait et valide le champ « valeur » d'une requête de vote (1 ou -1)."""
    try:
        valeur = int(request.data.get("valeur"))
    except (TypeError, ValueError):
        raise ValidationError({"valeur": "La valeur du vote doit être 1 ou -1."}) from None
    if valeur not in (1, -1):
        raise ValidationError({"valeur": "La valeur du vote doit être 1 ou -1."})
    return valeur
