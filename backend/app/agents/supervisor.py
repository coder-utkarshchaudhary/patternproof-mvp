"""Supervisor (manager) agent — orchestrates the audit pipeline.

Routes tasks to worker agents based on the current state:
- Static DP analysis for each crawled page
- Dynamic DP analysis for multi-page flows (checkout, signup, cancel)
- Decides when the audit is complete
"""

import logging

from langchain_community.llms import Ollama

from app.agents.state import AuditState
from app.core.config import settings

logger = logging.getLogger(__name__)

SUPERVISOR_PROMPT = """You are the supervisor of a dark pattern audit system.

You are auditing the website: {target_url}

Current state:
- Pages visited: {visited_count}
- Pages in queue: {queue_count}
- Findings so far: {findings_count}
- Current flow: {flow_type}
- Iteration: {iteration}/{max_iterations}

Your job is to decide the next action. Choose one of:
- "crawl_next" — Crawl the next page in the queue
- "static_analysis" — Run static dark pattern detection on the current page
- "dynamic_flow" — Start or continue a dynamic flow analysis (checkout, signup, cancel)
- "complete" — The audit is done, generate the final report

Respond with ONLY the action name, nothing else."""


def create_supervisor_llm():
    return Ollama(
        base_url=settings.ollama_base_url,
        model=settings.agent_model,
        temperature=0,
    )


async def supervisor_node(state: AuditState) -> dict:
    """Supervisor decision node — determines next action."""
    if state.iteration_count >= state.max_iterations:
        logger.warning("Max iterations reached for audit %d", state.audit_id)
        return {"next_action": "complete", "is_complete": True}

    if not state.visited_pages and state.crawl_queue:
        return {
            "next_action": "crawl_next",
            "iteration_count": state.iteration_count + 1,
        }

    llm = create_supervisor_llm()
    prompt = SUPERVISOR_PROMPT.format(
        target_url=state.target_url,
        visited_count=len(state.visited_pages),
        queue_count=len(state.crawl_queue),
        findings_count=len(state.findings),
        flow_type=state.flow_type or "none",
        iteration=state.iteration_count,
        max_iterations=state.max_iterations,
    )

    try:
        response = llm.invoke(prompt).strip().lower()
        action = response if response in (
            "crawl_next", "static_analysis", "dynamic_flow", "complete"
        ) else "complete"
    except Exception as e:
        logger.error("Supervisor LLM failed: %s", e)
        action = "complete" if state.visited_pages else "crawl_next"

    is_complete = action == "complete"
    return {
        "next_action": action,
        "iteration_count": state.iteration_count + 1,
        "is_complete": is_complete,
    }
