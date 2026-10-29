from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('groups', views.GroupViewSet, basename='group')

urlpatterns = router.urls
