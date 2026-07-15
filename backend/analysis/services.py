from django.utils import timezone


def run_stub_analysis(course_of_action):
    """
    Intentional stub: the real crash-reduction/cost-benefit analysis has not
    been designed yet. Returns a deterministic placeholder payload so the
    Run Analysis flow is wired end-to-end and can be swapped for a real
    implementation later without touching any other file.
    """
    return {
        'summary': 'Analysis not yet implemented.',
        'metrics': {},
        'intervention_count': course_of_action.interventions.count(),
        'generated_at': timezone.now().isoformat(),
    }
