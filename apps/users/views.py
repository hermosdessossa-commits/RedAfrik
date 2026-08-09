"""Vues de l'app users : inscription, déconnexion et profils."""

from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema

from apps.communities.serializers import CommunauteSerializer
from .models import User
from .serializers import (
    InscriptionSerializer,
    ProfilSerializer,
    UtilisateurSerializer,
)


def obtenir_tokens(utilisateur):
    """Génère la paire de jetons JWT (accès + rafraîchissement) pour un utilisateur."""
    refresh = RefreshToken.for_user(utilisateur)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class DeconnexionSerializer(serializers.Serializer):
    """Corps de requête et de réponse de la déconnexion."""

    refresh = serializers.CharField()
    detail = serializers.CharField(required=False)


class ConnexionView(TokenObtainPairView):
    """
    POST /api/auth/connexion/

    Échange {username, password} contre une paire de jetons JWT.
    Débit limité (scope « connexion ») pour contrer le brute-force.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"


class InscriptionView(generics.CreateAPIView):
    """
    POST /api/auth/inscription/

    Crée un compte et retourne directement les jetons JWT
    (l'utilisateur est connecté dès son inscription).
    Débit limité (scope « inscription ») pour limiter les comptes robots.
    """

    serializer_class = InscriptionSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "inscription"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save()
        return Response(
            {
                "utilisateur": UtilisateurSerializer(
                    utilisateur, context={"request": request}
                ).data,
                **obtenir_tokens(utilisateur),
            },
            status=status.HTTP_201_CREATED,
        )


class DeconnexionView(APIView):
    """
    POST /api/auth/deconnexion/

    Révoque (blackliste) le jeton de rafraîchissement fourni.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DeconnexionSerializer,
        responses={200: DeconnexionSerializer},
        tags=["authentification"],
    )
    def post(self, request):
        try:
            refresh = RefreshToken(request.data.get("refresh"))
            refresh.blacklist()
        except TokenError:
            raise ValidationError(
                {"refresh": "Jeton de rafraîchissement invalide ou déjà révoqué."}
            )
        return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)


class UtilisateurViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Liste et consultation des profils publics, plus les actions personnelles
    « moi » et « profil » pour l'utilisateur connecté.

    Routes :
    - GET    /api/utilisateurs/
    - GET    /api/utilisateurs/{id}/
    - GET    /api/utilisateurs/moi/
    - GET    /api/utilisateurs/profil/  et  PUT/PATCH (bio, avatar)
    - GET    /api/utilisateurs/abonnements/
    """

    queryset = User.objects.all()
    serializer_class = UtilisateurSerializer
    lookup_field = "pk"
    # Recherche par nom d'utilisateur ou e-mail (ex : nomination d'un modérateur)
    search_fields = ("username", "email")
    # Le lookup ne porte que sur des identifiants numériques, pour ne pas
    # entrer en conflit avec les actions « moi », « profil » et « abonnements ».
    lookup_value_regex = r"[0-9]+"

    def get_permissions(self):
        """Les actions personnelles exigent l'authentification."""
        if self.action in ("moi", "profil", "abonnements"):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        from django.db.models import Count

        return (
            super()
            .get_queryset()
            .annotate(
                nombre_posts=Count("posts", distinct=True),
                nombre_commentaires=Count("commentaires", distinct=True),
                nombre_abonnements=Count("abonnements", distinct=True),
            )
        )

    @action(detail=False, methods=["get"])
    def moi(self, request):
        """Profil complet de l'utilisateur connecté."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "put", "patch"])
    def profil(self, request):
        """Consultation et mise à jour du profil personnel (bio, avatar)."""
        if request.method == "GET":
            return Response(ProfilSerializer(request.user).data)
        serializer = ProfilSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def abonnements(self, request):
        """Communautés auxquelles l'utilisateur connecté est abonné."""
        communautes = request.user.abonnements.select_related("communaute").values_list(
            "communaute__nom", flat=True
        )
        return Response({"abonnements": list(communautes)})
