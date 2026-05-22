import logging
import time
from datetime import datetime, timezone

from celery import Celery

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

celery_app = Celery("pattern_proof", broker=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="run_audit")
def run_audit(audit_id: int) -> None:
    """Orchestrate a full dark-pattern audit pipeline.

    Owns the top-level lifecycle: start/finish notifications, terminal status,
    ticket archiving, and error handling. Per-stage work is driven by the
    LangGraph pipeline.
    """
    from app.agents.runner import run_pipeline
    from app.db import repo
    from app.models.taxonomy import AuditStatus
    from app.services import notify

    logger.info("=== Audit %s: task picked up by worker ===", audit_id)
    t0 = time.monotonic()

    audit = repo.get_audit(audit_id)
    if not audit:
        logger.error("run_audit: audit %s not found — aborting", audit_id)
        return

    logger.info("Audit %s: URL=%s, status=%s", audit_id, audit["url"], audit["status"])
    notify.notify_started(audit)
    logger.info("Notification for audit start has been sent. Check slack and whatsapp.")

    try:
        run_pipeline(audit_id)

        elapsed = time.monotonic() - t0
        repo.update_audit_status(
            audit_id,
            AuditStatus.COMPLETED,
            progress_message="Audit complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        _archive_tickets(repo, audit_id, final_status="completed")
        fresh = repo.get_audit(audit_id) or audit
        notify.notify_completed(fresh)
        logger.info("=== Audit %s: COMPLETED in %.1fs ===", audit_id, elapsed)
        logger.info("Notification for audit complete has been sent. Check slack and whatsapp.")

    except Exception as e:  # noqa: BLE001
        elapsed = time.monotonic() - t0
        logger.exception("=== Audit %s: FAILED after %.1fs — %s ===", audit_id, elapsed, e)
        repo.update_audit_status(
            audit_id,
            AuditStatus.FAILED,
            progress_message="Audit failed",
            error_message=str(e)[:500],
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        _archive_tickets(repo, audit_id, final_status="failed", result={"error": str(e)[:500]})


def _archive_tickets(repo, audit_id: int, *, final_status: str, result: dict | None = None) -> None:
    """Move all active tickets for this audit into ticket_archive."""
    try:
        repo.archive_tickets(audit_id, final_status=final_status, result=result or {})
        logger.info("Audit %s: tickets archived with status=%s", audit_id, final_status)
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: failed to archive tickets — %s", audit_id, e)
