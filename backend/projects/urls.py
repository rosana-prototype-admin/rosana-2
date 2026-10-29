from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('opportunities', views.OpportunityViewSet, basename='opportunity')
router.register('projects', views.ProjectViewSet, basename='project')
router.register('sites', views.SiteViewSet, basename='site')
router.register('strategies', views.StrategyViewSet, basename='strategy')

nested_urlpatterns = [
    path(
        'opportunities/<int:opportunity_pk>/projects/',
        views.ProjectViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='opportunity-project-list',
    ),
    path(
        'projects/<int:project_pk>/sites/',
        views.SiteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-site-list',
    ),
    path(
        'sites/<int:site_pk>/strategies/',
        views.StrategyViewSet.as_view({'get': 'list'}),
        name='site-strategy-list',
    ),
]

urlpatterns = nested_urlpatterns + router.urls
