"""Vues de l'app communities : CRUD, abonnements et tendances."""

from django.db.models import Count, Exists, OuterRef, Subquery
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.moderation.models import Moderateur
from core.permissions import EstCreateurOuAdministrateur
from .models import Abonnement, Communaute
from .serializers import CommunauteSerializer


class CommunauteViewSet(viewsets.ModelViewSet):
    """
    Gestion des communautés.

    Routes :
    - GET    /api/communautes/                 liste (recherche par ?search=)
    - POST   /api/communautes/                 création (le créateur devient admin)
    - GET    /api/communautes/{nom}/           détail
    - PUT/PATCH /api/communautes/{nom}/        modification (créateur ou admin)
    - DELETE /api/communautes/{nom}/           suppression (créateur uniquement)
    - POST   /api/communautes/{nom}/abonner/   s'abonner
    - DELETE /api/communautes/{nom}/abonner/   se désabonner
    - GET    /api/communautes/tendances/       classées par nombre d'abonnés
    """

    queryset = Communaute.objects.select_related("createur").all()
    serializer_class = CommunauteSerializer
    lookup_field = "nom"

    search_fields = ("nom", "description")

    def get_queryset(self):
        """Annote les compteurs (abonnés, posts) et l'abonnement de l'utilisateur."""
        queryset = super().get_queryset().annotate(
            nombre_abonnes=Count("abonnements", distinct=True),
            nombre_posts=Count("posts", distinct=True),
        )
        if self.request.user.is_authenticated:
            abonnement = Abonnement.objects.filter(
                utilisateur=self.request.user, communaute=OuterRef("pk")
            )
            queryset = queryset.annotate(est_abonne=Exists(abonnement))
            role = Moderateur.objects.filter(
                utilisateur=self.request.user, communaute=OuterRef("pk")
            )
            queryset = queryset.annotate(mon_role=Subquery(role.values("role")[:1]))
        return queryset

    def get_permissions(self):
        """
        Création réservée aux utilisateurs connectés ; modification et
        suppression soumises à la permission EstCreateurOuAdministrateur
        (vérifiée au niveau de l'objet dans has_object_permission).
        """
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), EstCreateurOuAdministrateur()]
        return super().get_permissions()

    @action(detail=True, methods=["post", "delete"], url_path="abonner")
    def abonner(self, request, nom=None):
        """
        POST : abonne l'utilisateur connecté à la communauté.
        DELETE : désabonne l'utilisateur connecté.
        """
        communaute = self.get_object()
        if request.method == "DELETE":
            Abonnement.objects.filter(
                utilisateur=request.user, communaute=communaute
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        abonnement, cree = Abonnement.objects.get_or_create(
            utilisateur=request.user, communaute=communaute
        )
        if not cree:
            return Response(
                {"detail": "Vous êtes déjà abonné à cette communauté."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Abonnement enregistré."}, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def tendances(self, request):
        """Communautés les plus suivies (abonnés, puis activité de posts)."""
        communautes = self.get_queryset().order_by(
            "-nombre_abonnes", "-nombre_posts"
        )
        page = self.paginate_queryset(communautes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(communautes, many=True)
        return Response(serializer.data)
