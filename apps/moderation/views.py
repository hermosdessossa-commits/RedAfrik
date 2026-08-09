"""Vues de l'app moderation : gestion des modérateurs et des signalements."""

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.communities.models import Communaute
from core.permissions import est_administrateur, est_moderateur
from .models import Moderateur, Signalement
from .serializers import ModerateurSerializer, SignalementSerializer


class ModerateurViewSet(viewsets.ModelViewSet):
    """
    Gestion des modérateurs d'une communauté (réservée aux administrateurs).

    Routes :
    - GET    /api/moderateurs/?communaute={nom}   liste (modérateurs de la communauté)
    - POST   /api/moderateurs/                    nommer {utilisateur, communaute, role}
    - PATCH  /api/moderateurs/{id}/               changer le rôle
    - DELETE /api/moderateurs/{id}/               démettre
    """

    queryset = Moderateur.objects.select_related("utilisateur", "communaute").all()
    serializer_class = ModerateurSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def _exiger_administrateur(self, communaute):
        if not est_administrateur(self.request.user, communaute):
            raise PermissionDenied(
                "Vous devez être administrateur de cette communauté."
            )

    def get_queryset(self):
        queryset = super().get_queryset()
        communaute = self.request.query_params.get("communaute")
        if communaute:
            queryset = queryset.filter(communaute__nom=communaute)
        return queryset

    def list(self, request, *args, **kwargs):
        # La lecture de la liste des modérateurs est ouverte aux modérateurs
        communaute_nom = request.query_params.get("communaute")
        if not communaute_nom:
            raise ValidationError(
                {"communaute": "Le paramètre « communaute » est requis."}
            )
        communaute = get_object_or_404(Communaute, nom=communaute_nom)
        if not est_moderateur(request.user, communaute):
            raise PermissionDenied("Vous devez être modérateur de cette communauté.")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        # La nomination est réservée aux administrateurs de la communauté
        communaute = serializer.validated_data["communaute"]
        self._exiger_administrateur(communaute)
        serializer.save()

    def perform_update(self, serializer):
        # Le changement de rôle est réservé aux administrateurs
        self._exiger_administrateur(self.get_object().communaute)
        serializer.save()

    def perform_destroy(self, instance):
        # La révocation est réservée aux administrateurs
        self._exiger_administrateur(instance.communaute)
        instance.delete()


class SignalementViewSet(viewsets.ModelViewSet):
    """
    Signalements de contenu.

    Routes :
    - POST   /api/signalements/                   signaler {post | commentaire, raison}
    - GET    /api/signalements/?communaute={nom}  liste (modérateurs, filtre par statut ?statut=)
    - POST   /api/signalements/{id}/traiter/      {statut: resolu | rejete} (modérateurs)
    - DELETE /api/signalements/{id}/              suppression (modérateurs)
    """

    queryset = Signalement.objects.select_related(
        "utilisateur",
        "post",
        "commentaire",
        "post__communaute",
        "commentaire__post__communaute",
    ).all()
    serializer_class = SignalementSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def _communaute_depuis_parametre(self):
        nom = self.request.query_params.get("communaute")
        if not nom:
            raise ValidationError(
                {"communaute": "Le paramètre « communaute » est requis."}
            )
        return get_object_or_404(Communaute, nom=nom)

    def _exiger_moderateur(self, communaute):
        if not est_moderateur(self.request.user, communaute):
            raise PermissionDenied("Vous devez être modérateur de cette communauté.")

    def get_queryset(self):
        queryset = super().get_queryset()
        nom = self.request.query_params.get("communaute")
        if nom:
            queryset = queryset.filter(
                models.Q(post__communaute__nom=nom)
                | models.Q(commentaire__post__communaute__nom=nom)
            )
        statut = self.request.query_params.get("statut")
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def list(self, request, *args, **kwargs):
        # La lecture des signalements est réservée aux modérateurs
        self._exiger_moderateur(self._communaute_depuis_parametre())
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)

    def destroy(self, request, *args, **kwargs):
        signalement = self.get_object()
        communaute = signalement.communaute_cible()
        if communaute is None:
            # Cible supprimée (signalement orphelin) : le lien avec une
            # communauté a disparu. On refuse la suppression à quiconque
            # n'est pas membre du staff, plutôt que de laisser n'importe
            # quel utilisateur authentifié supprimer le signalement.
            if not request.user.is_staff:
                raise PermissionDenied(
                    "Ce signalement est orphelin (cible supprimée) : "
                    "seule l'administration peut le supprimer."
                )
        else:
            self._exiger_moderateur(communaute)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="traiter")
    def traiter(self, request, pk=None):
        """Change le statut d'un signalement (réservé aux modérateurs)."""
        signalement = self.get_object()
        communaute = signalement.communaute_cible()
        if communaute is None:
            raise PermissionDenied("La cible du signalement n'existe plus.")
        self._exiger_moderateur(communaute)

        statut = request.data.get("statut")
        if statut not in (Signalement.Statut.RESOLU, Signalement.Statut.REJETE):
            raise ValidationError(
                {"statut": "Le statut doit être « resolu » ou « rejete »."}
            )
        signalement.statut = statut
        signalement.save(update_fields=["statut"])
        return Response(self.get_serializer(signalement).data)
