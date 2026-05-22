"""ReportGenerator slave agent — final node of the audit graph.

Aggregates findings, scores DPDP/CCPA compliance, pulls Exa references for the
detected pattern types, renders a PDF, uploads it to Supabase Storage, and
persists the report row.
"""

import time

from app.agents.state import AuditState
from app.db import repo
from app.models.taxonomy import AuditStatus
from app.services import exa_client, storage
from app.services.pdf_generator import generate_pdf_bytes
from app.services.report_builder import ReportBuilder
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def report_node(state: AuditState) -> dict:
    logger.info(
        "Audit %s: report_node starting — pages=%d findings=%d",
        state.audit_id, len(state.visited_pages), len(state.findings),
    )
    t0 = time.monotonic()

    repo.update_audit_status(
        state.audit_id, AuditStatus.GENERATING_REPORT, progress_message="Generating report…"
    )

    logger.info("Audit %s: building report structure", state.audit_id)
    builder = ReportBuilder()
    result = builder.build_report(
        url=state.target_url,
        page_count=len(state.visited_pages),
        findings=state.findings,
    )
    deduped = result["findings"]
    logger.info(
        "Audit %s: report built — score=%s deduped_findings=%d",
        state.audit_id, result["score"], len(deduped),
    )

    ccpa_patterns = [f.ccpa_pattern for f in deduped if f.ccpa_pattern]
    logger.info("Audit %s: fetching Exa references for %d CCPA pattern(s)", state.audit_id, len(set(ccpa_patterns)))
    references = exa_client.references_for(ccpa_patterns)
    logger.info("Audit %s: got %d reference(s) from Exa", state.audit_id, len(references))

    pdf_path = None
    try:
        logger.info("Audit %s: generating PDF", state.audit_id)
        pdf_bytes = generate_pdf_bytes(
            url=state.target_url,
            page_count=len(state.visited_pages),
            score=result["score"],
            summary=result["summary"],
            findings=deduped,
            references=references,
        )
        pdf_path = storage.upload_report_pdf(state.audit_id, pdf_bytes)
        logger.info("Audit %s: PDF uploaded → %s", state.audit_id, pdf_path)
    except Exception as e:  # noqa: BLE001
        logger.error("Audit %s: PDF generation/upload failed — %s", state.audit_id, e)

    repo.upsert_report(
        state.audit_id,
        {
            "summary": result["summary"],
            "score": result["score"],
            "pdf_path": pdf_path,
            "references": references,
        },
    )

    elapsed = time.monotonic() - t0
    logger.info(
        "Audit %s: report_node done in %.1fs — score=%s findings=%d refs=%d pdf=%s",
        state.audit_id, elapsed, result["score"], len(deduped), len(references),
        "yes" if pdf_path else "no",
    )
    return {"is_complete": True, "next_action": "complete"}
