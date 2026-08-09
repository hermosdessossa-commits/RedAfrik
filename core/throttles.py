"""Limitation du débit des requêtes en écriture (protection du système)."""

from rest_framework.throttling import ScopedRateThrottle

METHODES_ECRITURE = ("POST", "PUT", "PATCH")


class ThrottleEcriture:
    """
    Applique le débit « creation » (voir DEFAULT_THROTTLE_RATES) à toute
    requête en écriture du viewset qui hérite de ce mixin.
    """

    throttle_scope = "creation"

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.request and self.request.method in METHODES_ECRITURE:
            throttles.append(ScopedRateThrottle())
        return throttles