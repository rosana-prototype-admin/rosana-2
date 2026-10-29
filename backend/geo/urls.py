from rest_framework.routers import DefaultRouter

from .views import CountryCodeViewSet, JcodeViewSet

router = DefaultRouter()
router.register('jcodes', JcodeViewSet, basename='jcode')
router.register('country-codes', CountryCodeViewSet, basename='countrycode')

urlpatterns = router.urls
