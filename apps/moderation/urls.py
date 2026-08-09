"""Routes de l'app moderation."""

from rest_framework.routers import DefaultRouter

from .views import ModerateurViewSet, SignalementViewSet

router = DefaultRouter()
router.register("moderateurs", ModerateurViewSet, basename="moderateur")
router.register("signalements", SignalementViewSet, basename="signalement")

urlpatterns = router.urls
