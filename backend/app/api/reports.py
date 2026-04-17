from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.database import Audit, Finding, Report
from app.models.schemas import FindingOut, ReportOut

router = APIRouter(tags=["reports"])


@router.get("/audits/{audit_id}/findings", response_model=list[FindingOut])
async def list_findings(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding).where(Finding.audit_id == audit_id))
    return result.scalars().all()


@router.get("/audits/{audit_id}/report", response_model=ReportOut)
async def get_report(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Audit)
        .where(Audit.id == audit_id)
        .options(selectinload(Audit.report), selectinload(Audit.findings))
    )
    audit = result.scalar_one_or_none()
    if not audit or not audit.report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportOut(
        id=audit.report.id,
        audit_id=audit.id,
        summary=audit.report.summary,
        score=audit.report.score,
        pdf_path=audit.report.pdf_path,
        generated_at=audit.report.generated_at,
        findings=[FindingOut.model_validate(f) for f in audit.findings],
    )


@router.get("/audits/{audit_id}/report/pdf")
async def get_report_pdf(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.audit_id == audit_id))
    report = result.scalar_one_or_none()
    if not report or not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(report.pdf_path, media_type="application/pdf")
