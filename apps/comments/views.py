"""Vues de l'app comments : CRUD, arborescence et votes."""

from collections import defaultdict

from django.db.models import OuterRef, Subquery
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.posts.views import _valider_valeur
from apps.votes.models import VoteCommentaire
from core.permissions import EstAuteurOuModerateur
from .models import Commentaire
from .serializers import CommentaireSerializer


def construire_arbre(commentaires):
    """
    Regroupe les commentaires par commentaire_parent_id en une seule passe.

    Retourne un dictionnaire {id_parent: [enfants, ...]} où la clé None
    désigne les commentaires racines.
    """
    arbre = defaultdict(list)
    for commentaire in commentaires:
        arbre[commentaire.commentaire_parent_id].append(commentaire)
    return arbre


class CommentaireViewSet(viewsets.ModelViewSet):
    """
    Gestion des commentaires.

    Routes :
    - GET    /api/commentaires/?post={id}     arborescence du post
    - POST   /api/commentaires/               créer {contenu, post, commentaire_parent?}
    - GET    /api/commentaires/{id}/          détail
    - PUT/PATCH /api/commentaires/{id}/       modifier (auteur ou modérateur)
    - DELETE /api/commentaires/{id}/          supprimer (auteur ou modérateur)
    - POST   /api/commentaires/{id}/vote/     voter {valeur: 1 | -1}
    - DELETE /api/commentaires/{id}/vote/     retirer son vote
    """

    queryset = Commentaire.objects.select_related("auteur", "post").all()
    serializer_class = CommentaireSerializer
    lookup_field = "pk"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            vote = VoteCommentaire.objects.filter(
                commentaire=OuterRef("pk"), utilisateur=self.request.user
            )
            queryset = queryset.annotate(vote_actuel=Subquery(vote.values("valeur")[:1]))
        return queryset

    def list(self, request, *args, **kwargs):
        """Renvoie l'arborescence complète des commentaires d'un post."""
        post_id = request.query_params.get("post")
        if not post_id:
            raise ValidationError(
                {"post": "Le paramètre « post » est requis pour lister les commentaires."}
            )
        # Une seule requête pour tout l'arbre, puis regroupement en mémoire
        commentaires = (
            self.get_queryset()
            .filter(post_id=post_id)
            .select_related("auteur")
            .order_by("date_creation")
        )
        arbre = construire_arbre(commentaires)
        racines = arbre.get(None, [])

        page = self.paginate_queryset(racines)
        serializer = self.get_serializer(
            page if page is not None else racines,
            many=True,
            context={**self.get_serializer_context(), "arbre": arbre},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def get_permissions(self):
        """Modification/suppression soumises à EstAuteurOuModerateur."""
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), EstAuteurOuModerateur()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(auteur=self.request.user)

    @action(detail=True, methods=["post", "delete"], url_path="vote")
    def vote(self, request, pk=None):
        """
        POST {valeur: 1 | -1} : crée ou met à jour le vote de l'utilisateur.
        DELETE : retire le vote de l'utilisateur.
        """
        commentaire = self.get_object()
        if request.method == "DELETE":
            VoteCommentaire.objects.filter(
                utilisateur=request.user, commentaire=commentaire
            ).delete()
            commentaire.refresh_from_db()
            return Response({"score": commentaire.score})

        if commentaire.auteur == request.user:
            raise ValidationError(
                "Vous ne pouvez pas voter sur votre propre commentaire."
            )
        valeur = _valider_valeur(request)
        VoteCommentaire.objects.update_or_create(
            utilisateur=request.user,
            commentaire=commentaire,
            defaults={"valeur": valeur},
        )
        commentaire.refresh_from_db()
        return Response({"valeur": valeur, "score": commentaire.score})
