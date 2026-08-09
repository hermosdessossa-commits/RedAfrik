"""Envoi d'e-mails transactionnels (vérification, réinitialisation…).

Les messages passent par le backend configuré dans settings.EMAIL_BACKEND
(console en développement, SMTP en production). Tous les envois sont
enveloppés dans un try/except afin de ne jamais bloquer l'API en cas
d'échec de la messagerie.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _envoyer(subjet: str, template: str, contexte: dict, destinataire: str) -> bool:
    """Rend un template texte et l'envoie ; True si l'envoi a abouti."""
    try:
        message = render_to_string(f"emails/{template}.txt", contexte)
        send_mail(
            subject=subjet,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinataire],
            fail_silently=False,
        )
        return True
    except Exception:  # pragma: no cover - dépend du backend SMTP externe
        logger.exception("Échec d'envoi de l'e-mail « %s » à %s", subjet, destinataire)
        return False


def envoyer_verification_email(utilisateur, token_texte: str) -> bool:
    return _envoyer(
        "Vérifiez votre adresse e-mail — RedAfrik",
        "verification_email",
        {
            "utilisateur": utilisateur,
            "lien": settings.FRONTEND_URL + "/#/verifier-email/" + token_texte,
        },
        utilisateur.email,
    )


def envoyer_reset_mot_de_passe(utilisateur, token_texte: str) -> bool:
    return _envoyer(
        "Réinitialisation de votre mot de passe — RedAfrik",
        "reinitialisation_mdp",
        {
            "utilisateur": utilisateur,
            "lien": settings.FRONTEND_URL + "/#/reinitialiser-mdp/" + token_texte,
        },
        utilisateur.email,
    )
