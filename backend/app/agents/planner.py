"""Planner slave agent — turns an audit request into ordered task tickets.

Uses Claude to decide crawl scope and which page types to prioritize (pricing,
signup, cart, cancellation). Tickets are persisted to both the ``tickets`` table
(for live visibility in Supabase) and the ``agent_memory`` document store.
"""

from app.agents.state import AuditState, Ticket
from app.db import repo
from app.models.taxonomy import AuditStatus
from app.services import llm
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PLANNER_SYSTEM = """You are the Planner in a dark-pattern audit system that certifies websites \
for compliance with India's DPDP Act and the CCPA 2023 dark-pattern guidelines.

Given a target website, produce a short ordered list of task tickets describing what to inspect.
Prioritize pages where dark patterns commonly appear: pricing/checkout, sign-up/registration,
subscription/cancellation, cookie/consent banners, and product pages.

Return ONLY JSON of the form:
{"tickets": [{"title": "...", "detail": "...", "priority": "high|normal|low"}, ...]}
Keep it to at most 6 tickets."""


def planner_node(state: AuditState) -> dict:
    logger.info("Audit %s: Planner starting — target=%s", state.audit_id, state.target_url)
    repo.update_audit_status(
        state.audit_id, AuditStatus.PLANNING, progress_message="Planning audit scope…"
    )

    user = f"Target website: {state.target_url}\nCrawl budget: up to {state.max_iterations} steps."
    try:
        data = llm.claude_json(PLANNER_SYSTEM, user)
        raw = data.get("tickets", []) if isinstance(data, dict) else []
        logger.info("Audit %s: Planner LLM returned %d raw ticket(s)", state.audit_id, len(raw))
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: Planner LLM failed (%s); using default ticket", state.audit_id, e)
        raw = []

    if not raw:
        raw = [{"title": "Full static audit", "detail": "Crawl and inspect all reachable pages.", "priority": "high"}]

    tickets = [
        Ticket(id=i, title=t.get("title", "Inspect"), detail=t.get("detail", ""), priority=t.get("priority", "normal"))
        for i, t in enumerate(raw)
    ]

    # Persist to tickets table (live visibility) and agent_memory (document store).
    ticket_rows = [
        {
            "title": t.title,
            "detail": t.detail,
            "priority": t.priority,
            "ticket_type": "planner",
            "assigned_to": "planner",
            "status": "pending",
        }
        for t in tickets
    ]
    try:
        repo.create_tickets(state.audit_id, ticket_rows)
        logger.info("Audit %s: %d ticket(s) written to tickets table", state.audit_id, len(tickets))
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: failed to persist tickets to tickets table — %s", state.audit_id, e)

    for t in tickets:
        repo.add_memory(state.audit_id, agent="planner", kind="ticket", payload=t.model_dump())

    for t in tickets:
        logger.info(
            "Audit %s: ticket[%s] priority=%s — %s: %s",
            state.audit_id, t.id, t.priority, t.title, t.detail[:80] if t.detail else "",
        )

    return {
        "tickets": tickets,
        "agent_notes": state.agent_notes + [f"Planned {len(tickets)} task(s)."],
        "next_action": "manager",
    }
