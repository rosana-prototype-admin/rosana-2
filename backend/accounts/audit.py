from .models import AuditEvent


def record_admin_event(request, action, target, before=None, after=None, group=None):
    """Persist a small, JSON-safe before/after snapshot for a privileged action."""
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    return AuditEvent.objects.create(
        actor=request.user if request and request.user.is_authenticated else None,
        action=action,
        entity_type=target.__class__.__name__,
        entity_id=str(target.pk),
        group=group,
        before=before or {},
        after=after or {},
        ip_address=ip_address,
    )
