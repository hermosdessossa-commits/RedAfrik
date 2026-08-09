"""Back-office RedAfrik : site d'administration personnalisé.

Remplace l'AdminSite Django par défaut afin de fournir un tableau de bord
avec statistiques, un habillage aux couleurs de la plateforme et un nommage
francophone cohérent (variables CSS du thème dans
core/static/admin/css/redafrik_admin.css).
"""

from django.contrib import admin

from .models import JournalAction


class JournalActionAdmin(admin.ModelAdmin):
    """Consultation du journal des actions (lecture et purge uniquement)."""

    list_display = (
        "date_creation",
        "utilisateur",
        "methode",
        "chemin",
        "statut",
        "adresse_ip",
        "pays",
    )
    list_filter = ("methode", "statut", "date_creation")
    search_fields = ("adresse_ip", "chemin", "utilisateur__username")
    date_hierarchy = "date_creation"
    list_select_related = ("utilisateur",)
    readonly_fields = (
        "utilisateur",
        "methode",
        "chemin",
        "statut",
        "adresse_ip",
        "agent",
        "geolocalisation",
        "date_creation",
    )

    def pays(self, objet):
        if not objet.geolocalisation:
            return "—"
        return objet.geolocalisation.get("pays")

    pays.short_description = "pays"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RedAfrikAdminSite(admin.AdminSite):
    """Site d'administration RedAfrik : ajoute les stats au tableau de bord."""

    index_template = "admin/index.html"

    def each_context(self, request):
        contexte = super().each_context(request)
        contexte["site_url"] = None  # pas de « Afficher le site » ambigu ici
        return contexte

    def index(self, request, extra_context=None):
        """Tableau de bord : comptes et derniers signalements à traiter."""

        from django.contrib.auth import get_user_model

        from apps.comments.models import Commentaire
        from apps.communities.models import Abonnement, Communaute
        from apps.moderation.models import Moderateur, Signalement
        from apps.posts.models import Post
        from apps.votes.models import VoteCommentaire, VotePost

        Utilisateur = get_user_model()

        extra = extra_context or {}
        extra["statistiques"] = [
            {
                "titre": "Utilisateurs",
                "valeur": Utilisateur.objects.count(),
                "icone": "users",
                "lien": "admin:users_user_changelist",
                "texte": "Utilisateurs actifs, classés par karma dans la liste.",
            },
            {
                "titre": "Communautés",
                "valeur": Communaute.objects.count(),
                "icone": "communautes",
                "lien": "admin:communities_communaute_changelist",
                "texte": "Communautés thématiques de la plateforme.",
            },
            {
                "titre": "Publications",
                "valeur": Post.objects.count(),
                "icone": "posts",
                "lien": "admin:posts_post_changelist",
                "texte": "Posts publiés (texte, liens, images).",
            },
            {
                "titre": "Commentaires",
                "valeur": Commentaire.objects.count(),
                "icone": "commentaires",
                "lien": "admin:comments_commentaire_changelist",
                "texte": "Dont réponses imbriquées.",
            },
            {
                "titre": "Votes",
                "valeur": VotePost.objects.count() + VoteCommentaire.objects.count(),
                "icone": "votes",
                "texte": "Votes positifs et négatifs cumulés.",
            },
            {
                "titre": "Signalements",
                "valeur": Signalement.objects.count(),
                "icone": "signalements",
                "lien": "admin:moderation_signalement_changelist",
                "texte": "Contenus signalés par les utilisateurs.",
            },
            {
                "titre": "Modérateurs",
                "valeur": Moderateur.objects.count(),
                "icone": "moderateurs",
                "lien": "admin:moderation_moderateur_changelist",
                "texte": "Rôles de modération par communauté.",
            },
            {
                "titre": "Abonnements",
                "valeur": Abonnement.objects.count(),
                "icone": "abonnements",
                "texte": "Couples utilisateur ↔ communauté.",
            },
            {
                "titre": "Actions journalisées",
                "valeur": JournalAction.objects.count(),
                "icone": "actions",
                "lien": "admin:core_journalaction_changelist",
                "texte": "Trace IP + géolocalisation (rétention 90 jours).",
            },
        ]

        extra["signalements_recents"] = (
            Signalement.objects.select_related("utilisateur", "post", "commentaire")
            .order_by("-date_creation")[:6]
        )
        extra["signalements_en_attente"] = Signalement.objects.filter(
            statut=Signalement.Statut.EN_ATTENTE
        ).count()

        return super().index(request, extra)


# Instance partagée : les AdminClass enregistrent dessus (voir apps/*/admin.py)
site = RedAfrikAdminSite(name="redafrik")

site.register(JournalAction, JournalActionAdmin)