"""Vue racine de l'API : index descriptif de tous les endpoints."""

from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

INDEX_ENDPOINTS = [
    {
        "domaine": "Authentification",
        "endpoints": [
            {"methode": "POST", "path": "/api/auth/inscription/", "description": "Créer un compte (retourne les jetons JWT)"},
            {"methode": "POST", "path": "/api/auth/connexion/", "description": "Connexion {username, password} -> {access, refresh}"},
            {"methode": "POST", "path": "/api/auth/refresh/", "description": "Rafraîchir le jeton d'accès {refresh}"},
            {"methode": "POST", "path": "/api/auth/deconnexion/", "description": "Révoquer le jeton de rafraîchissement"},
        ],
    },
    {
        "domaine": "Utilisateurs",
        "endpoints": [
            {"methode": "GET", "path": "/api/utilisateurs/", "description": "Classement des utilisateurs par karma"},
            {"methode": "GET", "path": "/api/utilisateurs/moi/", "description": "Profil complet de l'utilisateur connecté"},
            {"methode": "GET/PUT/PATCH", "path": "/api/utilisateurs/profil/", "description": "Consulter / modifier son profil (bio, avatar)"},
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
            {"methode": "GET", "path": "/api/posts/", "description": "Lister les posts (?communaute=, ?tri=populaire, ?search=)"},
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
        ],
    },
]


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
