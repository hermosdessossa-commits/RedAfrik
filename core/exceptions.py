"""
Gestionnaire d'exceptions unifié de l'API RedAfrik.

Toutes les erreurs retournent une structure JSON homogène :

    {"erreur": {"detail": "message global"}}          -> erreurs globales
    {"erreur": {"champ": ["message"]}}                -> erreurs de validation

Cela permet aux clients (frontend, applications mobiles) de traiter
toutes les erreurs de la même manière, quel que soit leur statut HTTP.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework.views import exception_handler


def redafrik_exception_handler(exc, context):
    """Normalise la réponse d'erreur produite par le gestionnaire DRF."""

    # Échec de récupération du contexte ? Délègue au gestionnaire par défaut.
    response = exception_handler(exc, context)
    if response is None:
        return response

    donnees = response.data

    # Limitation de débit (429) : message explicite en français
    if response.status_code == 429:
        donnees = {"detail": _("Trop de requêtes. Veuillez réessayer dans un instant.")}

    erreurs = donnees

    # Erreur globale avec un simple « detail » textuel
    if isinstance(donnees, dict) and isinstance(donnees.get("detail"), str):
        erreurs = {"detail": donnees["detail"]}

    # Les erreurs non liées à un champ précis (validate()) sont regroupées
    # sous la clé « global » au lieu de « non_field_errors ».
    if isinstance(erreurs, dict) and "non_field_errors" in erreurs:
        erreurs["global"] = erreurs.pop("non_field_errors")

    response.data = {"erreur": erreurs}
    return response
