"""
Routage global du projet RedAfrik.

Toutes les routes de l'API sont exposées sous le préfixe /api/ et chaque
app Django déclare ses propres routes dans son fichier urls.py.
La documentation OpenAPI est servie sur /api/docs/ (Swagger UI).
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from core.admin import site as redafrik_admin
from core.views import index_api

urlpatterns = [
    path("admin/", redafrik_admin.urls),
    # Index descriptif de l'API (tous les endpoints)
    path("api/", index_api, name="index-api"),
    # Documentation OpenAPI : schéma et interface Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    # Chaque app expose ses endpoints sous le préfixe /api/
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.communities.urls")),
    path("api/", include("apps.posts.urls")),
    path("api/", include("apps.comments.urls")),
    path("api/", include("apps.moderation.urls")),
    path("api/", include("core.urls")),
    # Interface web (SPA)
    path("", include("frontend.urls")),
]

# En développement uniquement : servir les fichiers uploadés (avatars, images)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
