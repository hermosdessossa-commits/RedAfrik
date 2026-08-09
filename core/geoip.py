"""Géolocalisation des adresses IP via la base GeoLite2 (MaxMind).

La base n'est pas versionnée : placez un fichier GeoLite2-City.mmdb au
chemin indiqué par GEOIP_DB_PATH (défaut : data/GeoLite2-City.mmdb).
Le lecteur est ouvert paresseusement à la première requête publique ; sans
base, toutes les adresses renvoient None sans jamais lever d'erreur.
"""

import ipaddress
from pathlib import Path

from django.conf import settings

try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError

    _GEOIP2_DISPONIBLE = True
except ImportError:  # base optionnelle : le site fonctionne sans
    _GEOIP2_DISPONIBLE = False
    AddressNotFoundError = ValueError

_lecteur = None
_tentative = False


def geolocaliser(adresse_ip):
    """
    Retourne un dictionnaire {pays, code_pays, region, ville, latitude,
    longitude, fuseau_horaire} si l'adresse est publique et couverte par la
    base ; sinon None (IP privées, locales, réservées ou base absente).
    """
    if not _GEOIP2_DISPONIBLE or not adresse_ip:
        return None
    try:
        ip = ipaddress.ip_address(adresse_ip)
    except ValueError:
        return None
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return None
    lecteur = _obtenir_lecteur()
    if lecteur is None:
        return None
    try:
        reponse = lecteur.city(adresse_ip)
    except (AddressNotFoundError, ValueError):
        return None
    return {
        "pays": reponse.country.name,
        "code_pays": reponse.country.iso_code,
        "region": reponse.subdivisions.most_specific.name,
        "ville": reponse.city.name,
        "latitude": reponse.location.latitude,
        "longitude": reponse.location.longitude,
        "fuseau_horaire": reponse.location.time_zone,
    }


def masquer_ip(adresse_ip):
    """
    Masque partiellement une adresse IP pour les voyeurs non superutilisateurs
    (IPv4 : dernier octet ; IPv6 : les 16 derniers bits), ou None si absente.
    """
    if not adresse_ip:
        return None
    try:
        ip = ipaddress.ip_address(adresse_ip)
    except ValueError:
        return str(adresse_ip)
    if ip.version == 4:
        parties = str(ip).split(".")
        return ".".join(parties[:-1]) + ".***"
    return ":".join(str(ip).split(":")[:-1]) + ":****"


def _obtenir_lecteur():
    """Ouvre le lecteur GeoLite2 une seule fois par processus (échec silencieux)."""
    global _lecteur, _tentative
    if _lecteur is None and not _tentative:
        _tentative = True
        chemin = Path(getattr(settings, "GEOIP_DB_PATH", ""))
        if chemin.is_file():
            try:
                _lecteur = geoip2.database.Reader(str(chemin))
            except (OSError, ValueError):
                _lecteur = None
    return _lecteur