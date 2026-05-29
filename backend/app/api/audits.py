from fastapi import APIRouter, HTTPException

from app.core.dispatch import dispatch_audit
from app.core.logging_config import get_logger
from app.db import repo
from app.models.schemas import AuditCreate, AuditDetail, AuditOut

logger = get_logger(__name__)
router = APIRouter(tags=["audits"])

@router.post("/audits", response_model=AuditOut, status_code=201)
def create_audit(body: AuditCreate):
    audit = repo.create_audit(str(body.url))
    audit_id = audit["id"]
    logger.info("Audit %s created for URL=%s — dispatching pipeline", audit_id, body.url)
    dispatch_audit(audit_id)
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
