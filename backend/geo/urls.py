from rest_framework.routers import DefaultRouter

from .views import JcodeViewSet

router = DefaultRouter()
router.register('jcodes', JcodeViewSet, basename='jcode')

urlpatterns = router.urls
