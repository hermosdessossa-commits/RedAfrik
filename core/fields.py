"""Champs DRF partagés : import d'images avec validation préalable."""

from rest_framework import serializers

from core.validateurs import valider_image_upload


class ImageImporteeField(serializers.ImageField):
    """
    Champ image DRF : valide l'extension, la taille et l'intégrité
    avant le traitement DRF, pour des messages d'erreur clairs.
    """

    def to_internal_value(self, data):
        valider_image_upload(data)
        return super().to_internal_value(data)
