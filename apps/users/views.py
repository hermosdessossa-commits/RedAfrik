"""Vues de l'app users : inscription, déconnexion, profils et sécurité du compte."""

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core import securite
from core.mail import envoyer_reset_mot_de_passe, envoyer_verification_email
from core.throttles import ThrottleEcriture

from .models import JetonSecurite, User
from .serializers import (
    ChangementMotDePasseSerializer,
    ConfirmationResetSerializer,
    DemandeResetSerializer,
    InscriptionSerializer,
    ProfilSerializer,
    SuppressionCompteSerializer,
    UtilisateurPublicSerializer,
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


def _clef_ip(request) -> str:
    """Clé de verrouillage fondée sur l'adresse IP du client."""
    return "ip:" + request.META.get("REMOTE_ADDR", "")


def _creer_jeton(utilisateur, but, duree_heures: int) -> str:
    """Crée un jeton de sécurité et retourne sa valeur claire (pour l'e-mail)."""
    _, valeur = JetonSecurite.creer(utilisateur, but, duree_heures)
    return valeur


class ConnexionView(TokenObtainPairView):
    """
    POST /api/auth/connexion/

    Échange {username, password} contre une paire de jetons JWT.
    Débit limité (scope « connexion ») et verrouillage temporaire après
    plusieurs échecs (par nom d'utilisateur et par adresse IP).
    """

    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "connexion"

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "")
        for clef in (username, _clef_ip(request)):
            if securite.est_verrouille(clef):
                raise AuthenticationFailed(
                    "Trop de tentatives de connexion. Réessayez dans quelques minutes."
                )
        try:
            reponse = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            securite.noter_echec(username)
            securite.noter_echec(_clef_ip(request))
            raise
        securite.reinitialiser_echecs(username)
        securite.reinitialiser_echecs(_clef_ip(request))
        return reponse


class InscriptionView(generics.CreateAPIView):
    """
    POST /api/auth/inscription/

    Crée un compte et retourne directement les jetons JWT
    (l'utilisateur est connecté dès son inscription).
    Débit limité (scope « inscription ») pour limiter les comptes robots.
    """

    serializer_class = InscriptionSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "inscription"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save()
        envoyer_verification_email(
            utilisateur, _creer_jeton(utilisateur, "verification", 24)
        )
        return Response(
            {
                "utilisateur": UtilisateurSerializer(
                    utilisateur, context={"request": request}
                ).data,
                **obtenir_tokens(utilisateur),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifierEmailView(APIView):
    """
    POST /api/auth/verifier-email/           renvoie un nouveau lien
    POST /api/auth/verifier-email/{jeton}/   valide l'adresse e-mail
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request, jeton=None):
        if jeton is None:
            utilisateur = request.user if request.user.is_authenticated else None
            if utilisateur is None:
                raise ValidationError(
                    {"detail": "Vous devez être connecté pour renvoyer un lien."}
                )
            if utilisateur.email_verifie:
                return Response({"detail": "Adresse déjà vérifiée."})
            envoyer_verification_email(
                utilisateur, _creer_jeton(utilisateur, "verification", 24)
            )
            return Response({"detail": "Lien de vérification envoyé."})
        jeton_obj = (
            JetonSecurite.objects.filter(
                but="verification", jeton_hache=JetonSecurite._hacher(jeton)
            )
            .select_related("utilisateur")
            .first()
        )
        if jeton_obj is None or not jeton_obj.verifier(jeton):
            raise ValidationError({"detail": "Lien de vérification invalide ou expiré."})
        jeton_obj.utilisateur.email_verifie = True
        jeton_obj.utilisateur.save(update_fields=["email_verifie"])
        return Response({"detail": "Adresse e-mail vérifiée."})


class DemandeResetMotDePasseView(APIView):
    """
    POST /api/auth/reinitialiser-mdp/

    Envoie un lien de réinitialisation par e-mail (réponse neutre pour ne
    pas révéler l'existence d'un compte).
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "connexion"

    @extend_schema(
        request=DemandeResetSerializer,
        responses={200: DemandeResetSerializer},
        tags=["authentification"],
    )
    def post(self, request):
        serializer = DemandeResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = User.objects.filter(email=serializer.validated_data["email"]).first()
        if utilisateur is not None:
            envoyer_reset_mot_de_passe(
                utilisateur, _creer_jeton(utilisateur, "reset_mot_de_passe", 1)
            )
        return Response({"detail": "Si ce compte existe, un lien vient d'être envoyé."})


class ConfirmationResetMotDePasseView(APIView):
    """
    POST /api/auth/reinitialiser-mdp/confirmer/

    Valide le jeton reçu par e-mail et applique le nouveau mot de passe.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "connexion"

    @extend_schema(
        request=ConfirmationResetSerializer,
        responses={200: ConfirmationResetSerializer},
        tags=["authentification"],
    )
    def post(self, request):
        serializer = ConfirmationResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jeton = serializer.validated_data["jeton"]
        jeton_obj = (
            JetonSecurite.objects.filter(
                but="reset_mot_de_passe", jeton_hache=JetonSecurite._hacher(jeton)
            )
            .select_related("utilisateur")
            .first()
        )
        if jeton_obj is None or not jeton_obj.verifier(jeton):
            raise ValidationError(
                {"detail": "Lien de réinitialisation invalide ou expiré."}
            )
        jeton_obj.utilisateur.set_password(
            serializer.validated_data["nouveau_mot_de_passe"]
        )
        jeton_obj.utilisateur.save(update_fields=["password"])
        return Response({"detail": "Mot de passe réinitialisé."})


class DeconnexionView(APIView):
    """
    POST /api/auth/deconnexion/

    Révoque (blackliste) le jeton de rafraîchissement fourni.
    """

    permission_classes = (permissions.IsAuthenticated,)

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
            ) from None
        return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)


class UtilisateurViewSet(ThrottleEcriture, viewsets.ReadOnlyModelViewSet):
    """
    Liste et consultation des profils publics, plus les actions personnelles
    « moi », « profil », « abonnements », « mdp » et « supprimer-compte »
    pour l'utilisateur connecté.

    Routes :
    - GET    /api/utilisateurs/
    - GET    /api/utilisateurs/{id}/
    - GET    /api/utilisateurs/moi/
    - GET    /api/utilisateurs/profil/  et  PUT/PATCH (bio, avatar, username, email)
    - POST   /api/utilisateurs/mdp/          changer son mot de passe
    - DELETE /api/utilisateurs/supprimer-compte/   supprimer définitivement le compte
    - GET    /api/utilisateurs/abonnements/
    """

    queryset = User.objects.all()
    serializer_class = UtilisateurPublicSerializer
    lookup_field = "pk"
    # Recherche par nom d'utilisateur ou e-mail (ex : nomination d'un modérateur)
    search_fields = ("username", "email")
    # Le lookup ne porte que sur des identifiants numériques, pour ne pas
    # entrer en conflit avec les actions « moi », « profil » et « abonnements ».
    lookup_value_regex = r"[0-9]+"

    def get_serializer_class(self):
        """Le profil personnel expose l'e-mail ; les profils publics ne le diffusent jamais."""
        if self.action == "moi":
            return UtilisateurSerializer
        return UtilisateurPublicSerializer

    def get_permissions(self):
        """Les actions personnelles exigent l'authentification."""
        if self.action in ("moi", "profil", "abonnements", "mdp", "supprimer_compte"):
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
        """Consultation et mise à jour du profil personnel."""
        if request.method == "GET":
            return Response(ProfilSerializer(request.user).data)
        serializer = ProfilSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="mdp")
    def mdp(self, request):
        """Change le mot de passe du compte connecté (ancien mot de passe requis)."""
        serializer = ChangementMotDePasseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(
            serializer.validated_data["ancien_mot_de_passe"]
        ):
            raise ValidationError(
                {"ancien_mot_de_passe": "Le mot de passe actuel est incorrect."}
            )
        request.user.set_password(serializer.validated_data["nouveau_mot_de_passe"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Mot de passe modifié."})

    @action(detail=False, methods=["delete"], url_path="supprimer-compte")
    def supprimer_compte(self, request):
        """
        Supprime définitivement le compte : ses posts, commentaires,
        communautés créées et rôles de modération disparaissent.
        """
        serializer = SuppressionCompteSerializer(
            data=request.data, context={"request": request}
        )
        serializer.instance = request.user
        serializer.is_valid(raise_exception=True)
        request.user.delete()
        return Response(
            {"detail": "Votre compte a été supprimé définitivement."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def abonnements(self, request):
        """Communautés auxquelles l'utilisateur connecté est abonné."""
        communautes = request.user.abonnements.select_related("communaute").values_list(
            "communaute__nom", flat=True
        )
        return Response({"abonnements": list(communautes)})