"""Read current retained synthetic text/PDF facts; never restore a model prompt."""
import hashlib

from .intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
from .store import canonical
from .ui_read_model import IntakeReadModel


__all__=['read_current_conducted_plan_from_facts']


def read_current_conducted_plan_from_facts(workspace,intake_id,*,method,
        expected_revision=None,expected_context_sha256=None):
    """One genuine current read and one facts build, preserving all parent results.

    Optional None pins select the just-read current snapshot, not approval or the
    original provider context. Existing reader errors and controls propagate.
    """
    native=IntakeReadModel(workspace).current_conducted_plan_context(intake_id)
    context,analysis=native['context'],native['analysis']
    current_sha256=hashlib.sha256(canonical(context).encode('utf-8')).hexdigest()
    facts_plan=build_conducted_plan_from_intake_facts(context,analysis,
        expected_revision=context['revision'] if expected_revision is None else expected_revision,
        expected_context_sha256=current_sha256 if expected_context_sha256 is None else expected_context_sha256,
        method=method)
    return dict(context=context,analysis=analysis,facts_plan=facts_plan)
