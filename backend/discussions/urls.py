from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('comments', views.CommentViewSet, basename='comment')

nested_urlpatterns = [
    path(
        'projects/<int:project_pk>/comments/',
        views.CommentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-comment-list',
    ),
]

urlpatterns = nested_urlpatterns + router.urls
