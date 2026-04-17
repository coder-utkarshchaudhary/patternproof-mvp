from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.database import Audit, AuditStatus
from app.models.schemas import AuditCreate, AuditDetail, AuditOut

router = APIRouter(tags=["audits"])


@router.post("/audits", response_model=AuditOut, status_code=201)
async def create_audit(body: AuditCreate, db: AsyncSession = Depends(get_db)):
    audit = Audit(url=str(body.url), status=AuditStatus.QUEUED)
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    # TODO: enqueue Celery task – run_audit.delay(audit.id)
    return audit


@router.get("/audits", response_model=list[AuditOut])
async def list_audits(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Audit).order_by(Audit.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.get("/audits/{audit_id}", response_model=AuditDetail)
async def get_audit(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Audit).where(Audit.id == audit_id).options(selectinload(Audit.pages))
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit
