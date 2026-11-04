from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(request):
    """Return a lightweight response when the application process is alive."""
    return JsonResponse({
        'status': 'ok',
        'service': 'rosana-api',
        'version': settings.APP_VERSION,
    })


@require_GET
def readiness(request):
    """Return whether the application can reach its primary database."""
    try:
        connection.ensure_connection()
    except OperationalError:
        return JsonResponse(
            {
                'status': 'unavailable',
                'service': 'rosana-api',
                'version': settings.APP_VERSION,
                'database': 'unavailable',
            },
            status=503,
        )

    return JsonResponse({
        'status': 'ok',
        'service': 'rosana-api',
        'version': settings.APP_VERSION,
        'database': 'ok',
    })
