"""Routes du noyau : journal des actions et contrôle de santé."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import JournalActionViewSet, sante

router = DefaultRouter()
router.register("actions", JournalActionViewSet, basename="action")

urlpatterns = [
    path("sante/", sante, name="sante"),
    *router.urls,
]