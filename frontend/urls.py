"""Routes du frontend : la SPA capture toutes les routes web."""

from django.urls import path, re_path

from .views import IndexView

urlpatterns = [
    path("", IndexView.as_view(), name="accueil"),
    # Toutes les autres routes non-API servent l'application, afin que les
    # liens partagés sans fragment (ex : /c/tech-afrique) fonctionnent au
    # rechargement. L'index convertit le chemin en fragment côté client.
    re_path(r"^(?!api/|admin/|static/|media/).*", IndexView.as_view()),
]