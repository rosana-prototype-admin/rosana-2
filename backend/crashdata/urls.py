from rest_framework.routers import DefaultRouter

from .views import CrashCasualtyConversionTableViewSet

router = DefaultRouter()
router.register('crash-conversion-tables', CrashCasualtyConversionTableViewSet, basename='crash-conversion-table')

urlpatterns = router.urls
