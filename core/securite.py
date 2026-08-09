"""Protection contre la force brute sur la connexion.

Un compteur d'échecs par clé (nom d'utilisateur, adresse IP) est conservé
en base ; après un nombre d'échecs dépassant le seuil dans la fenêtre, la
clé est verrouillée jusqu'à la fin de la fenêtre glissante.
"""

from datetime import timedelta

from django.utils import timezone

from apps.users.models import EchecConnexion

SEUIL_ECHECS = 6
FENETRE = timedelta(minutes=15)


def _depuis_debut_fenetre():
    return timezone.now() - FENETRE


def est_verrouille(clef: str) -> bool:
    """Vrai si la clé a dépassé le seuil d'échecs sur la fenêtre glissante."""
    if not clef:
        return False
    return (
        EchecConnexion.objects.filter(
            clef=clef, horodatage__gte=_depuis_debut_fenetre()
        ).count()
        >= SEUIL_ECHECS
    )


def noter_echec(clef: str) -> None:
    """Enregistre un échec et purge les traces périmées de la clé."""
    if not clef:
        return
    EchecConnexion.objects.filter(clef=clef, horodatage__lt=_depuis_debut_fenetre()).delete()
    EchecConnexion.objects.create(clef=clef)


def reinitialiser_echecs(clef: str) -> None:
    """Supprime l'historique d'échecs d'une clé (après une connexion réussie)."""
    if clef:
        EchecConnexion.objects.filter(clef=clef).delete()
