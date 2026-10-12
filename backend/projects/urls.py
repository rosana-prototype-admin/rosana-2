from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('opportunities', views.OpportunityViewSet, basename='opportunity')
router.register('strategies', views.StrategyViewSet, basename='strategy')
router.register('interventions', views.InterventionViewSet, basename='intervention')
router.register('projects', views.ProjectViewSet, basename='project')
router.register('organizations', views.OrganizationViewSet, basename='organization')

nested_urlpatterns = [
    path(
        'opportunities/<int:opportunity_pk>/strategies/',
        views.StrategyViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='opportunity-strategy-list',
    ),
    path(
        'strategies/<int:strategy_pk>/interventions/',
        views.InterventionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='strategy-intervention-list',
    ),
    path(
        'strategies/<int:strategy_pk>/projects/',
        views.ProjectViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='strategy-project-list',
    ),
]

urlpatterns = nested_urlpatterns + router.urls
