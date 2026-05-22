from fastapi import APIRouter, HTTPException, Response

from app.db import repo
from app.models.schemas import FindingOut, ReportOut
from app.services import storage

router = APIRouter(tags=["reports"])


@router.get("/audits/{audit_id}/findings", response_model=list[FindingOut])
def list_findings(audit_id: int):
    return repo.list_findings(audit_id)


@router.get("/audits/{audit_id}/report", response_model=ReportOut)
def get_report(audit_id: int):
    report = repo.get_report(audit_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = [FindingOut.model_validate(f) for f in repo.list_findings(audit_id)]
    return ReportOut(
        id=report["id"],
        audit_id=audit_id,
        summary=report["summary"],
        score=report["score"],
        pdf_path=report.get("pdf_path"),
        references=report.get("references") or [],
        generated_at=report["generated_at"],
        findings=findings,
    )


@router.get("/audits/{audit_id}/report/pdf")
def get_report_pdf(audit_id: int):
    report = repo.get_report(audit_id)
    if not report or not report.get("pdf_path"):
        raise HTTPException(status_code=404, detail="PDF report not found")
    data = storage.download(report["pdf_path"])
    if data is None:
        raise HTTPException(status_code=404, detail="PDF artifact unavailable")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="audit-{audit_id}.pdf"'},
    )
