"""
Tests du journal des actions : IP + géolocalisation à chaque requête.

Couvre la journalisation (anonyme, JWT, proxy de confiance), l'endpoint
staff (masquage IP), la géolocalisation, la purge de rétention et le
contrôle de santé.

Lancement : python manage.py test tests --settings=config.settings_test
"""

from datetime import timedelta

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User
from core.geoip import geolocaliser, masquer_ip
from core.models import JournalAction


def se_connecter(client, nom_utilisateur, mot_de_passe):
    reponse = client.post(
        "/api/auth/connexion/",
        {"username": nom_utilisateur, "password": mot_de_passe},
        format="json",
    )
    return reponse.data["access"]


def en_tete(jeton):
    return {"HTTP_AUTHORIZATION": f"Bearer {jeton}"}


class TestJournalisation(APITestCase):
    def test_chaque_requete_journalisee(self):
        reponse = self.client.get("/api/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(JournalAction.objects.count(), 1)
        entree = JournalAction.objects.get()
        self.assertEqual(entree.chemin, "/api/")
        self.assertEqual(entree.methode, "GET")
        self.assertEqual(entree.statut, 200)
        self.assertEqual(entree.adresse_ip, "127.0.0.1")
        self.assertIsNone(entree.utilisateur)
        self.assertIsNone(entree.geolocalisation)

    def test_utilisateur_jwt_associe(self):
        utilisateur = User.objects.create_user(
            "kwame", "kwame@example.com", "MotDePasse!123"
        )
        jeton = se_connecter(self.client, "kwame", "MotDePasse!123")
        self.client.get("/api/utilisateurs/moi/", **en_tete(jeton))
        entree = JournalAction.objects.filter(
            chemin="/api/utilisateurs/moi/"
        ).get()
        self.assertEqual(entree.utilisateur, utilisateur)

    def test_assets_exclus_du_journal(self):
        self.client.get("/static/style.css")
        self.client.get("/favicon.ico")
        self.assertEqual(JournalAction.objects.count(), 0)

    def test_xff_ignore_sans_proxy_de_confiance(self):
        self.client.get("/api/", HTTP_X_FORWARDED_FOR="203.0.113.9")
        entree = JournalAction.objects.get()
        self.assertEqual(entree.adresse_ip, "127.0.0.1")

    def test_xff_utilise_derriere_proxy_de_confiance(self):
        with override_settings(TRUSTED_PROXY_IPS=["127.0.0.1"]):
            self.client.get(
                "/api/", HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.1"
            )
        entree = JournalAction.objects.get()
        self.assertEqual(entree.adresse_ip, "203.0.113.9")

    def test_journal_desactive_par_reglage(self):
        with override_settings(JOURNAL_ACTIONS_ENABLED=False):
            self.client.get("/api/")
        self.assertEqual(JournalAction.objects.count(), 0)


class TestEndpointJournal(APITestCase):
    def setUp(self):
        self.mot_de_passe = "MotDePasse!123"
        self.utilisateur = User.objects.create_user(
            "amina", "amina@example.com", self.mot_de_passe
        )
        self.modo = User.objects.create_user(
            "modo", "modo@example.com", self.mot_de_passe, is_staff=True
        )
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", self.mot_de_passe
        )
        JournalAction.objects.create(
            utilisateur=self.utilisateur,
            methode="GET",
            chemin="/api/posts/",
            statut=200,
            adresse_ip="203.0.113.42",
        )
        self.chemin = "/api/actions/"

    def test_non_authentifie_refuse(self):
        self.assertEqual(
            self.client.get(self.chemin).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_utilisateur_simple_refuse(self):
        jeton = se_connecter(self.client, "amina", self.mot_de_passe)
        reponse = self.client.get(self.chemin, **en_tete(jeton))
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_voit_ip_masquee(self):
        jeton = se_connecter(self.client, "modo", self.mot_de_passe)
        reponse = self.client.get(self.chemin, **en_tete(jeton))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        trace = self._trace_posts(reponse)
        self.assertEqual(trace["adresse_ip"], "203.0.113.***")
        self.assertEqual(trace["utilisateur"], "amina")

    def test_superutilisateur_voit_ip_complete(self):
        jeton = se_connecter(self.client, "admin", self.mot_de_passe)
        reponse = self.client.get(self.chemin, **en_tete(jeton))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        trace = self._trace_posts(reponse)
        self.assertEqual(trace["adresse_ip"], "203.0.113.42")

    @staticmethod
    def _trace_posts(reponse):
        return next(
            r for r in reponse.data["results"] if r["chemin"] == "/api/posts/"
        )

    def test_filtres_utilisateur_et_chemin(self):
        jeton = se_connecter(self.client, "modo", self.mot_de_passe)
        reponse = self.client.get(
            f"{self.chemin}?chemin=posts", **en_tete(jeton)
        )
        self.assertEqual(len(reponse.data["results"]), 1)
        reponse = self.client.get(
            f"{self.chemin}?utilisateur=99999", **en_tete(jeton)
        )
        self.assertEqual(len(reponse.data["results"]), 0)


class TestGeolocalisationEtPurge(APITestCase):
    def test_geolocalisation_ip_privee(self):
        for ip in ("127.0.0.1", "192.168.1.10", "10.0.0.5", "::1"):
            self.assertIsNone(geolocaliser(ip))
        self.assertIsNone(geolocaliser(None))

    def test_masquage_ip(self):
        self.assertIsNone(masquer_ip(None))
        self.assertEqual(masquer_ip("203.0.113.42"), "203.0.113.***")
        self.assertIn("****", masquer_ip("2001:db8::1"))

    def test_purge_journal_respecte_la_retention(self):
        ancienne = JournalAction.objects.create(
            methode="GET", chemin="/api/", statut=200
        )
        JournalAction.objects.filter(pk=ancienne.pk).update(
            date_creation=timezone.now() - timedelta(days=91)
        )
        recente = JournalAction.objects.create(
            methode="GET", chemin="/api/", statut=200
        )
        call_command("purge_journal")
        self.assertFalse(
            JournalAction.objects.filter(pk=ancienne.pk).exists()
        )
        self.assertTrue(JournalAction.objects.filter(pk=recente.pk).exists())

    def test_purge_avec_jours_explicites(self):
        ancienne = JournalAction.objects.create(
            methode="POST", chemin="/api/posts/", statut=201
        )
        JournalAction.objects.filter(pk=ancienne.pk).update(
            date_creation=timezone.now() - timedelta(days=31)
        )
        call_command("purge_journal", "--jours", "30")
        self.assertFalse(JournalAction.objects.filter(pk=ancienne.pk).exists())


class TestSante(APITestCase):
    def test_sante_ok(self):
        reponse = self.client.get("/api/sante/")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["statut"], "ok")