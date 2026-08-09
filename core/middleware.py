"""Middleware de journalisation des actions : IP + géolocalisation.

Chaque requête HTTP est enregistrée dans JournalAction après la réponse
(l'utilisateur est résolu depuis le jeton JWT) ; en cas d'exception, la
trace est écrite avec un statut 500 et l'exception est relancée.

La confiance accordée à l'en-tête X-Forwarded-For est strictement limitée
aux adresses déclarées dans TRUSTED_PROXY_IPS (anti-spoofing).
"""

import logging

from django.conf import settings

from .geoip import geolocaliser
from .models import JournalAction

journal = logging.getLogger("redafrik.actions")


class JournalisationMiddleware:
    """Consigne l'adresse IP et la géolocalisation de chaque action."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "JOURNAL_ACTIONS_ENABLED", True):
            return self.get_response(request)
        try:
            reponse = self.get_response(request)
        except Exception:
            self._journaliser(request, 500)
            raise
        self._journaliser(request, getattr(reponse, "status_code", 500))
        return reponse

    def _journaliser(self, request, statut):
        chemin = request.path
        if self._exclure(chemin):
            return
        try:
            adresse_ip = self._adresse_ip(request)
            utilisateur = self._resoudre_utilisateur(request)
            # Compte supprimé par la requête elle-même (ex : supprimer-compte) :
            # l'instance n'a plus de clé primaire et ne peut plus référencer la FK.
            if utilisateur is not None and utilisateur.pk is None:
                utilisateur = None
            JournalAction.objects.create(
                utilisateur=utilisateur,
                methode=request.method,
                chemin=chemin[:300],
                statut=statut,
                adresse_ip=adresse_ip or None,
                agent=(request.META.get("HTTP_USER_AGENT") or "")[:400],
                geolocalisation=geolocaliser(adresse_ip),
            )
            journal.info(
                "%s %s %s", request.method, chemin, statut,
                extra={
                    "ip": adresse_ip,
                    "utilisateur": getattr(utilisateur, "username", None),
                    "methode": request.method,
                    "chemin": chemin,
                    "statut": statut,
                },
            )
        except Exception:  # noqa: BLE001 — la journalisation ne doit jamais casser l'API
            # Une défaillance de journalisation ne doit jamais casser l'API.
            journal.exception(
                "Échec de journalisation de %s %s", request.method, chemin
            )

    @staticmethod
    def _exclure(chemin):
        """Les assets (statiques, médias) ne sont pas des « actions »."""
        for prefixe in (
            settings.MEDIA_URL,
            settings.STATIC_URL,
            "/favicon",
        ):
            if chemin.startswith(prefixe):
                return True
        return False

    @staticmethod
    def _adresse_ip(request):
        """IP réelle : X-Forwarded-For n'est accepté que derrière un proxy connu."""
        ip_directe = (request.META.get("REMOTE_ADDR") or "").strip()
        if ip_directe in settings.TRUSTED_PROXY_IPS:
            en_tete = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
            if en_tete:
                return en_tete.split(",")[0].strip()
        return ip_directe

    @staticmethod
    def _resoudre_utilisateur(request):
        """Utilisateur du jeton JWT, même si la vue n'a pas été atteinte."""
        utilisateur = getattr(request, "user", None)
        if utilisateur is not None and utilisateur.is_authenticated:
            return utilisateur
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication

            couple = JWTAuthentication().authenticate(request)
        except Exception:  # noqa: BLE001 — jeton invalide, expiré ou utilisateur absent
            return None
        return couple[0] if couple else None