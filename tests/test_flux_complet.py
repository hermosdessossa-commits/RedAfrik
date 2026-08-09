"""
Tests d'intégration du flux complet de RedAfrik : inscription, communautés,
publications, commentaires, votes (scores et karma) et modération.

Lancement : python manage.py test tests
"""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.comments.models import Commentaire
from apps.communities.models import Abonnement, Communaute
from apps.moderation.models import Moderateur, Signalement
from apps.posts.models import Post
from apps.users.models import User
from apps.votes.models import VotePost


def se_connecter(client, nom_utilisateur, mot_de_passe):
    """Authentifie un client de test et retourne les jetons JWT."""
    reponse = client.post(
        "/api/auth/connexion/",
        {"username": nom_utilisateur, "password": mot_de_passe},
        format="json",
    )
    return reponse.data["access"]


def en_tete(jeton):
    return {"HTTP_AUTHORIZATION": f"Bearer {jeton}"}


class TestAuthentification(APITestCase):
    def test_inscription_retourne_les_jetons(self):
        reponse = self.client.post(
            "/api/auth/inscription/",
            {
                "username": "amina",
                "email": "amina@example.com",
                "mot_de_passe": "MotDePasse!123",
                "mot_de_passe_confirmation": "MotDePasse!123",
            },
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", reponse.data)
        self.assertIn("refresh", reponse.data)
        self.assertEqual(User.objects.count(), 1)

    def test_inscription_mots_de_passe_differents(self):
        reponse = self.client.post(
            "/api/auth/inscription/",
            {
                "username": "amina",
                "email": "amina@example.com",
                "mot_de_passe": "MotDePasse!123",
                "mot_de_passe_confirmation": "AutreChose!456",
            },
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        # Format d'erreur normalisé
        self.assertIn("erreur", reponse.data)

    def test_connexion_et_profil(self):
        User.objects.create_user("kwame", "kwame@example.com", "MotDePasse!123")
        jeton = se_connecter(self.client, "kwame", "MotDePasse!123")
        reponse = self.client.get(
            "/api/utilisateurs/moi/", **en_tete(jeton)
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["username"], "kwame")
        self.assertEqual(reponse.data["karma"], 0)

    def test_profil_non_authentifie_refuse(self):
        reponse = self.client.get("/api/utilisateurs/moi/")
        self.assertEqual(reponse.status_code, status.HTTP_401_UNAUTHORIZED)


class TestCommunautes(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            "createur", "createur@example.com", "MotDePasse!123"
        )
        self.jeton = se_connecter(self.client, "createur", "MotDePasse!123")
        self.tetes = en_tete(self.jeton)

    def test_creation_et_auto_administration(self):
        reponse = self.client.post(
            "/api/communautes/",
            {"nom": "tech-afrique", "description": "La tech par l'Afrique"},
            format="json",
            **self.tetes,
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        communaute = Communaute.objects.get(nom="tech-afrique")
        self.assertEqual(communaute.createur, self.utilisateur)
        # Le créateur est automatiquement administrateur
        moderateur = Moderateur.objects.get(
            utilisateur=self.utilisateur, communaute=communaute
        )
        self.assertEqual(moderateur.role, Moderateur.Role.ADMINISTRATEUR)

    def test_abonnement_et_desabonnement(self):
        communaute = Communaute.objects.create(
            nom="musique", createur=self.utilisateur
        )
        abonnement = self.client.post(
            f"/api/communautes/{communaute.nom}/abonner/",
            **self.tetes,
        )
        self.assertEqual(abonnement.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Abonnement.objects.filter(
                utilisateur=self.utilisateur, communaute=communaute
            ).exists()
        )
        # L'abonnement est visible dans le détail de la communauté
        detail = self.client.get(
            f"/api/communautes/{communaute.nom}/", **self.tetes
        )
        self.assertTrue(detail.data["est_abonne"])
        desabonnement = self.client.delete(
            f"/api/communautes/{communaute.nom}/abonner/", **self.tetes
        )
        self.assertEqual(desabonnement.status_code, status.HTTP_204_NO_CONTENT)

    def test_tendances_classe_par_abonnes(self):
        communaute = Communaute.objects.create(
            nom="culture", createur=self.utilisateur
        )
        Abonnement.objects.create(utilisateur=self.utilisateur, communaute=communaute)
        tendances = self.client.get("/api/communautes/tendances/")
        self.assertEqual(tendances.status_code, status.HTTP_200_OK)
        noms = [c["nom"] for c in tendances.data["results"]]
        self.assertEqual(noms[0], "culture")


class TestPostsCommentairesEtVotes(APITestCase):
    def setUp(self):
        self.auteur = User.objects.create_user(
            "auteur", "auteur@example.com", "MotDePasse!123"
        )
        self.votant = User.objects.create_user(
            "votant", "votant@example.com", "MotDePasse!123"
        )
        self.communaute = Communaute.objects.create(
            nom="sports", createur=self.auteur
        )
        self.jeton_votant = se_connecter(self.client, "votant", "MotDePasse!123")
        self.tetes_votant = en_tete(self.jeton_votant)
        self.jeton_auteur = se_connecter(self.client, "auteur", "MotDePasse!123")
        self.tetes_auteur = en_tete(self.jeton_auteur)

    def creer_post(self):
        reponse = self.client.post(
            "/api/posts/",
            {
                "titre": "L'Afrique dans le football mondial",
                "contenu": "Analyse du Mondial 2026.",
                "communaute": "sports",
            },
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        return reponse.data

    def test_vote_met_a_jour_score_et_karma(self):
        post = self.creer_post()
        post_id = post["id"]

        vote = self.client.post(
            f"/api/posts/{post_id}/vote/",
            {"valeur": 1},
            format="json",
            **self.tetes_votant,
        )
        self.assertEqual(vote.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.get(pk=post_id).score, 1)
        # Le karma de l'auteur reflète le score de son post
        self.auteur.refresh_from_db()
        self.assertEqual(self.auteur.karma, 1)

        # Un second utilisateur vote négativement
        User.objects.create_user("votant2", "votant2@example.com", "MotDePasse!123")
        jeton_votant2 = se_connecter(self.client, "votant2", "MotDePasse!123")
        self.client.post(
            f"/api/posts/{post_id}/vote/",
            {"valeur": -1},
            format="json",
            **en_tete(jeton_votant2),
        )
        self.assertEqual(Post.objects.get(pk=post_id).score, 0)

        # Le votant modifie son vote : 0 - 1 = -1
        self.client.post(
            f"/api/posts/{post_id}/vote/",
            {"valeur": -1},
            format="json",
            **self.tetes_votant,
        )
        self.assertEqual(Post.objects.get(pk=post_id).score, -2)
        self.auteur.refresh_from_db()
        self.assertEqual(self.auteur.karma, -2)

        # Retrait du vote : le score remonte
        self.client.delete(f"/api/posts/{post_id}/vote/", **self.tetes_votant)
        self.assertEqual(Post.objects.get(pk=post_id).score, -1)

    def test_vote_unique_et_auto_vote_interdit(self):
        post = self.creer_post()
        post_id = post["id"]
        # Un utilisateur ne peut voter qu'une fois (modifiable, pas de doublon)
        self.client.post(
            f"/api/posts/{post_id}/vote/", {"valeur": 1}, format="json", **self.tetes_votant
        )
        self.client.post(
            f"/api/posts/{post_id}/vote/", {"valeur": 1}, format="json", **self.tetes_votant
        )
        self.assertEqual(VotePost.objects.filter(post_id=post_id).count(), 1)
        # L'auteur ne peut pas voter sur son propre post
        reponse = self.client.post(
            f"/api/posts/{post_id}/vote/",
            {"valeur": 1},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_commentaires_imbriques(self):
        post = self.creer_post()
        post_id = post["id"]
        racine = self.client.post(
            "/api/commentaires/",
            {"contenu": "Très bonne analyse !", "post": post_id},
            format="json",
            **self.tetes_votant,
        )
        self.assertEqual(racine.status_code, status.HTTP_201_CREATED)
        reponse = self.client.post(
            "/api/commentaires/",
            {
                "contenu": "Je suis d'accord avec toi.",
                "post": post_id,
                "commentaire_parent": racine.data["id"],
            },
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)

        arbre = self.client.get(f"/api/commentaires/?post={post_id}")
        self.assertEqual(arbre.status_code, status.HTTP_200_OK)
        racines = arbre.data["results"]
        self.assertEqual(len(racines), 1)
        self.assertEqual(len(racines[0]["reponses"]), 1)

        # Vote sur un commentaire
        vote = self.client.post(
            f"/api/commentaires/{racine.data['id']}/vote/",
            {"valeur": 1},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(vote.status_code, status.HTTP_200_OK)
        self.assertEqual(Commentaire.objects.get(pk=racine.data["id"]).score, 1)

    def test_tri_populaire(self):
        self.creer_post()
        Post.objects.create(
            titre="Post moins populaire",
            contenu="...",
            auteur=self.auteur,
            communaute=self.communaute,
            score=5,
        )
        reponse = self.client.get(
            "/api/posts/?communaute=sports&tri=populaire"
        )
        noms = [p["titre"] for p in reponse.data["results"]]
        self.assertEqual(noms[0], "Post moins populaire")
        self.assertEqual(len(noms), 2)


class TestModeration(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin", "admin@example.com", "MotDePasse!123"
        )
        self.auteur = User.objects.create_user(
            "auteur", "auteur@example.com", "MotDePasse!123"
        )
        self.tiers = User.objects.create_user(
            "tiers", "tiers@example.com", "MotDePasse!123"
        )
        self.communaute = Communaute.objects.create(
            nom="economie", createur=self.admin
        )
        Moderateur.objects.create(
            utilisateur=self.admin,
            communaute=self.communaute,
            role=Moderateur.Role.ADMINISTRATEUR,
        )
        self.post = Post.objects.create(
            titre="Contenu à signaler",
            contenu="...",
            auteur=self.auteur,
            communaute=self.communaute,
        )
        self.jeton_admin = se_connecter(self.client, "admin", "MotDePasse!123")
        self.jeton_tiers = se_connecter(self.client, "tiers", "MotDePasse!123")

    def test_signalement_et_traitement(self):
        signalement = self.client.post(
            "/api/signalements/",
            {"post": self.post.pk, "raison": "Contenu inapproprié."},
            format="json",
            **en_tete(self.jeton_tiers),
        )
        self.assertEqual(signalement.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            signalement.data["statut"], Signalement.Statut.EN_ATTENTE
        )

        # Un non-modérateur ne peut pas traiter le signalement
        refuse = self.client.post(
            f"/api/signalements/{signalement.data['id']}/traiter/",
            {"statut": "resolu"},
            format="json",
            **en_tete(self.jeton_tiers),
        )
        self.assertEqual(refuse.status_code, status.HTTP_403_FORBIDDEN)

        # L'administrateur (modérateur) le résout
        traite = self.client.post(
            f"/api/signalements/{signalement.data['id']}/traiter/",
            {"statut": "resolu"},
            format="json",
            **en_tete(self.jeton_admin),
        )
        self.assertEqual(traite.status_code, status.HTTP_200_OK)
        self.assertEqual(traite.data["statut"], "resolu")

    def test_moderateur_supprime_contenu_d_autrui(self):
        # L'administrateur supprime le post d'un autre utilisateur
        reponse = self.client.delete(
            f"/api/posts/{self.post.pk}/", **en_tete(self.jeton_admin)
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_nomination_moderateur_reservee_aux_admins(self):
        reponse = self.client.post(
            "/api/moderateurs/",
            {
                "utilisateur": self.auteur.pk,
                "communaute": "economie",
                "role": "moderateur",
            },
            format="json",
            **en_tete(self.jeton_tiers),
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        reponse = self.client.post(
            "/api/moderateurs/",
            {
                "utilisateur": self.auteur.pk,
                "communaute": "economie",
                "role": "moderateur",
            },
            format="json",
            **en_tete(self.jeton_admin),
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)


class TestCorrectifs(APITestCase):
    """Régression : karma, signalements orphelins, doublons de modération, post immuable."""

    def setUp(self):
        self.auteur = User.objects.create_user(
            "auteur", "auteur@example.com", "MotDePasse!123"
        )
        self.autre = User.objects.create_user(
            "autre", "autre@example.com", "MotDePasse!123"
        )
        self.jeton_auteur = se_connecter(self.client, "auteur", "MotDePasse!123")
        self.tetes_auteur = en_tete(self.jeton_auteur)
        self.jeton_autre = se_connecter(self.client, "autre", "MotDePasse!123")
        self.tetes_autre = en_tete(self.jeton_autre)
        self.communaute = Communaute.objects.create(
            nom="corriges", createur=self.auteur
        )
        Moderateur.objects.create(
            utilisateur=self.auteur,
            communaute=self.communaute,
            role=Moderateur.Role.ADMINISTRATEUR,
        )

    def creer_post_vote(self):
        """Crée un post (par l'auteur) et le fait voter +1 par « autre »."""
        reponse = self.client.post(
            "/api/posts/",
            {"titre": "Post", "contenu": "Contenu", "communaute": "corriges"},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        post_id = reponse.data["id"]
        self.client.post(
            f"/api/posts/{post_id}/vote/",
            {"valeur": 1},
            format="json",
            **self.tetes_autre,
        )
        return post_id

    def test_karma_decremente_a_la_suppression_du_post(self):
        """Correctif 1 : le karma de l'auteur suit la suppression du post."""
        post_id = self.creer_post_vote()
        self.auteur.refresh_from_db()
        self.assertEqual(self.auteur.karma, 1)
        self.client.delete(f"/api/posts/{post_id}/", **self.tetes_auteur)
        self.auteur.refresh_from_db()
        self.assertEqual(self.auteur.karma, 0)

    def test_karma_suit_la_suppression_d_un_commentaire(self):
        """Correctif 1 : le karma suit la suppression d'un commentaire voté."""
        post_id = self.creer_post_vote()
        reponse = self.client.post(
            "/api/commentaires/",
            {"contenu": "Commentaire", "post": post_id},
            format="json",
            **self.tetes_autre,
        )
        commentaire_id = reponse.data["id"]
        self.client.post(
            f"/api/commentaires/{commentaire_id}/vote/",
            {"valeur": 1},
            format="json",
            **self.tetes_auteur,
        )
        # « autre » a créé le commentaire : son karma ne reflète que
        # le score de ce commentaire (le score du post va à l'auteur).
        self.autre.refresh_from_db()
        self.assertEqual(self.autre.karma, 1)
        self.client.delete(
            f"/api/commentaires/{commentaire_id}/", **self.tetes_autre
        )
        self.autre.refresh_from_db()
        self.assertEqual(self.autre.karma, 0)

    def test_signalement_orphelin_non_supprimable_par_un_utilisateur(self):
        """Correctif 2 : un signalement orphelin (cible rendue nulle) reste protégé."""
        post = Post.objects.create(
            titre="Cible",
            contenu="...",
            auteur=self.auteur,
            communaute=self.communaute,
        )
        signalement = self.client.post(
            "/api/signalements/",
            {"post": post.pk, "raison": "Spam"},
            format="json",
            **self.tetes_autre,
        )
        # Simulation d'un signalement devenu orphelin (cible détachée hors
        # Django, par exemple une purge manuelle de la base).
        Signalement.objects.filter(pk=signalement.data["id"]).update(
            post=None, commentaire=None
        )
        suppression = self.client.delete(
            f"/api/signalements/{signalement.data['id']}/", **self.tetes_autre
        )
        self.assertEqual(suppression.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            Signalement.objects.filter(pk=signalement.data["id"]).exists()
        )

    def test_moderateur_deja_nomme_refuse_au_lieu_de_500(self):
        """Correctif 4 : un doublon de modération renvoie 400, pas un 500."""
        communaute = Communaute.objects.create(
            nom="doublon", createur=self.auteur
        )
        Moderateur.objects.create(
            utilisateur=self.auteur,
            communaute=communaute,
            role=Moderateur.Role.ADMINISTRATEUR,
        )
        reponse = self.client.post(
            "/api/moderateurs/",
            {
                "utilisateur": self.auteur.pk,
                "communaute": "doublon",
                "role": "moderateur",
            },
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_changement_de_post_d_un_commentaire_refuse(self):
        """Correctif 5 : le post d'un commentaire est immuable lors d'un update."""
        post_id = self.creer_post_vote()
        reponse = self.client.post(
            "/api/commentaires/",
            {"contenu": "Commentaire", "post": post_id},
            format="json",
            **self.tetes_autre,
        )
        commentaire_id = reponse.data["id"]
        autre_post_id = self.creer_post_vote()
        patch = self.client.patch(
            f"/api/commentaires/{commentaire_id}/",
            {"post": autre_post_id},
            format="json",
            **self.tetes_autre,
        )
        self.assertEqual(patch.status_code, status.HTTP_400_BAD_REQUEST)


class TestProfilsEtRights(APITestCase):
    """Profil personnel, contenu modifiable/effaçable par l'auteur, filtre ?auteur=."""

    def setUp(self):
        self.auteur = User.objects.create_user(
            "auteur", "auteur@example.com", "MotDePasse!123"
        )
        self.tiers = User.objects.create_user(
            "tiers", "tiers@example.com", "MotDePasse!123"
        )
        self.communaute = Communaute.objects.create(
            nom="profil-test", createur=self.auteur
        )
        Moderateur.objects.create(
            utilisateur=self.auteur,
            communaute=self.communaute,
            role=Moderateur.Role.ADMINISTRATEUR,
        )
        self.jeton_auteur = se_connecter(self.client, "auteur", "MotDePasse!123")
        self.tetes_auteur = en_tete(self.jeton_auteur)
        self.jeton_tiers = se_connecter(self.client, "tiers", "MotDePasse!123")
        self.tetes_tiers = en_tete(self.jeton_tiers)

    def test_mise_a_jour_du_profil_bio_et_avatar(self):
        reponse = self.client.patch(
            "/api/utilisateurs/profil/",
            {"bio": "Développeuse à Dakar", "avatar_url": "https://exemple.com/a.png"},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.auteur.refresh_from_db()
        self.assertEqual(self.auteur.bio, "Développeuse à Dakar")
        self.assertEqual(self.auteur.avatar_url, "https://exemple.com/a.png")

    def test_modification_suppression_post_reservees_a_l_auteur(self):
        reponse = self.client.post(
            "/api/posts/",
            {"titre": "Mon post", "contenu": "Contenu", "communaute": "profil-test"},
            format="json",
            **self.tetes_auteur,
        )
        post_id = reponse.data["id"]

        patch_tiers = self.client.patch(
            f"/api/posts/{post_id}/",
            {"titre": "Détourné"},
            format="json",
            **self.tetes_tiers,
        )
        self.assertEqual(patch_tiers.status_code, status.HTTP_403_FORBIDDEN)

        delete_tiers = self.client.delete(
            f"/api/posts/{post_id}/", **self.tetes_tiers
        )
        self.assertEqual(delete_tiers.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(pk=post_id).exists())

        patch_auteur = self.client.patch(
            f"/api/posts/{post_id}/",
            {"titre": "Titre corrigé"},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(patch_auteur.status_code, status.HTTP_200_OK)

    def test_modification_suppression_commentaire_reservees_a_l_auteur(self):
        post = Post.objects.create(
            titre="Post",
            contenu="Contenu",
            auteur=self.auteur,
            communaute=self.communaute,
        )
        reponse = self.client.post(
            "/api/commentaires/",
            {"contenu": "Mon avis", "post": post.pk},
            format="json",
            **self.tetes_auteur,
        )
        commentaire_id = reponse.data["id"]

        patch_tiers = self.client.patch(
            f"/api/commentaires/{commentaire_id}/",
            {"contenu": "Détourné"},
            format="json",
            **self.tetes_tiers,
        )
        self.assertEqual(patch_tiers.status_code, status.HTTP_403_FORBIDDEN)
        delete_tiers = self.client.delete(
            f"/api/commentaires/{commentaire_id}/", **self.tetes_tiers
        )
        self.assertEqual(delete_tiers.status_code, status.HTTP_403_FORBIDDEN)

        patch_auteur = self.client.patch(
            f"/api/commentaires/{commentaire_id}/",
            {"contenu": "Corrigé"},
            format="json",
            **self.tetes_auteur,
        )
        self.assertEqual(patch_auteur.status_code, status.HTTP_200_OK)

    def test_filtre_posts_par_auteur(self):
        for i in range(2):
            Post.objects.create(
                titre=f"Post {i}",
                contenu="Contenu",
                auteur=self.auteur,
                communaute=self.communaute,
            )
        Post.objects.create(
            titre="Post tiers",
            contenu="Contenu",
            auteur=self.tiers,
            communaute=self.communaute,
        )
        reponse = self.client.get(f"/api/posts/?auteur={self.auteur.pk}")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        resultats = reponse.data["results"]
        self.assertEqual(len(resultats), 2)
        self.assertTrue(
            all(p["auteur"]["id"] == self.auteur.pk for p in resultats)
        )

    def test_roles_moderation_exposes_sur_la_communaute(self):
        detail_createur = self.client.get(
            f"/api/communautes/{self.communaute.nom}/", **self.tetes_auteur
        )
        self.assertTrue(detail_createur.data["est_moderateur"])
        self.assertTrue(detail_createur.data["est_administrateur"])
        detail_tiers = self.client.get(
            f"/api/communautes/{self.communaute.nom}/", **self.tetes_tiers
        )
        self.assertFalse(detail_tiers.data["est_moderateur"])
        self.assertFalse(detail_tiers.data["est_administrateur"])
        # Le visiteur anonyme n'a aucun rôle (régression 500)
        detail_anonyme = self.client.get(f"/api/communautes/{self.communaute.nom}/")
        self.assertEqual(detail_anonyme.status_code, status.HTTP_200_OK)
        self.assertFalse(detail_anonyme.data["est_moderateur"])


class TestModerationAnonymesEtParcours(APITestCase):
    """Panneau de modération : accès, traitement et droits des rôles."""

    def setUp(self):
        self.admin = User.objects.create_user(
            "admin", "admin@example.com", "MotDePasse!123"
        )
        self.moderateur = User.objects.create_user(
            "modo", "modo@example.com", "MotDePasse!123"
        )
        self.abuse = User.objects.create_user(
            "abuse", "abuse@example.com", "MotDePasse!123"
        )
        self.communaute = Communaute.objects.create(
            nom="modo-test", createur=self.admin
        )
        Moderateur.objects.create(
            utilisateur=self.admin,
            communaute=self.communaute,
            role=Moderateur.Role.ADMINISTRATEUR,
        )
        Moderateur.objects.create(
            utilisateur=self.moderateur,
            communaute=self.communaute,
            role=Moderateur.Role.MODERATEUR,
        )
        self.jeton_admin = se_connecter(self.client, "admin", "MotDePasse!123")
        self.tetes_admin = en_tete(self.jeton_admin)
        self.jeton_modo = se_connecter(self.client, "modo", "MotDePasse!123")
        self.tetes_modo = en_tete(self.jeton_modo)
        self.jeton_abuse = se_connecter(self.client, "abuse", "MotDePasse!123")
        self.tetes_abuse = en_tete(self.jeton_abuse)

    def test_signalements_anonymes_renvoient_403_pas_500(self):
        """Régression : AnonymousUser ne doit plus déclencher un 500."""
        reponse = self.client.get(
            f"/api/signalements/?communaute={self.communaute.nom}"
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_signalements_listes_uniquement_par_les_moderateurs(self):
        post = Post.objects.create(
            titre="Signalé",
            contenu="...",
            auteur=self.abuse,
            communaute=self.communaute,
        )
        self.client.post(
            "/api/signalements/",
            {"post": post.pk, "raison": "Spam"},
            format="json",
            **self.tetes_abuse,
        )
        refus = self.client.get(
            f"/api/signalements/?communaute={self.communaute.nom}",
            **self.tetes_abuse,
        )
        self.assertEqual(refus.status_code, status.HTTP_403_FORBIDDEN)

        liste_modo = self.client.get(
            f"/api/signalements/?communaute={self.communaute.nom}",
            **self.tetes_modo,
        )
        self.assertEqual(liste_modo.status_code, status.HTTP_200_OK)
        self.assertEqual(liste_modo.data["results"][0]["raison"], "Spam")

    def test_moderateur_traite_le_signalement_sans_etre_admin(self):
        post = Post.objects.create(
            titre="Signalé",
            contenu="...",
            auteur=self.abuse,
            communaute=self.communaute,
        )
        signalement = self.client.post(
            "/api/signalements/",
            {"post": post.pk, "raison": "Contenu inapproprié"},
            format="json",
            **self.tetes_abuse,
        )
        traite = self.client.post(
            f"/api/signalements/{signalement.data['id']}/traiter/",
            {"statut": "resolu"},
            format="json",
            **self.tetes_modo,
        )
        self.assertEqual(traite.status_code, status.HTTP_200_OK)
        self.assertEqual(traite.data["statut"], "resolu")

    def test_nomination_changement_de_role_et_demission(self):
        reponse = self.client.post(
            "/api/moderateurs/",
            {
                "utilisateur": self.abuse.pk,
                "communaute": "modo-test",
                "role": "moderateur",
            },
            format="json",
            **self.tetes_admin,
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        moderateur_id = reponse.data["id"]

        # Un simple modérateur ne peut pas promouvoir
        promotion_tiers = self.client.patch(
            f"/api/moderateurs/{moderateur_id}/",
            {"role": "administrateur"},
            format="json",
            **self.tetes_modo,
        )
        self.assertEqual(promotion_tiers.status_code, status.HTTP_403_FORBIDDEN)

        # L'administrateur promeut, puis révoque
        promotion = self.client.patch(
            f"/api/moderateurs/{moderateur_id}/",
            {"role": "administrateur"},
            format="json",
            **self.tetes_admin,
        )
        self.assertEqual(promotion.status_code, status.HTTP_200_OK)
        self.assertEqual(promotion.data["role"], "administrateur")

        demission = self.client.delete(
            f"/api/moderateurs/{moderateur_id}/", **self.tetes_admin
        )
        self.assertEqual(demission.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Moderateur.objects.filter(pk=moderateur_id).exists()
        )

    def test_recherche_utilisateurs_par_nom_pour_nomination(self):
        reponse = self.client.get("/api/utilisateurs/?search=abuse")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        noms = [u["username"] for u in reponse.data["results"]]
        self.assertIn("abuse", noms)
