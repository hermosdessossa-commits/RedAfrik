"""
Routage global du projet RedAfrik.

Toutes les routes de l'API sont exposées sous le préfixe /api/ et chaque
app Django déclare ses propres routes dans son fichier urls.py.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Chaque app expose ses endpoints sous le préfixe /api/
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.communities.urls")),
    path("api/", include("apps.posts.urls")),
    path("api/", include("apps.comments.urls")),
    path("api/", include("apps.moderation.urls")),
]
