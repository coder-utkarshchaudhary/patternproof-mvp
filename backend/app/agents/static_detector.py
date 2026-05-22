"""StaticDarkPatternDetector slave agent.

For each pending page, spawns the visual + semantic ephemeral sub-agents,
merges and dedupes their findings, persists them, and marks the page analyzed.
Pages whose analysis raised are flagged ``analysis_ok=False`` so the manager can
schedule a feedback pass.
"""

import logging
import time

from app.agents.ephemeral import semantic_subagent, visual_subagent
from app.agents.state import AuditState, DetectedFinding, PageContext
from app.db import repo

logger = logging.getLogger(__name__)


def _dedupe(findings: list[DetectedFinding]) -> list[DetectedFinding]:
    seen: set[tuple] = set()
    unique: list[DetectedFinding] = []
    for f in findings:
        key = (f.dp_type, f.page_url)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _analyze_page(audit_id: int, page: PageContext) -> tuple[list[DetectedFinding], bool]:
    findings: list[DetectedFinding] = []
    ok = True

    logger.info("Audit %s: visual sub-agent starting for %s", audit_id, page.url)
    try:
        visual = visual_subagent(page)
        findings += visual
        logger.info("Audit %s: visual sub-agent found %d detection(s) on %s", audit_id, len(visual), page.url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: visual sub-agent FAILED for %s — %s", audit_id, page.url, e)
        ok = False

    logger.info("Audit %s: semantic sub-agent starting for %s", audit_id, page.url)
    try:
        semantic = semantic_subagent(page)
        findings += semantic
        logger.info("Audit %s: semantic sub-agent found %d finding(s) on %s", audit_id, len(semantic), page.url)
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: semantic sub-agent FAILED for %s — %s", audit_id, page.url, e)
        ok = False

    deduped = _dedupe(findings)
    if len(deduped) < len(findings):
        logger.debug("Audit %s: deduped %d → %d findings on %s", audit_id, len(findings), len(deduped), page.url)
    return deduped, ok


def static_detector_node(state: AuditState) -> dict:
    total = len(state.pending_pages)
    logger.info("Audit %s: static_detector starting — %d page(s) to analyze", state.audit_id, total)
    t0 = time.monotonic()

    new_findings: list[DetectedFinding] = []
    analyzed: list[PageContext] = []

    for idx, page in enumerate(state.pending_pages):
        logger.info(
            "Audit %s: analyzing page %d/%d — %s",
            state.audit_id, idx + 1, total, page.url,
        )
        pt = time.monotonic()
        page_findings, ok = _analyze_page(state.audit_id, page)
        page.analyzed = True
        page.analysis_ok = ok

        if page_findings:
            rows = [
                {
                    "page_id": f.page_id,
                    "category": f.category,
                    "dp_type": f.dp_type,
                    "ccpa_pattern": f.ccpa_pattern,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "explanation": f.explanation,
                    "evidence_screenshot_path": f.evidence_screenshot_path,
                    "page_url": f.page_url,
                    "bounding_box": f.bounding_box,
                    "confidence_score": f.confidence_score,
                    "is_dynamic": f.is_dynamic,
                }
                for f in page_findings
            ]
            repo.insert_findings(state.audit_id, rows)

        repo.add_memory(
            state.audit_id,
            agent="static_detector",
            kind="page_output",
            payload={"page_url": page.url, "findings": len(page_findings), "ok": ok},
        )
        logger.info(
            "Audit %s: page %d/%d done in %.1fs — findings=%d ok=%s url=%s",
            state.audit_id, idx + 1, total, time.monotonic() - pt,
            len(page_findings), ok, page.url,
        )
        new_findings += page_findings
        analyzed.append(page)

    elapsed = time.monotonic() - t0
    failed_count = sum(1 for p in analyzed if not p.analysis_ok)
    logger.info(
        "Audit %s: static_detector done in %.1fs — analyzed=%d findings=%d failed=%d",
        state.audit_id, elapsed, len(analyzed), len(new_findings), failed_count,
    )
    if new_findings:
        by_severity = {}
        for f in new_findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        logger.info("Audit %s: findings by severity — %s", state.audit_id, by_severity)

    return {
        "findings": state.findings + new_findings,
        "visited_pages": state.visited_pages + analyzed,
        "pending_pages": [],
        "next_action": "manager",
    }
