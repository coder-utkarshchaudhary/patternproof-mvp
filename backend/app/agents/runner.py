"""Pipeline runner — invokes the compiled audit graph for one audit.

Called by the Celery worker. Keeps the recursion budget generous enough for the
manager↔slave feedback loop (each page analysis and feedback pass is a hop).
"""

import logging
import time

from app.agents.graph import audit_graph
from app.agents.state import AuditState
from app.core.config import settings
from app.db import repo

logger = logging.getLogger(__name__)


def run_pipeline(audit_id: int) -> None:
    audit = repo.get_audit(audit_id)
    if not audit:
        raise RuntimeError(f"Audit {audit_id} not found")

    logger.info("Audit %s: pipeline starting (url=%s)", audit_id, audit["url"])
    t0 = time.monotonic()

    state = AuditState(audit_id=audit_id, target_url=audit["url"])
    recursion_limit = settings.agent_max_iterations * 2 + 10
    logger.info("Audit %s: recursion_limit=%d", audit_id, recursion_limit)

    final_state = audit_graph.invoke(state, config={"recursion_limit": recursion_limit})

    elapsed = time.monotonic() - t0
    findings_count = len(final_state.get("findings", [])) if isinstance(final_state, dict) else 0
    pages_count = len(final_state.get("visited_pages", [])) if isinstance(final_state, dict) else 0
    logger.info(
        "Audit %s: pipeline finished in %.1fs — pages=%d findings=%d",
        audit_id, elapsed, pages_count, findings_count,
    )
