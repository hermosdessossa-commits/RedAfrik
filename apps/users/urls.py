"""Routes de l'app users : authentification JWT et profils."""

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ConfirmationResetMotDePasseView,
    ConnexionView,
    DeconnexionView,
    DemandeResetMotDePasseView,
    InscriptionView,
    UtilisateurViewSet,
    VerifierEmailView,
)

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
    # Sécurité du compte
    path("auth/verifier-email/", VerifierEmailView.as_view(), name="verifier-email"),
    path(
        "auth/verifier-email/<str:jeton>/",
        VerifierEmailView.as_view(),
        name="verifier-email-jeton",
    ),
    path(
        "auth/reinitialiser-mdp/",
        DemandeResetMotDePasseView.as_view(),
        name="reinitialiser-mdp",
    ),
    path(
        "auth/reinitialiser-mdp/confirmer/",
        ConfirmationResetMotDePasseView.as_view(),
        name="reinitialiser-mdp-confirmer",
    ),
    # --- Profils -------------------------------------------------------------
    *router.urls,
]
