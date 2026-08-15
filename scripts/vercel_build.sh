#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Build du frontend RedAfrik pour Vercel (SPA statique).
#
# - copie index.html, le CSS et le JS dans public/
# - génère config.js avec l'URL de l'API (variable d'environnement
#   REDAFRIK_API_URL, par défaut "/api/" — même hôte).
#
# À configurer dans le panneau Vercel (Environment Variables) :
#   REDAFRIK_API_URL=https://votre-api.onrender.com/api/
# -----------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

DEST="public"
rm -rf "$DEST"
mkdir -p "$DEST/static/frontend/js" "$DEST/static/frontend/css" "$DEST/static/frontend/img"

cp frontend/templates/frontend/index.html   "$DEST/index.html"
cp frontend/static/frontend/css/style.css   "$DEST/static/frontend/css/"
cp frontend/static/frontend/js/app.js       "$DEST/static/frontend/js/"
cp frontend/static/frontend/img/*           "$DEST/static/frontend/img/"

API_URL="${REDAFRIK_API_URL:-/api/}"
python3 - "$API_URL" > "$DEST/static/frontend/js/config.js" <<'PY'
import json
import sys
print("window.REDAFRIK_API = %s;" % json.dumps(sys.argv[1]))
PY

echo "Frontend prêt dans $DEST/ (API : $API_URL)"
