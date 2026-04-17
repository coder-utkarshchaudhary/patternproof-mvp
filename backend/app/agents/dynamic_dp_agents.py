"""Dynamic dark pattern detection agents.

These detect dark patterns that span multiple pages:
- Hidden costs in checkout flows
- Bait-and-switch across pages
- Forced continuity / subscription traps
- Obstruction (hard to cancel)

Each is a LangGraph node that operates on the shared AuditState.
"""

import logging

from langchain_community.llms import Ollama

from app.agents.state import AuditState, DetectedFinding
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Flow Navigator ──────────────────────────────────────────────────────

FLOW_NAVIGATOR_PROMPT = """You are analyzing a website for dynamic dark patterns.
You need to identify multi-page user flows to test (checkout, signup, cancellation).

Pages visited so far:
{pages}

Visible text on current page:
{text}

What flow should be tested next? Respond with one of:
- "checkout" — if there are products/pricing to test
- "signup" — if there are registration/signup forms
- "cancel" — if there are subscription/account management pages  
- "none" — no more flows to test

Respond with ONLY the flow type."""


async def flow_navigator_node(state: AuditState) -> dict:
    """Determine which multi-page flow to test for dynamic dark patterns."""
    llm = Ollama(
        base_url=settings.ollama_base_url,
        model=settings.agent_model,
        temperature=0,
    )

    pages_summary = "\n".join(
        f"- {p.url} ({p.title or 'untitled'})" for p in state.visited_pages
    )
    current_text = (state.current_page.visible_text or "")[:2000] if state.current_page else ""

    try:
        response = llm.invoke(
            FLOW_NAVIGATOR_PROMPT.format(pages=pages_summary, text=current_text)
        ).strip().lower()
        flow = response if response in ("checkout", "signup", "cancel") else None
    except Exception as e:
        logger.error("Flow navigator failed: %s", e)
        flow = None

    return {"flow_type": flow}


# ── Context Tracker ─────────────────────────────────────────────────────

CONTEXT_TRACKER_PROMPT = """You are analyzing a multi-page flow for hidden costs and bait-and-switch patterns.

Flow type: {flow_type}

Interaction history (previous pages in this flow):
{history}

Current page text:
{text}

Look for:
1. Prices that changed from previous pages
2. New fees or charges not previously mentioned
3. Terms that differ from what was initially shown
4. Options that were pre-selected without user consent

If you find any dark patterns, describe each one in this format:
FINDING: [type] | [severity: low/medium/high] | [description]

If no dark patterns found, respond: NONE"""


async def context_tracker_node(state: AuditState) -> dict:
    """Track context across pages to detect sneaking patterns."""
    if not state.flow_type or not state.current_page:
        return {}

    llm = Ollama(
        base_url=settings.ollama_base_url,
        model=settings.agent_model,
        temperature=0,
    )

    history = "\n".join(
        f"Step {i+1}: {h.get('action', 'visit')} → {h.get('url', 'unknown')}"
        for i, h in enumerate(state.interaction_history)
    )
    current_text = (state.current_page.visible_text or "")[:3000]

    try:
        response = llm.invoke(
            CONTEXT_TRACKER_PROMPT.format(
                flow_type=state.flow_type,
                history=history or "No previous steps",
                text=current_text,
            )
        )
    except Exception as e:
        logger.error("Context tracker failed: %s", e)
        return {}

    findings = _parse_findings(response, state.current_page.url)
    return {"findings": state.findings + findings} if findings else {}


# ── Obstruction Detector ────────────────────────────────────────────────

OBSTRUCTION_PROMPT = """You are analyzing a cancellation/deletion flow for obstruction dark patterns.

Flow type: {flow_type}
Steps taken so far: {step_count}
Interaction history:
{history}

Current page text:
{text}

Look for:
1. Excessive steps required to cancel/delete
2. Emotional manipulation (confirmshaming, guilt-tripping)
3. Hidden cancel buttons or links
4. Offers/discounts designed to prevent cancellation
5. Confusing language or trick questions

If you find any dark patterns, describe each one in this format:
FINDING: [type] | [severity: low/medium/high] | [description]

If no dark patterns found, respond: NONE"""


async def obstruction_detector_node(state: AuditState) -> dict:
    """Detect obstruction patterns in cancellation/deletion flows."""
    if state.flow_type != "cancel" or not state.current_page:
        return {}

    llm = Ollama(
        base_url=settings.ollama_base_url,
        model=settings.agent_model,
        temperature=0,
    )

    history = "\n".join(
        f"Step {i+1}: {h.get('action', 'visit')} → {h.get('url', 'unknown')}"
        for i, h in enumerate(state.interaction_history)
    )

    try:
        response = llm.invoke(
            OBSTRUCTION_PROMPT.format(
                flow_type=state.flow_type,
                step_count=len(state.interaction_history),
                history=history or "No previous steps",
                text=(state.current_page.visible_text or "")[:3000],
            )
        )
    except Exception as e:
        logger.error("Obstruction detector failed: %s", e)
        return {}

    findings = _parse_findings(response, state.current_page.url, is_dynamic=True)
    return {"findings": state.findings + findings} if findings else {}


def _parse_findings(
    response: str, page_url: str | None = None, is_dynamic: bool = True
) -> list[DetectedFinding]:
    """Parse FINDING: lines from LLM response."""
    findings = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line.upper().startswith("FINDING:"):
            continue
        parts = line[8:].split("|")
        if len(parts) < 3:
            continue
        dp_type_raw = parts[0].strip().lower().replace(" ", "_")
        severity = parts[1].strip().lower()
        description = parts[2].strip()

        if severity not in ("low", "medium", "high"):
            severity = "medium"

        findings.append(
            DetectedFinding(
                category="sneaking" if "cost" in dp_type_raw or "fee" in dp_type_raw
                else "obstruction" if "cancel" in dp_type_raw
                else "misdirection",
                dp_type=dp_type_raw[:50],
                severity=severity,
                title=dp_type_raw.replace("_", " ").title(),
                description=description,
                is_dynamic=is_dynamic,
                page_url=page_url,
            )
        )
    return findings
