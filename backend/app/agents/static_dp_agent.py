"""Static dark pattern detection agent.

Receives a page screenshot + HTML, calls the CV inference server
for detection, then calls the VLM for human-readable explanations.
Returns structured findings to the supervisor.
"""

import logging

import httpx

from app.agents.state import AuditState, DetectedFinding
from app.core.config import settings

logger = logging.getLogger(__name__)

# Map YOLO class names to taxonomy
CLASS_TO_CATEGORY = {
    "countdown_timer": ("urgency", "countdown_timer"),
    "limited_time_message": ("urgency", "limited_time_message"),
    "fake_scarcity": ("scarcity", "low_stock_message"),
    "low_stock_message": ("scarcity", "low_stock_message"),
    "high_demand_message": ("scarcity", "high_demand_message"),
    "confirmshaming": ("misdirection", "confirmshaming"),
    "visual_interference": ("misdirection", "visual_interference"),
    "trick_question": ("misdirection", "trick_question"),
    "preselection": ("forced_action", "preselection"),
    "forced_enrollment": ("forced_action", "forced_enrollment"),
    "disguised_ad": ("misdirection", "visual_interference"),
    "hidden_cost": ("sneaking", "hidden_costs"),
    "fake_social_proof": ("social_proof", "fake_activity"),
    "fake_activity": ("social_proof", "fake_activity"),
    "fake_testimonial": ("social_proof", "fake_testimonial"),
    "hard_to_cancel": ("obstruction", "hard_to_cancel"),
}


async def static_dp_node(state: AuditState) -> dict:
    """Analyze the current page for static dark patterns via CV + VLM."""
    page = state.current_page
    if not page or not page.screenshot_path:
        return {}

    findings: list[DetectedFinding] = []

    try:
        # 1. Call YOLO detection
        detections = await _call_detection(page.screenshot_path)

        # 2. For each detection, call VLM for explanation
        for det in detections:
            explanation = await _call_explanation(
                page.screenshot_path, det["class"], det["bbox"]
            )
            cat, dp_type = CLASS_TO_CATEGORY.get(
                det["class"], ("misdirection", "visual_interference")
            )
            findings.append(
                DetectedFinding(
                    category=cat,
                    dp_type=dp_type,
                    severity=_infer_severity(det["confidence"]),
                    title=f"{det['class'].replace('_', ' ').title()} detected",
                    description=f"Detected on page: {page.url}",
                    explanation=explanation,
                    evidence_screenshot_path=page.screenshot_path,
                    bounding_box=det["bbox"],
                    confidence_score=det["confidence"],
                    is_dynamic=False,
                    page_url=page.url,
                )
            )
    except Exception as e:
        logger.error("Static DP analysis failed for %s: %s", page.url, e)

    return {"findings": state.findings + findings}


async def _call_detection(screenshot_path: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=60) as client:
        with open(screenshot_path, "rb") as f:
            resp = await client.post(
                f"{settings.ml_inference_url}/detect",
                files={"file": ("screenshot.png", f, "image/png")},
            )
        resp.raise_for_status()
        return resp.json().get("detections", [])


async def _call_explanation(
    screenshot_path: str, dp_class: str, bbox: dict
) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(screenshot_path, "rb") as f:
                resp = await client.post(
                    f"{settings.ml_inference_url}/explain",
                    files={"file": ("screenshot.png", f, "image/png")},
                    data={"dp_class": dp_class},
                )
            resp.raise_for_status()
            return resp.json().get("explanation")
    except Exception as e:
        logger.warning("VLM explanation failed: %s", e)
        return None


def _infer_severity(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"
