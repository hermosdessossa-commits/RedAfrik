"""Vues de l'app posts : CRUD, tri et votes."""

from django.db.models import Count, OuterRef, Subquery
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.votes.models import VotePost
from apps.votes.validation import valider_valeur_vote
from core.permissions import EstAuteurOuModerateur
from core.throttles import ThrottleEcriture

from .models import Post
from .serializers import PostSerializer


class PostViewSet(ThrottleEcriture, viewsets.ModelViewSet):
    """
    Gestion des publications.

    Routes :
    - GET    /api/posts/                       liste
    - POST   /api/posts/                       création {titre, communaute, ...}
    - GET    /api/posts/{id}/                  détail
    - PUT/PATCH /api/posts/{id}/               modification (auteur ou modérateur)
    - DELETE /api/posts/{id}/                  suppression (auteur ou modérateur)
    - POST   /api/posts/{id}/vote/             voter {valeur: 1 | -1}
    - DELETE /api/posts/{id}/vote/             retirer son vote

    Parameters de liste :
    - ?communaute=nom      filtre par communauté
    - ?auteur={id}         filtre par auteur (page profil)
    - ?tri=populaire       tri par score décroissant (défaut : récents)
    - ?search=...          recherche dans le titre et le contenu
    """

    queryset = Post.objects.select_related("auteur", "communaute").all()
    serializer_class = PostSerializer
    lookup_field = "pk"

    search_fields = ("titre", "contenu")

    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            nombre_commentaires=Count("commentaires", distinct=True)
        )
        if self.request.user.is_authenticated:
            vote = VotePost.objects.filter(
                post=OuterRef("pk"), utilisateur=self.request.user
            )
            queryset = queryset.annotate(vote_actuel=Subquery(vote.values("valeur")[:1]))
        return queryset

    def filter_queryset(self, queryset):
        """Filtres par communauté et tri chronologique / populaire."""
        queryset = super().filter_queryset(queryset)
        communaute = self.request.query_params.get("communaute")
        if communaute:
            queryset = queryset.filter(communaute__nom=communaute)
        auteur = self.request.query_params.get("auteur")
        if auteur:
            queryset = queryset.filter(auteur_id=auteur)
        tri = self.request.query_params.get("tri", "recents")
        if tri == "populaire":
            queryset = queryset.order_by("-score")
        else:
            queryset = queryset.order_by("-date_creation")
        return queryset

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
        post = self.get_object()
        if request.method == "DELETE":
            VotePost.objects.filter(utilisateur=request.user, post=post).delete()
            post.refresh_from_db()
            return Response({"score": post.score})

        if post.auteur == request.user:
            raise ValidationError(
                "Vous ne pouvez pas voter sur votre propre publication."
            )
        valeur = valider_valeur_vote(request)
        VotePost.objects.update_or_create(
            utilisateur=request.user, post=post, defaults={"valeur": valeur}
        )
        # Le score a été recalculé par le signal ; on le relit depuis la base.
        post.refresh_from_db()
        return Response({"valeur": valeur, "score": post.score})
