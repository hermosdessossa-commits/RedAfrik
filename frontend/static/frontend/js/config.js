/* --------------------------------------------------------------------------
   Configuration de la SPA RedAfrik.
   Sur le déploiement Vercel, scripts/vercel_build.sh remplace ce fichier par
   une version pointant vers l'API (variable REDAFRIK_API_URL). En local
   (servi par Django), l'API est accessible au même hôte, sous /api/.
   -------------------------------------------------------------------------- */

window.REDAFRIK_API = window.REDAFRIK_API || "/api/";
