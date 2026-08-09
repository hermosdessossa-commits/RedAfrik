"""Jeu de données de démonstration RedAfrik.

Crée des utilisateurs, une communauté, des publications, des commentaires,
des votes (les signaux mettent à jour scores et karma) et un signalement,
afin de disposer d'une base réaliste pour la démo locale et les tests e2e.

Usage :
    python manage.py seed            # ajoute les données (idempotent)
    python manage.py seed --reset   # vide la base puis réinjecte
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.comments.models import Commentaire
from apps.communities.models import Abonnement, Communaute
from apps.moderation.models import Moderateur, Signalement
from apps.posts.models import Post
from apps.votes.models import VoteCommentaire, VotePost

USER_MODEL = get_user_model()

MOT_DE_PASSE = "motdepasse123"


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (utilisateurs, communauté, posts, votes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Vide toutes les tables avant de réinjecter les données.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            call_command("flush", interactive=False)
            self.stdout.write("Base vidée.")

        try:
            utilisateurs = self._creer_utilisateurs()
            communaute = self._creer_communaute(utilisateurs)
            self._creer_abonnements(utilisateurs, communaute)
            posts = self._creer_posts(utilisateurs, communaute)
            commentaires = self._creer_commentaires(utilisateurs, posts)
            self._creer_votes(utilisateurs, posts, commentaires)
            self._creer_signalement(utilisateurs["zoe"], posts["comment"])
            self._nommer_moderateur(utilisateurs, communaute)
        except Exception as exc:
            raise CommandError(f"Échec du seed : {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            "Données de démonstration créées : "
            f"{USER_MODEL.objects.count()} utilisateurs, "
            f"r/{communaute.nom}, {Post.objects.count()} posts, "
            f"{Commentaire.objects.count()} commentaires."
        ))

    @staticmethod
    def _creer_utilisateurs():
        """Crée les utilisateurs de démonstration (idempotent)."""
        noms = ["demo", "ali", "fatou", "zoe"]
        existants = {u.username: u for u in USER_MODEL.objects.filter(username__in=noms)}
        nouveaux = {}
        for nom in noms:
            utilisateur = existants.get(nom)
            if utilisateur is None:
                utilisateur = USER_MODEL.objects.create_user(
                    username=nom,
                    email=f"{nom}@redafrik.demo",
                    password=MOT_DE_PASSE,
                )
            nouveaux[nom] = utilisateur
        # Profils : bio et avatar optionnels
        nouveaux["demo"].bio = "Fondateur de la communauté tech-afrique."
        nouveaux["demo"].avatar_url = ""
        nouveaux["fatou"].bio = "Passionnée de data et de cultures africaines."
        for utilisateur in nouveaux.values():
            utilisateur.save(update_fields=["bio", "avatar_url"])
        return nouveaux

    def _creer_communaute(self, utilisateurs):
        communaute, _ = Communaute.objects.get_or_create(
            nom="tech-afrique",
            defaults={
                "description": "Innovations, startups et débats tech de la diaspora africaine.",
                "createur": utilisateurs["demo"],
            },
        )
        # Le sérialiseur crée l'administrateur à la création via l'API ;
        # en seed on le garantit explicitement.
        Moderateur.objects.get_or_create(
            utilisateur=utilisateurs["demo"],
            communaute=communaute,
            defaults={"role": Moderateur.Role.ADMINISTRATEUR},
        )
        return communaute

    def _creer_abonnements(self, utilisateurs, communaute):
        for nom in ("demo", "ali", "fatou"):
            Abonnement.objects.get_or_create(
                utilisateur=utilisateurs[nom], communaute=communaute
            )

    def _creer_posts(self, utilisateurs, communaute):
        donnees = [
            ("demo", "Lancement d'un incubateur pour fintechs à Dakar",
             "Un collectif de développeurs sénégalais ouvre un appel à candidatures…"),
            ("demo", "Comment la diaspora finance les start-ups locales ?",
             "Retours d'expérience bienvenus : quels montages, quels risques ?"),
            ("ali", "Audio : podcast tech hebdo",
             "Nouvel épisode disponible : l'intelligence artificielle appliquée aux langues africaines."),
        ]
        posts = {}
        for nom, titre, contenu in donnees:
            post, _ = Post.objects.get_or_create(
                titre=titre,
                defaults={"auteur": utilisateurs[nom], "communaute": communaute, "contenu": contenu},
            )
            posts[titre.split()[0].lower()] = post
        return posts

    def _creer_commentaires(self, utilisateurs, posts):
        post = posts["lancement"]
        racine, _ = Commentaire.objects.get_or_create(
            contenu="Excellente initiative, comment participer ?",
            defaults={"auteur": utilisateurs["fatou"], "post": post},
        )
        Commentaire.objects.get_or_create(
            contenu="Rendez-vous page 12 du rapport pour les détails pratiques.",
            defaults={"auteur": utilisateurs["demo"], "post": post, "commentaire_parent": racine},
        )
        return [racine]

    def _creer_votes(self, utilisateurs, posts, commentaires):
        for post in posts.values():
            if not VotePost.objects.filter(utilisateur=utilisateurs["demo"], post=post).exists():
                VotePost.objects.create(utilisateur=utilisateurs["demo"], post=post, valeur=1)
        for commentaire in commentaires:
            if not VoteCommentaire.objects.filter(
                utilisateur=utilisateurs["ali"], commentaire=commentaire
            ).exists():
                VoteCommentaire.objects.create(
                    utilisateur=utilisateurs["ali"], commentaire=commentaire, valeur=1
                )

    def _creer_signalement(self, utilisatrice, post):
        if not Signalement.objects.filter(utilisateur=utilisatrice, post=post).exists():
            Signalement.objects.create(
                utilisateur=utilisatrice,
                post=post,
                raison="Propos jugés hors sujet et non sourcés.",
            )

    def _nommer_moderateur(self, utilisateurs, communaute):
        Moderateur.objects.get_or_create(
            utilisateur=utilisateurs["ali"],
            communaute=communaute,
            defaults={"role": Moderateur.Role.MODERATEUR},
        )