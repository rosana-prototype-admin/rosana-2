from rest_framework.routers import DefaultRouter

from .views import FocusAreaViewSet, InterventionTypeViewSet

router = DefaultRouter()
router.register('focus-areas', FocusAreaViewSet, basename='focusarea')
router.register('intervention-types', InterventionTypeViewSet, basename='interventiontype')

urlpatterns = router.urls
