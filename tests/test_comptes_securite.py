"""Tests du Lot 1 : sécurité des comptes (vérification e-mail, réinitialisation,
changement de mot de passe, suppression de compte, anti force brute)."""

from django.core import mail
from rest_framework.test import APITestCase

from apps.users.models import EchecConnexion, JetonSecurite, User


class TestVerificationEmail(APITestCase):
    def setUp(self):
        self.donnees = {
            "username": "amina",
            "email": "amina@redafrik.demo",
            "mot_de_passe": "motdepasse123",
            "mot_de_passe_confirmation": "motdepasse123",
        }

    def test_inscription_envoie_email_et_marque_non_verifie(self):
        reponse = self.client.post(
            "/api/auth/inscription/", self.donnees, content_type="application/json"
        )
        self.assertEqual(reponse.status_code, 201)
        utilisateur = User.objects.get(username="amina")
        self.assertFalse(utilisateur.email_verifie)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Vérifiez votre adresse e-mail", mail.outbox[0].subject)

    def test_validation_du_jeton_verifie_le_compte(self):
        self.client.post(
            "/api/auth/inscription/", self.donnees, content_type="application/json"
        )
        utilisateur = User.objects.get(username="amina")
        jeton = JetonSecurite.objects.get(but="verification")
        from apps.users.models import JetonSecurite as JS

        # Récupère la valeur claire impossible depuis la base (hachée) :
        # on génère un jeton et on utilise sa valeur via le flux e-mail.
        jeton.delete()
        valeur = JS.creer(utilisateur, "verification", 24)[1]
        reponse = self.client.post(f"/api/auth/verifier-email/{valeur}/")
        self.assertEqual(reponse.status_code, 200)
        utilisateur.refresh_from_db()
        self.assertTrue(utilisateur.email_verifie)

    def test_jeton_expire_est_refuse(self):
        self.client.post(
            "/api/auth/inscription/", self.donnees, content_type="application/json"
        )
        utilisateur = User.objects.get(username="amina")
        from django.utils import timezone

        from apps.users.models import JetonSecurite as JS

        jeton, valeur = JS.creer(utilisateur, "verification", 24)
        jeton.expire_le = timezone.now() - timezone.timedelta(hours=1)
        jeton.save(update_fields=["expire_le"])
        reponse = self.client.post(f"/api/auth/verifier-email/{valeur}/")
        self.assertEqual(reponse.status_code, 400)
        utilisateur.refresh_from_db()
        self.assertFalse(utilisateur.email_verifie)


class TestResetMotDePasse(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="demo", email="demo@redafrik.demo", password="motdepasse123"
        )

    def test_demande_envoie_lien_et_accepte_neutre(self):
        reponse = self.client.post(
            "/api/auth/reinitialiser-mdp/",
            {"email": "demo@redafrik.demo"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # E-mail inconnu : même réponse (pas de fuite de compte)
        reponse = self.client.post(
            "/api/auth/reinitialiser-mdp/",
            {"email": "inconnu@redafrik.demo"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_confirmation_change_le_mot_de_passe(self):
        from apps.users.models import JetonSecurite as JS

        valeur = JS.creer(self.utilisateur, "reset_mot_de_passe", 1)[1]
        reponse = self.client.post(
            "/api/auth/reinitialiser-mdp/confirmer/",
            {
                "jeton": valeur,
                "nouveau_mot_de_passe": "nouveaumotdepasse",
                "confirmation": "nouveaumotdepasse",
            },
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.utilisateur.refresh_from_db()
        self.assertTrue(self.utilisateur.check_password("nouveaumotdepasse"))

    def test_jeton_invalide_refuse(self):
        reponse = self.client.post(
            "/api/auth/reinitialiser-mdp/confirmer/",
            {
                "jeton": "mauvais-jeton",
                "nouveau_mot_de_passe": "nouveaumotdepasse",
                "confirmation": "nouveaumotdepasse",
            },
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 400)


class TestChangementEtSuppression(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="demo", email="demo@redafrik.demo", password="motdepasse123"
        )
        self.client.force_authenticate(self.utilisateur)

    def test_changement_mot_de_passe_connecte(self):
        reponse = self.client.post(
            "/api/utilisateurs/mdp/",
            {
                "ancien_mot_de_passe": "motdepasse123",
                "nouveau_mot_de_passe": "motdepasse456",
                "confirmation": "motdepasse456",
            },
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.utilisateur.refresh_from_db()
        self.assertTrue(self.utilisateur.check_password("motdepasse456"))

    def test_changement_avec_mauvais_ancien_mdp_refuse(self):
        reponse = self.client.post(
            "/api/utilisateurs/mdp/",
            {
                "ancien_mot_de_passe": "mauvais",
                "nouveau_mot_de_passe": "motdepasse456",
                "confirmation": "motdepasse456",
            },
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 400)

    def test_suppression_compte_avec_mot_de_passe(self):
        reponse = self.client.delete(
            "/api/utilisateurs/supprimer-compte/",
            {"mot_de_passe": "motdepasse123"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(User.objects.filter(username="demo").exists())

    def test_suppression_sans_bon_mot_de_passe_refuse(self):
        reponse = self.client.delete(
            "/api/utilisateurs/supprimer-compte/",
            {"mot_de_passe": "mauvais"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertTrue(User.objects.filter(username="demo").exists())

    def test_profil_met_a_jour_username_email_et_revoque_verification(self):
        self.utilisateur.email_verifie = True
        self.utilisateur.save(update_fields=["email_verifie"])
        reponse = self.client.patch(
            "/api/utilisateurs/profil/",
            {"username": "nouveau-nom", "email": "nouveau@redafrik.demo"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 200)
        self.utilisateur.refresh_from_db()
        self.assertEqual(self.utilisateur.username, "nouveau-nom")
        self.assertEqual(self.utilisateur.email, "nouveau@redafrik.demo")
        self.assertFalse(self.utilisateur.email_verifie)


class TestAntiForceBrute(APITestCase):
    def test_verrouillage_apres_seuil_echecs(self):
        for _ in range(6):
            self.client.post(
                "/api/auth/connexion/",
                {"username": "demo", "password": "mauvais"},
                content_type="application/json",
            )
        # Le 7e essai, même avec le bon mot de passe, est bloqué
        User.objects.create_user(
            username="demo", email="demo@redafrik.demo", password="motdepasse123"
        )
        reponse = self.client.post(
            "/api/auth/connexion/",
            {"username": "demo", "password": "motdepasse123"},
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 401)
        self.assertTrue(
            EchecConnexion.objects.filter(clef="demo").count() >= 6
        )
