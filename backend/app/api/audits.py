import logging

from fastapi import APIRouter, HTTPException

from app.db import repo
from app.models.schemas import AuditCreate, AuditDetail, AuditOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["audits"])


@router.post("/audits", response_model=AuditOut, status_code=201)
def create_audit(body: AuditCreate):
    audit = repo.create_audit(str(body.url))
    audit_id = audit["id"]
    logger.info("Audit %s created for URL=%s — enqueueing pipeline task", audit_id, body.url)

    # Enqueue the pipeline. Imported lazily so the API process doesn't need the
    # full agent/ML dependency graph just to schedule a task.
    from app.worker import run_audit

    task = run_audit.delay(audit_id)
    logger.info("Audit %s enqueued — celery task_id=%s", audit_id, task.id)
    return audit


@router.get("/audits", response_model=list[AuditOut])
def list_audits(limit: int = 20, offset: int = 0):
    return repo.list_audits(limit=limit, offset=offset)


@router.get("/audits/{audit_id}", response_model=AuditDetail)
def get_audit(audit_id: int):
    audit = repo.get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return {**audit, "pages": repo.list_pages(audit_id)}
