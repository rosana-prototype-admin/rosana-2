from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('projects', views.ProjectViewSet, basename='project')
router.register('courses-of-action', views.CourseOfActionViewSet, basename='courseofaction')
router.register('interventions', views.InterventionViewSet, basename='intervention')

nested_urlpatterns = [
    path(
        'projects/<int:project_pk>/courses-of-action/',
        views.CourseOfActionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-courseofaction-list',
    ),
    path(
        'courses-of-action/<int:coa_pk>/interventions/',
        views.InterventionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='courseofaction-intervention-list',
    ),
]

urlpatterns = nested_urlpatterns + router.urls
