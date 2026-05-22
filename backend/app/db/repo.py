"""Supabase data-access helpers.

Plain synchronous functions over the service-role client. FastAPI endpoints
that call these are declared as ``def`` (not ``async def``) so Starlette runs
them in a threadpool and the event loop is never blocked. The Celery worker
calls them directly.
"""

from __future__ import annotations

from typing import Any

from app.core.supabase import get_client
from app.models.taxonomy import AuditStatus


# ── Audits ──────────────────────────────────────────────────────────────────

def create_audit(url: str) -> dict[str, Any]:
    res = (
        get_client()
        .table("audits")
        .insert({"url": url, "status": AuditStatus.QUEUED.value})
        .execute()
    )
    return res.data[0]


def get_audit(audit_id: int) -> dict[str, Any] | None:
    res = get_client().table("audits").select("*").eq("id", audit_id).limit(1).execute()
    return res.data[0] if res.data else None


def list_audits(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("audits")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data or []


def update_audit_status(
    audit_id: int,
    status: AuditStatus | str,
    *,
    progress_message: str | None = None,
    error_message: str | None = None,
    completed_at: str | None = None,
) -> None:
    patch: dict[str, Any] = {"status": status.value if isinstance(status, AuditStatus) else status}
    if progress_message is not None:
        patch["progress_message"] = progress_message
    if error_message is not None:
        patch["error_message"] = error_message
    if completed_at is not None:
        patch["completed_at"] = completed_at
    get_client().table("audits").update(patch).eq("id", audit_id).execute()


# ── Pages ─────────────────────────────────────────────────────────────────────

def insert_page(audit_id: int, page: dict[str, Any]) -> dict[str, Any]:
    row = {"audit_id": audit_id, **page}
    res = get_client().table("audit_pages").insert(row).execute()
    return res.data[0]


def list_pages(audit_id: int) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("audit_pages")
        .select("*")
        .eq("audit_id", audit_id)
        .order("id")
        .execute()
    )
    return res.data or []


# ── Findings ──────────────────────────────────────────────────────────────────

def insert_findings(audit_id: int, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not findings:
        return []
    rows = [{"audit_id": audit_id, **f} for f in findings]
    res = get_client().table("findings").insert(rows).execute()
    return res.data or []


def list_findings(audit_id: int) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("findings")
        .select("*")
        .eq("audit_id", audit_id)
        .order("id")
        .execute()
    )
    return res.data or []


# ── Reports ─────────────────────────────────────────────────────────────────────

def upsert_report(audit_id: int, report: dict[str, Any]) -> dict[str, Any]:
    row = {"audit_id": audit_id, **report}
    res = (
        get_client()
        .table("reports")
        .upsert(row, on_conflict="audit_id")
        .execute()
    )
    return res.data[0]


def get_report(audit_id: int) -> dict[str, Any] | None:
    res = get_client().table("reports").select("*").eq("audit_id", audit_id).limit(1).execute()
    return res.data[0] if res.data else None


# ── Tickets ──────────────────────────────────────────────────────────────────

def create_tickets(audit_id: int, tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tickets:
        return []
    rows = [{"audit_id": audit_id, **t} for t in tickets]
    res = get_client().table("tickets").insert(rows).execute()
    return res.data or []


def update_ticket_status(
    ticket_id: int,
    status: str,
    *,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> None:
    patch: dict[str, Any] = {"status": status}
    if started_at is not None:
        patch["started_at"] = started_at
    if completed_at is not None:
        patch["completed_at"] = completed_at
    get_client().table("tickets").update(patch).eq("id", ticket_id).execute()


def list_tickets(audit_id: int) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("tickets")
        .select("*")
        .eq("audit_id", audit_id)
        .order("id")
        .execute()
    )
    return res.data or []


def archive_tickets(audit_id: int, *, final_status: str, result: dict[str, Any] | None = None) -> None:
    """Move all tickets for an audit into ticket_archive, then delete them."""
    tickets = list_tickets(audit_id)
    if not tickets:
        return
    archive_rows = [
        {
            "original_id": t["id"],
            "audit_id": t["audit_id"],
            "title": t["title"],
            "detail": t.get("detail"),
            "priority": t.get("priority", "normal"),
            "ticket_type": t.get("ticket_type", "planner"),
            "assigned_to": t.get("assigned_to"),
            "final_status": final_status,
            "result": result or {},
            "created_at": t["created_at"],
            "completed_at": t.get("completed_at"),
        }
        for t in tickets
    ]
    get_client().table("ticket_archive").insert(archive_rows).execute()
    ids = [t["id"] for t in tickets]
    get_client().table("tickets").delete().in_("id", ids).execute()


# ── Agent memory (JSONB document store) ──────────────────────────────────────────

def add_memory(audit_id: int, agent: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("agent_memory")
        .insert({"audit_id": audit_id, "agent": agent, "kind": kind, "payload": payload})
        .execute()
    )
    return res.data[0]


def list_memory(
    audit_id: int, *, agent: str | None = None, kind: str | None = None
) -> list[dict[str, Any]]:
    q = get_client().table("agent_memory").select("*").eq("audit_id", audit_id)
    if agent:
        q = q.eq("agent", agent)
    if kind:
        q = q.eq("kind", kind)
    return q.order("id").execute().data or []
