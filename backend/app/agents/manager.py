"""Manager (supervisor) agent — orchestrates the audit pipeline.

Deterministic routing with a Claude-backed feedback loop: when pages failed to
analyze, Claude decides whether a re-analysis pass is worthwhile (bounded by
``agent_max_feedback_retries``).

Routes one of: plan | crawl | static_analysis | report | complete.
"""

from app.agents.state import AuditState
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db import repo
from app.models.taxonomy import AuditStatus
from app.services import llm

logger = get_logger(__name__)

FEEDBACK_SYSTEM = """You supervise a dark-pattern audit. Some pages failed automated analysis.
Decide whether one more analysis pass is worthwhile given the retry budget.
Return ONLY JSON: {"retry": true|false, "reason": "..."}"""


def manager_node(state: AuditState) -> dict:
    logger.info(
        "Audit %s: manager iteration=%d tickets=%d visited=%d pending=%d",
        state.audit_id, state.iteration_count,
        len(state.tickets), len(state.visited_pages), len(state.pending_pages),
    )

    if state.iteration_count >= state.max_iterations:
        logger.warning(
            "Audit %s: hit max_iterations=%d — forcing report", state.audit_id, state.max_iterations
        )
        _log_progress(state.audit_id, state.iteration_count, "report", f"Reached iteration limit ({state.max_iterations}) — forcing report generation")
        return {"next_action": "report", "iteration_count": state.iteration_count + 1}

    base = {"iteration_count": state.iteration_count + 1, "next_action": "manager"}

    # 1. Plan first.
    if not state.tickets:
        logger.info("Audit %s: manager → plan (no tickets yet)", state.audit_id)
        _log_progress(state.audit_id, state.iteration_count, "plan", "Starting audit planning — determining inspection scope")
        return {**base, "next_action": "plan"}

    # 2. Crawl if nothing has been fetched yet.
    if not state.visited_pages and not state.pending_pages:
        logger.info("Audit %s: manager → crawl (no pages fetched yet)", state.audit_id)
        _log_progress(state.audit_id, state.iteration_count, "crawl", f"Plan ready ({len(state.tickets)} task(s)) — initiating page crawl")
        return {**base, "next_action": "crawl"}

    # 3. Analyze any pending pages.
    if state.pending_pages:
        logger.info(
            "Audit %s: manager → static_analysis (%d pages pending)",
            state.audit_id, len(state.pending_pages),
        )
        _log_progress(state.audit_id, state.iteration_count, "static_analysis", f"Crawl complete — analyzing {len(state.pending_pages)} page(s) for dark patterns")
        repo.update_audit_status(
            state.audit_id, AuditStatus.ANALYZING, progress_message="Analyzing pages for dark patterns…"
        )
        return {**base, "next_action": "static_analysis"}

    # 4. All crawled pages have been processed — consider a feedback pass.
    failed = [p for p in state.visited_pages if not p.analysis_ok]
    if failed and state.feedback_count < settings.agent_max_feedback_retries:
        logger.info(
            "Audit %s: manager — %d/%d pages failed analysis, feedback_count=%d/%d",
            state.audit_id, len(failed), len(state.visited_pages),
            state.feedback_count, settings.agent_max_feedback_retries,
        )
        if _should_retry(state, len(failed)):
            logger.info("Audit %s: manager → static_analysis (feedback pass %d)", state.audit_id, state.feedback_count + 1)
            _log_progress(state.audit_id, state.iteration_count, "static_analysis", f"Re-analyzing {len(failed)} failed page(s) (retry pass {state.feedback_count + 1})")
            for p in failed:
                p.analysis_ok = True
            return {
                **base,
                "next_action": "static_analysis",
                "pending_pages": failed,
                "visited_pages": [p for p in state.visited_pages if p.analysis_ok or p in failed],
                "feedback_count": state.feedback_count + 1,
                "agent_notes": state.agent_notes + [f"Feedback pass for {len(failed)} page(s)."],
            }

    # 5. Done — generate the report.
    logger.info(
        "Audit %s: manager → report (all done — visited=%d findings=%d)",
        state.audit_id, len(state.visited_pages), len(state.findings),
    )
    _log_progress(state.audit_id, state.iteration_count, "report", f"Analysis complete — {len(state.visited_pages)} page(s), {len(state.findings)} finding(s) — generating report")
    return {**base, "next_action": "report"}


def _log_progress(audit_id: int, iteration: int, action: str, message: str) -> None:
    try:
        repo.add_memory(
            audit_id,
            agent="manager",
            kind="progress_log",
            payload={"iteration": iteration, "action": action, "message": message},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: failed to persist progress log — %s", audit_id, e)


def _should_retry(state: AuditState, n_failed: int) -> bool:
    user = (
        f"Pages failed: {n_failed} of {len(state.visited_pages)}. "
        f"Retry budget used: {state.feedback_count}/{settings.agent_max_feedback_retries}."
    )
    try:
        data = llm.claude_json(FEEDBACK_SYSTEM, user, max_tokens=200)
        decision = bool(isinstance(data, dict) and data.get("retry"))
        logger.info(
            "Audit %s: manager feedback decision = %s (reason: %s)",
            state.audit_id, decision, (data or {}).get("reason", "—"),
        )
        return decision
    except Exception as e:  # noqa: BLE001
        logger.warning("Audit %s: manager feedback decision failed (%s); retrying once", state.audit_id, e)
        return state.feedback_count == 0
