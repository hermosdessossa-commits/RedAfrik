"""Tests du Lot 2 : import d'images (posts, bannières, avatars)."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from apps.users.models import User


def _fabriquer_image(nom="photo.png", format_="PNG", couleur=(255, 0, 0), taille=(64, 64)):
    """Construit un fichier image PNG valide en mémoire."""
    tampon = BytesIO()
    Image.new("RGB", taille, couleur).save(tampon, format=format_)
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/" + format_.lower())


def _fabriquer_image_lourde():
    """Image valide dépassant la limite de 5 Mo (bruit aléatoire peu compressible)."""
    import random

    random.seed(42)
    pixels = bytes(random.getrandbits(8) for _ in range(2600 * 2600 * 3))
    tampon = BytesIO()
    Image.frombytes("RGB", (2600, 2600), pixels).save(tampon, format="PNG")
    return SimpleUploadedFile("lourde.png", tampon.getvalue(), content_type="image/png")


def _fabriquer_fichier(nom="fichier.txt", taille=1024):
    return SimpleUploadedFile(nom, b"x" * taille, content_type="text/plain")


class TestUploadPost(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="kofi", email="kofi@redafrik.demo", password="motdepasse123"
        )
        self.client.force_authenticate(self.utilisateur)
        self.communaute = self.apps_communaute()

    @staticmethod
    def apps_communaute():
        from apps.communities.models import Communaute

        createur = User.objects.get(username="kofi")
        return Communaute.objects.create(
            nom="art-africain", description="Galerie", createur=createur
        )

    def test_creer_post_avec_image(self):
        reponse = self.client.post(
            "/api/posts/",
            {
                "titre": "Mon œuvre",
                "contenu": "",
                "communaute": "art-africain",
                "image": _fabriquer_image(),
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 201)
        self.assertIn("/media/posts/", reponse.data["image"])

    def test_post_avec_fichier_non_image_est_refuse(self):
        reponse = self.client.post(
            "/api/posts/",
            {
                "titre": "Pièce jointe",
                "communaute": "art-africain",
                "image": _fabriquer_fichier(),
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Format d'image", str(reponse.data))

    def test_post_avec_image_trop_lourde_est_refuse(self):
        reponse = self.client.post(
            "/api/posts/",
            {
                "titre": "Image lourde",
                "communaute": "art-africain",
                "image": _fabriquer_image_lourde(),
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("5 Mo", str(reponse.data))

    def test_post_sans_contenu_ni_image_toujours_refuse(self):
        reponse = self.client.post(
            "/api/posts/",
            {"titre": "Vide", "communaute": "art-africain"},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)

    def test_upload_anonyme_refuse(self):
        self.client.force_authenticate(None)
        reponse = self.client.post(
            "/api/posts/",
            {
                "titre": "Anonyme",
                "communaute": "art-africain",
                "image": _fabriquer_image(),
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 401)


class TestUploadCommunaute(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="aya", email="aya@redafrik.demo", password="motdepasse123"
        )
        self.client.force_authenticate(self.utilisateur)

    def test_creer_communaute_avec_banniere(self):
        reponse = self.client.post(
            "/api/communautes/",
            {"nom": "photo-dakar", "description": "", "banniere": _fabriquer_image("banniere.png")},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 201)
        self.assertIn("/media/communautes/", reponse.data["banniere"])

    def test_banniere_non_image_refusee(self):
        reponse = self.client.post(
            "/api/communautes/",
            {"nom": "photo-dakar", "description": "", "banniere": _fabriquer_fichier()},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)


class TestUploadAvatar(APITestCase):
    def setUp(self):
        self.utilisateur = User.objects.create_user(
            username="issouf", email="issouf@redafrik.demo", password="motdepasse123"
        )
        self.client.force_authenticate(self.utilisateur)

    def test_mettre_a_jour_avatar(self):
        reponse = self.client.patch(
            "/api/utilisateurs/profil/",
            {"avatar": _fabriquer_image("avatar.png")},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("/media/avatars/", reponse.data["avatar"])

    def test_avatar_non_image_refuse(self):
        reponse = self.client.patch(
            "/api/utilisateurs/profil/",
            {"avatar": _fabriquer_fichier()},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 400)
