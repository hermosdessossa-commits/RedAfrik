#!/usr/bin/env bash
# Prépare la base dédiée aux tests e2e (redafrik_e2e) puis y applique les
# migrations. Exécuté automatiquement par Playwright avant le runserver.
set -euo pipefail

cd "$(dirname "$0")/.."

export PGPASSWORD="${DB_PASSWORD:-redafrik}"

if ! psql -p 5433 -h localhost -U redafrik -lqt | cut -d '|' -f 1 | grep -qw redafrik_e2e; then
  createdb -p 5433 -h localhost -U redafrik redafrik_e2e
fi

.venv/bin/python manage.py migrate --settings=config.settings_e2e --no-input &>/dev/null || \
  .venv/bin/python manage.py migrate --settings=config.settings_e2e

# Base vierge et reproductible : recharge l'état de départ avant chaque lancé
.venv/bin/python manage.py flush --noinput --settings=config.settings_e2e

# Jeu de données de démonstration, prévisible pour les scénarios
.venv/bin/python manage.py seed --settings=config.settings_e2e --reset &>/dev/null || \
  .venv/bin/python manage.py seed --settings=config.settings_e2e

echo "Base e2e prête."