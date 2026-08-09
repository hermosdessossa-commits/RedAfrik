"""Formatteur de logs JSON pour la production (ingestion par collecteur)."""

import json
import logging


class FormateurJson(logging.Formatter):
    """Sérialise chaque enregistrement en une ligne JSON (une par événement)."""

    def format(self, record):
        entree = {
            "horodatage": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "niveau": record.levelname,
            "journal": record.name,
            "message": record.getMessage(),
        }
        for clef in ("adresse_ip", "utilisateur", "methode", "chemin", "statut"):
            valeur = record.__dict__.get(clef)
            if valeur is not None:
                entree[clef] = valeur
        if record.exc_info:
            entree["exception"] = self.formatException(record.exc_info)
        return json.dumps(entree, ensure_ascii=False)