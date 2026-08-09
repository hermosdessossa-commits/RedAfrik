"""Routes de l'app users : authentification JWT et profils."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import ConnexionView, DeconnexionView, InscriptionView, UtilisateurViewSet

router = DefaultRouter()
router.register("utilisateurs", UtilisateurViewSet, basename="utilisateur")

urlpatterns = [
    # --- Authentification ----------------------------------------------------
    path("auth/inscription/", InscriptionView.as_view(), name="inscription"),
    # Connexion : POST {username, password} -> {access, refresh}
    path("auth/connexion/", ConnexionView.as_view(), name="connexion"),
    # Rafraîchissement : POST {refresh} -> {access}
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    # Déconnexion : POST {refresh} (révoque le jeton)
    path("auth/deconnexion/", DeconnexionView.as_view(), name="deconnexion"),
    # --- Profils -------------------------------------------------------------
    *router.urls,
]
