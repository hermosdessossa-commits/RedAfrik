"""
Permissions personnalisées de RedAfrik.

Les droits de modération reposent sur le modèle Moderateur de l'app
moderation : un utilisateur peut être « modérateur » ou « administrateur »
d'une communauté. L'auteur d'une communauté en est automatiquement
administrateur.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.moderation.models import Moderateur

# --- Fonctions utilitaires ---------------------------------------------------


def role_dans_communaute(utilisateur, communaute):
    """Retourne le rôle de l'utilisateur dans la communauté, ou None."""
    try:
        return Moderateur.objects.get(
            utilisateur=utilisateur, communaute=communaute
        ).role
    except Moderateur.DoesNotExist:
        return None


def est_moderateur(utilisateur, communaute):
    """True si l'utilisateur est modérateur ou administrateur de la communauté."""
    return role_dans_communaute(utilisateur, communaute) in (
        Moderateur.Role.MODERATEUR,
        Moderateur.Role.ADMINISTRATEUR,
    )


def est_administrateur(utilisateur, communaute):
    """True si l'utilisateur est administrateur de la communauté."""
    return role_dans_communaute(utilisateur, communaute) == Moderateur.Role.ADMINISTRATEUR


def communaute_associee(obj):
    """
    Retourne la communauté associée à un contenu (Post ou Commentaire),
    ce qui permet d'utiliser les mêmes permissions pour les deux types.
    """
    if hasattr(obj, "communaute"):
        return obj.communaute
    if hasattr(obj, "post"):
        return obj.post.communaute
    return None


# --- Classes de permission ----------------------------------------------------


class EstAuteurOuLectureSeule(BasePermission):
    """Lecture pour tous, modification réservée à l'auteur du contenu."""

    message = "Seul l'auteur de ce contenu peut le modifier."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.auteur == request.user


class EstAuteurOuModerateur(BasePermission):
    """
    Modification/suppression réservée à l'auteur du contenu ou à un
    modérateur de la communauté dans laquelle le contenu est publié
    (utilisé pour les posts et les commentaires).
    """

    message = "Seul l'auteur ou un modérateur de la communauté peut modifier ce contenu."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.auteur == request.user:
            return True
        communaute = communaute_associee(obj)
        return bool(communaute) and est_moderateur(request.user, communaute)


class EstCreateurOuAdministrateur(BasePermission):
    """
    Modification d'une communauté réservée à son créateur ou à un
    administrateur ; suppression réservée au créateur uniquement.
    """

    message = "Vous n'avez pas les droits de modération sur cette communauté."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.createur == request.user:
            return True
        # La suppression est réservée au créateur de la communauté
        if request.method == "DELETE":
            return False
        return est_administrateur(request.user, obj)
