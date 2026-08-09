"""Routes de l'app communities."""

from rest_framework.routers import DefaultRouter

from .views import CommunauteViewSet

router = DefaultRouter()
router.register("communautes", CommunauteViewSet, basename="communaute")

urlpatterns = router.urls
