"""Audit task dispatcher.

In production (eager_execution=False) the pipeline is sent to a Celery worker
via the Redis broker — fire-and-forget, returns immediately.

In dev/test mode (eager_execution=True) the pipeline runs in a daemon thread
in the same process — no Redis or separate worker required.  Both paths execute
identical code; only the execution context differs.
"""

from __future__ import annotations

import threading

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def dispatch_audit(audit_id: int) -> None:
    from app.worker import run_audit

    if settings.eager_execution:
        logger.info("Audit %s: eager mode — running pipeline in background thread", audit_id)
        thread = threading.Thread(target=run_audit, args=(audit_id,), daemon=True)
        thread.start()
    else:
        task = run_audit.delay(audit_id)
        logger.info("Audit %s: dispatched to Celery — task_id=%s", audit_id, task.id)
