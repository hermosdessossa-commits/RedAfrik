"""Vue racine de l'API : index descriptif, journal des actions et santé."""

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .geoip import masquer_ip
from .models import JournalAction

INDEX_ENDPOINTS = [
    {
        "domaine": "Authentification",
        "endpoints": [
            {"methode": "POST", "path": "/api/auth/inscription/", "description": "Créer un compte (retourne les jetons JWT)"},
            {"methode": "POST", "path": "/api/auth/connexion/", "description": "Connexion {username, password} -> {access, refresh}"},
            {"methode": "POST", "path": "/api/auth/refresh/", "description": "Rafraîchir le jeton d'accès {refresh}"},
            {"methode": "POST", "path": "/api/auth/deconnexion/", "description": "Révoquer le jeton de rafraîchissement"},
            {"methode": "POST", "path": "/api/auth/verifier-email/", "description": "Renvoyer le lien de vérification d'e-mail"},
            {"methode": "POST", "path": "/api/auth/verifier-email/{jeton}/", "description": "Valider l'adresse e-mail avec le lien reçu"},
            {"methode": "POST", "path": "/api/auth/reinitialiser-mdp/", "description": "Demander un lien de réinitialisation {email}"},
            {"methode": "POST", "path": "/api/auth/reinitialiser-mdp/confirmer/", "description": "Réinitialiser le mot de passe {jeton, nouveau_mot_de_passe}"},
        ],
    },
    {
        "domaine": "Utilisateurs",
        "endpoints": [
            {"methode": "GET", "path": "/api/utilisateurs/", "description": "Classement des utilisateurs par karma (?search=)"},
            {"methode": "GET", "path": "/api/utilisateurs/{id}/", "description": "Profil public d'un utilisateur"},
            {"methode": "GET", "path": "/api/utilisateurs/moi/", "description": "Profil complet de l'utilisateur connecté"},
            {"methode": "GET/PUT/PATCH", "path": "/api/utilisateurs/profil/", "description": "Consulter / modifier son profil (bio, avatar, username, email)"},
            {"methode": "POST", "path": "/api/utilisateurs/mdp/", "description": "Changer son mot de passe {ancien_mot_de_passe, nouveau_mot_de_passe, confirmation}"},
            {"methode": "DELETE", "path": "/api/utilisateurs/supprimer-compte/", "description": "Supprimer définitivement son compte {mot_de_passe}"},
            {"methode": "GET", "path": "/api/utilisateurs/abonnements/", "description": "Communautés suivies par l'utilisateur connecté"},
        ],
    },
    {
        "domaine": "Communautés",
        "endpoints": [
            {"methode": "GET", "path": "/api/communautes/", "description": "Lister les communautés (?search=)"},
            {"methode": "POST", "path": "/api/communautes/", "description": "Créer une communauté (le créateur devient administrateur)"},
            {"methode": "GET", "path": "/api/communautes/{nom}/", "description": "Détail d'une communauté (abonnés, abonnement)"},
            {"methode": "PUT/PATCH/DELETE", "path": "/api/communautes/{nom}/", "description": "Modifier (créateur/admin) ou supprimer (créateur)"},
            {"methode": "POST/DELETE", "path": "/api/communautes/{nom}/abonner/", "description": "S'abonner / se désabonner"},
            {"methode": "GET", "path": "/api/communautes/tendances/", "description": "Communautés les plus suivies"},
        ],
    },
    {
        "domaine": "Publications",
        "endpoints": [
            {"methode": "GET", "path": "/api/posts/", "description": "Lister les posts (?communaute=, ?auteur=, ?tri=populaire, ?search=)"},
            {"methode": "POST", "path": "/api/posts/", "description": "Publier {titre, communaute, contenu|url_externe|image_url}"},
            {"methode": "PUT/PATCH/DELETE", "path": "/api/posts/{id}/", "description": "Modifier / supprimer (auteur ou modérateur)"},
            {"methode": "POST/DELETE", "path": "/api/posts/{id}/vote/", "description": "Voter {valeur: 1|-1} ou retirer son vote"},
        ],
    },
    {
        "domaine": "Commentaires",
        "endpoints": [
            {"methode": "GET", "path": "/api/commentaires/?post={id}", "description": "Arborescence des commentaires d'un post"},
            {"methode": "POST", "path": "/api/commentaires/", "description": "Commenter {contenu, post, commentaire_parent?}"},
            {"methode": "PUT/PATCH/DELETE", "path": "/api/commentaires/{id}/", "description": "Modifier / supprimer (auteur ou modérateur)"},
            {"methode": "POST/DELETE", "path": "/api/commentaires/{id}/vote/", "description": "Voter {valeur: 1|-1} ou retirer son vote"},
        ],
    },
    {
        "domaine": "Modération",
        "endpoints": [
            {"methode": "GET", "path": "/api/moderateurs/?communaute={nom}", "description": "Lister les modérateurs (modérateurs requis)"},
            {"methode": "POST", "path": "/api/moderateurs/", "description": "Nommer un modérateur (administrateurs requis)"},
            {"methode": "PATCH/DELETE", "path": "/api/moderateurs/{id}/", "description": "Changer le rôle / démettre (administrateurs requis)"},
            {"methode": "POST", "path": "/api/signalements/", "description": "Signaler un post ou un commentaire"},
            {"methode": "GET", "path": "/api/signalements/?communaute={nom}", "description": "Lister les signalements (modérateurs requis, ?statut=)"},
            {"methode": "POST", "path": "/api/signalements/{id}/traiter/", "description": "Résoudre / rejeter un signalement (modérateurs requis)"},
            {"methode": "DELETE", "path": "/api/signalements/{id}/", "description": "Supprimer un signalement (modérateurs requis)"},
        ],
    },
    {
        "domaine": "Administration",
        "endpoints": [
            {"methode": "GET", "path": "/api/actions/", "description": "Journal des actions : IP et géolocalisation (staff uniquement, ?utilisateur=, ?methode=, ?du=, ?au=, ?chemin=)"},
            {"methode": "GET", "path": "/api/sante/", "description": "Contrôle de santé (vérifie l'accès à la base de données)"},
        ],
    },
]


class JournalActionSerializer(serializers.ModelSerializer):
    """Sérialiseur du journal ; l'IP est masquée hors superutilisateurs."""

    utilisateur = serializers.CharField(
        source="utilisateur.username", read_only=True, default=None
    )
    adresse_ip = serializers.SerializerMethodField()

    class Meta:
        model = JournalAction
        fields = (
            "id",
            "utilisateur",
            "methode",
            "chemin",
            "statut",
            "adresse_ip",
            "geolocalisation",
            "date_creation",
        )

    def get_adresse_ip(self, obj):
        if self.context["request"].user.is_superuser:
            return obj.adresse_ip
        return masquer_ip(obj.adresse_ip)


class JournalActionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consultation du journal des actions (réservée au staff).

    Filtres : ?utilisateur={id}, ?methode=GET, ?chemin=posts,
    ?du=2026-01-01, ?au=2026-02-01.
    """

    serializer_class = JournalActionSerializer
    permission_classes = (permissions.IsAdminUser,)
    queryset = JournalAction.objects.select_related("utilisateur").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        utilisateur = params.get("utilisateur")
        if utilisateur:
            queryset = queryset.filter(utilisateur_id=utilisateur)
        methode = params.get("methode")
        if methode:
            queryset = queryset.filter(methode=methode.upper())
        chemin = params.get("chemin")
        if chemin:
            queryset = queryset.filter(chemin__icontains=chemin)
        du = params.get("du")
        if du:
            queryset = queryset.filter(date_creation__date__gte=du)
        au = params.get("au")
        if au:
            queryset = queryset.filter(date_creation__date__lte=au)
        return queryset


@extend_schema(
    responses={200: serializers.Serializer, 503: serializers.Serializer},
    tags=["racine"],
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def sante(request):
    """Contrôle de santé : vérifie l'accès à la base de données."""
    try:
        connection.ensure_connection()
    except DatabaseError:
        return Response(
            {"statut": "indisponible", "base_de_donnees": "erreur"},
            status=503,
        )
    return Response({"statut": "ok", "base_de_donnees": "ok"})


class EndpointSerializer(serializers.Serializer):
    methode = serializers.CharField()
    path = serializers.CharField()
    description = serializers.CharField()


class DomaineSerializer(serializers.Serializer):
    domaine = serializers.CharField()
    endpoints = EndpointSerializer(many=True)


class IndexApiSerializer(serializers.Serializer):
    nom = serializers.CharField()
    version = serializers.CharField()
    documentation_complete = serializers.CharField()
    schema = serializers.CharField()
    endpoints = DomaineSerializer(many=True)


@extend_schema(responses=IndexApiSerializer, tags=["racine"])
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def index_api(request):
    """Index de l'API : documentation vivante des endpoints disponibles."""
    return Response(
        {
            "nom": "RedAfrik API",
            "version": "1.0.0",
            "documentation_complete": "/api/docs/",
            "schema": "/api/schema/",
            "endpoints": INDEX_ENDPOINTS,
        }
    )
