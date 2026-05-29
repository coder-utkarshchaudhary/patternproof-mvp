"""Key-based job orchestration API.

POST /api/jobs   — Start a new audit job; returns an opaque job_key immediately.
GET  /api/jobs/{key} — Poll job status with a live markdown progress summary.

Job states (simplified from internal AuditStatus):
  processing — any non-terminal status
  done       — audit completed successfully
  failed     — audit failed or timed out
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dispatch import dispatch_audit
from app.core.logging_config import get_logger
from app.db import repo
from app.models.schemas import AuditCreate, JobCreateOut, JobStatusOut

logger = get_logger(__name__)
router = APIRouter(tags=["jobs"])

_TERMINAL_MAP = {
    "completed": "done",
    "failed": "failed",
}

_ACTION_ICON = {
    "plan": "📋",
    "crawl": "🌐",
    "static_analysis": "🔍",
    "report": "📄",
}


@router.post("/jobs", response_model=JobCreateOut, status_code=201)
def create_job(body: AuditCreate):
    """Create an audit job and return the job key immediately.

    The pipeline runs in the background; use GET /api/jobs/{key} to track it.
    """
    audit = repo.create_audit(str(body.url))
    audit_id = audit["id"]
    logger.info("Job %s created for URL=%s — dispatching pipeline", audit_id, body.url)
    dispatch_audit(audit_id)
    return JobCreateOut(
        job_key=str(audit_id),
        url=audit["url"],
        status="processing",
        created_at=audit["created_at"],
    )


@router.get("/jobs/{key}", response_model=JobStatusOut)
def get_job_status(key: str):
    """Return current job status and a live markdown progress summary."""
    try:
        audit_id = int(key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job key — must be a numeric id")

    audit = repo.get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail=f"Job '{key}' not found")

    job_status = _TERMINAL_MAP.get(audit["status"], "processing")

    pages = repo.list_pages(audit_id)
    findings = repo.list_findings(audit_id)
    tickets = repo.list_tickets(audit_id)
    logs = repo.list_memory(audit_id, agent="manager", kind="progress_log")

    summary_md = _build_summary_md(audit, pages, findings, tickets, logs)

    return JobStatusOut(
        job_key=key,
        url=audit["url"],
        status=job_status,
        progress_message=audit.get("progress_message"),
        error_message=audit.get("error_message"),
        summary_md=summary_md,
        created_at=audit["created_at"],
        completed_at=audit.get("completed_at"),
    )


def _build_summary_md(audit: dict, pages: list, findings: list, tickets: list, logs: list) -> str:
    url = audit.get("url", "")
    raw_status = audit.get("status", "queued")
    display_status = raw_status.replace("_", " ").title()
    created = (audit.get("created_at") or "")[:19].replace("T", " ")
    completed = (audit.get("completed_at") or "")[:19].replace("T", " ")
    progress = audit.get("progress_message") or ""

    lines: list[str] = [
        "# Audit Progress Report",
        "",
        f"**URL:** `{url}`  ",
        f"**Job Status:** {display_status}  ",
        f"**Started:** {created} UTC",
    ]

    if completed:
        lines.append(f"**Completed:** {completed} UTC")

    lines.append("")

    if progress:
        lines += [f"> {progress}", ""]

    # Planned tasks
    if tickets:
        lines += [f"## Planned Tasks ({len(tickets)})", ""]
        for t in tickets:
            done = t.get("status") in ("done", "completed")
            icon = "✓" if done else "○"
            priority = t.get("priority", "normal")
            lines.append(f"- {icon} **[{priority}]** {t['title']}")
            if t.get("detail"):
                lines.append(f"  _{t['detail'][:120]}_")
        lines.append("")

    # Crawl results
    if pages:
        lines += [f"## Crawled Pages ({len(pages)})", ""]
        for p in pages:
            title = p.get("page_title") or p.get("page_url", "")
            lines.append(f"- [{title}]({p['page_url']})")
        lines.append("")
    elif raw_status not in ("queued", "planning"):
        lines += ["## Crawled Pages", "", "_Crawl not yet started._", ""]

    # Findings summary
    if findings:
        severity_counts: dict[str, int] = {}
        for f in findings:
            sev = f.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        lines += [f"## Findings ({len(findings)} total)", ""]
        for sev in ("high", "medium", "low"):
            if severity_counts.get(sev):
                lines.append(f"- **{sev.title()}:** {severity_counts[sev]}")
        lines.append("")

        lines.append("### Top Findings")
        lines.append("")
        for f in findings[:8]:
            dp = f.get("dp_type", "").replace("_", " ")
            sev = f.get("severity", "")
            lines.append(f"- **{f['title']}** — _{dp}_ ({sev})")
        if len(findings) > 8:
            lines.append(f"- _…and {len(findings) - 8} more_")
        lines.append("")
    else:
        lines += [f"## Findings (0)", "", "_No findings detected yet._", ""]

    # Manager activity log
    if logs:
        lines += ["## Manager Activity Log", ""]
        for entry in logs:
            payload = entry.get("payload", {})
            msg = payload.get("message", "")
            action = payload.get("action", "")
            iter_n = payload.get("iteration", "?")
            icon = _ACTION_ICON.get(action, "▸")
            lines.append(f"- {icon} **[iter {iter_n}]** {msg}")
        lines.append("")

    # Error block
    if audit.get("error_message"):
        lines += [
            "## Error",
            "",
            "```",
            audit["error_message"],
            "```",
            "",
        ]

    return "\n".join(lines)
