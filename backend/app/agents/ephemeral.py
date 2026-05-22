"""Ephemeral per-page sub-agents spawned by the StaticDarkPatternDetector.

- ``visual_subagent``  — YOLO detection (ML service) + Claude-vision explanation.
- ``semantic_subagent`` — cheap LLM parses cleaned HTML/text into taxonomy-tagged
  findings.

Both return ``DetectedFinding`` lists; the detector node merges and dedupes them.
"""

from __future__ import annotations

import io
import logging

import httpx
from bs4 import BeautifulSoup
from PIL import Image

from app.agents.state import DetectedFinding, PageContext
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.taxonomy import DPType, category_for, ccpa_for
from app.services import llm, storage

logger = get_logger(__name__)

VALID_TYPES = {t.value for t in DPType}

VISION_SYSTEM = """You are a dark-pattern expert analyzing a cropped UI region from a webpage.
A computer-vision model flagged it as a possible "{dp_class}" dark pattern.
In 2-4 sentences explain: what the element is, why it is a deceptive (dark) pattern, and how it \
manipulates users. Be factual; do not speculate beyond what is visible."""

SEMANTIC_SYSTEM = """You are a dark-pattern auditor checking a single web page for compliance with \
India's CCPA 2023 dark-pattern guidelines and the DPDP Act.

From the page text/HTML, identify STATIC dark patterns only (visible on one page; ignore multi-step \
flows). Use these type tags exactly: countdown_timer, limited_time_message, low_stock_message, \
high_demand_message, confirmshaming, visual_interference, trick_question, disguised_ad, nagging, \
preselection, forced_enrollment, fake_activity, fake_testimonial, hidden_costs, drip_pricing, \
basket_sneaking, hidden_subscription, bait_and_switch.

Return ONLY JSON:
{"findings": [{"dp_type": "<tag>", "severity": "low|medium|high", "title": "...", \
"description": "...", "evidence": "<short quote from the page>"}]}
If none are found, return {"findings": []}. Do not invent evidence."""


def _infer_severity(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def visual_subagent(page: PageContext) -> list[DetectedFinding]:
    if not page.screenshot_path:
        return []
    screenshot = storage.download(page.screenshot_path)
    if not screenshot:
        return []

    try:
        resp = httpx.post(
            f"{settings.ml_inference_url}/detect",
            files={"file": ("screenshot.png", screenshot, "image/png")},
            timeout=120,
        )
        resp.raise_for_status()
        detections = resp.json().get("detections", [])
    except httpx.HTTPError as e:
        logger.warning("YOLO /detect failed for %s: %s", page.url, e)
        raise

    findings: list[DetectedFinding] = []
    for det in detections:
        dp_class = det.get("class", "unknown")
        bbox = det.get("bbox") or {}
        confidence = float(det.get("confidence", 0.0))
        explanation = _explain_region(screenshot, dp_class, bbox)
        findings.append(
            DetectedFinding(
                category=category_for(dp_class),
                dp_type=dp_class if dp_class in VALID_TYPES else "visual_interference",
                ccpa_pattern=ccpa_for(dp_class),
                severity=_infer_severity(confidence),
                title=f"{dp_class.replace('_', ' ').title()} (visual)",
                description=f"Detected on {page.url}",
                explanation=explanation,
                evidence_screenshot_path=page.screenshot_path,
                bounding_box=bbox or None,
                confidence_score=confidence,
                page_url=page.url,
                page_id=page.page_id,
                source="visual",
            )
        )
    return findings


def _explain_region(screenshot: bytes, dp_class: str, bbox: dict) -> str | None:
    try:
        img = Image.open(io.BytesIO(screenshot)).convert("RGB")
        if bbox:
            crop = img.crop((int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])))
        else:
            crop = img
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        return llm.claude_vision(
            buf.getvalue(),
            VISION_SYSTEM.format(dp_class=dp_class),
            "Explain this flagged region.",
        )
    except Exception as e:  # noqa: BLE001 - explanation is best-effort
        logger.warning("Vision explanation failed: %s", e)
        return None


def _clean_text(page: PageContext) -> str:
    if page.html_path:
        html = storage.download(page.html_path)
        if html:
            soup = BeautifulSoup(html.decode("utf-8", errors="ignore"), "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            if text:
                return text[:12000]
    return (page.visible_text or "")[:12000]


def semantic_subagent(page: PageContext) -> list[DetectedFinding]:
    text = _clean_text(page)
    if not text:
        return []

    user = f"URL: {page.url}\nTitle: {page.title or ''}\n\nPAGE CONTENT:\n{text}"
    data = llm.cheap_parse_json(SEMANTIC_SYSTEM, user)
    raw = data.get("findings", []) if isinstance(data, dict) else []

    findings: list[DetectedFinding] = []
    for f in raw:
        dp_type = str(f.get("dp_type", "")).strip().lower()
        if dp_type not in VALID_TYPES:
            continue
        severity = str(f.get("severity", "medium")).lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        evidence = f.get("evidence")
        desc = f.get("description", "")
        if evidence:
            desc = f"{desc}\nEvidence: “{evidence}”"
        findings.append(
            DetectedFinding(
                category=category_for(dp_type),
                dp_type=dp_type,
                ccpa_pattern=ccpa_for(dp_type),
                severity=severity,
                title=f.get("title") or dp_type.replace("_", " ").title(),
                description=desc.strip(),
                evidence_screenshot_path=page.screenshot_path,
                page_url=page.url,
                page_id=page.page_id,
                source="semantic",
            )
        )
    return findings
