"""Validateurs partagés : contrôle des fichiers image importés."""

from django.core.exceptions import ValidationError
from django.core.files import File
from PIL import Image

TAILLE_MAX_IMAGE = 5 * 1024 * 1024  # 5 Mo
EXTENSIONS_AUTORISEES = {"jpg", "jpeg", "png", "gif", "webp"}


def valider_image_upload(fichier: File) -> None:
    """
    Vérifie l'extension, la taille et l'intégrité d'une image importée.

    S'applique aux champs ImageField (uploads de posts, bannières, avatars).
    """
    nom = (fichier.name or "").lower()
    extension = nom.rsplit(".", 1)[-1] if "." in nom else ""
    if extension not in EXTENSIONS_AUTORISEES:
        raise ValidationError(
            "Format d'image non pris en charge. Utilisez JPG, PNG, GIF ou WebP."
        )
    if getattr(fichier, "size", 0) > TAILLE_MAX_IMAGE:
        raise ValidationError("L'image ne doit pas dépasser 5 Mo.")
    try:
        fichier.seek(0)
        with Image.open(fichier) as image:
            image.verify()
        fichier.seek(0)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError("Le fichier envoyé n'est pas une image valide.") from None
