from rest_framework.permissions import SAFE_METHODS, BasePermission


def can_read(user, project):
    return (
        project.owner_id == user.pk
        or project.editors.filter(pk=user.pk).exists()
        or project.guests.filter(pk=user.pk).exists()
    )


def can_write(user, project):
    return project.owner_id == user.pk or project.editors.filter(pk=user.pk).exists()


class ProjectAccessPermission(BasePermission):
    """
    Object-level permission shared by Project, CourseOfAction, and Intervention
    viewsets. Every model in the hierarchy implements get_project() so this one
    class can enforce owner/editor (read+write) vs. guest (read-only) access
    without duplicating the check per model.
    """

    def has_object_permission(self, request, view, obj):
        project = obj.get_project()
        if request.method in SAFE_METHODS:
            return can_read(request.user, project)
        return can_write(request.user, project)


class AncestorScopedMixin:
    """
    Shared behavior for viewsets nested under an ancestor object (a Project for
    CourseOfAction, a CourseOfAction for Intervention): resolves + authorizes
    the ancestor from the URL, never from client-supplied body data, and uses
    it to scope create.
    """

    def get_ancestor(self):
        raise NotImplementedError

    def perform_create(self, serializer):
        ancestor = self.get_ancestor()
        if not can_write(self.request.user, ancestor.get_project()):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied('You do not have write access to this project.')
        serializer.save(**self.get_create_kwargs(ancestor))

    def get_create_kwargs(self, ancestor):
        raise NotImplementedError
