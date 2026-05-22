"""Crawler slave agent — LangGraph node wrapping the Apify crawler.

Fetches pages, persists HTML + screenshots to Supabase Storage, records each
page in ``audit_pages`` and the raw crawl payload in ``agent_memory``, and
loads the resulting ``PageContext`` list into state for the static detector.
"""

import logging
import time

from app.agents.state import AuditState, PageContext
from app.db import repo
from app.models.taxonomy import AuditStatus
from app.services import apify_client, storage
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def crawler_node(state: AuditState) -> dict:
    logger.info("Audit %s: crawler starting — url=%s", state.audit_id, state.target_url)
    t0 = time.monotonic()

    repo.update_audit_status(
        state.audit_id, AuditStatus.CRAWLING, progress_message="Crawling website…"
    )

    raw_pages = apify_client.crawl(state.target_url)
    logger.info("Audit %s: Apify returned %d raw pages", state.audit_id, len(raw_pages))

    pages: list[PageContext] = []
    for idx, p in enumerate(raw_pages):
        page_url = p.get("url", "?")
        logger.info("Audit %s: persisting page %d/%d — %s", state.audit_id, idx + 1, len(raw_pages), page_url)

        screenshot_path = None
        if p.get("screenshot_bytes"):
            try:
                screenshot_path = storage.upload_screenshot(
                    state.audit_id, f"page_{idx}.png", p["screenshot_bytes"]
                )
                logger.debug("Audit %s: screenshot uploaded → %s", state.audit_id, screenshot_path)
            except Exception as e:  # noqa: BLE001
                logger.warning("Audit %s: screenshot upload failed for page %d — %s", state.audit_id, idx, e)

        html_path = None
        if p.get("html"):
            try:
                html_path = storage.upload_html(state.audit_id, f"page_{idx}.html", p["html"])
                logger.debug("Audit %s: HTML uploaded → %s", state.audit_id, html_path)
            except Exception as e:  # noqa: BLE001
                logger.warning("Audit %s: HTML upload failed for page %d — %s", state.audit_id, idx, e)

        row = repo.insert_page(
            state.audit_id,
            {
                "page_url": page_url,
                "page_title": p.get("title"),
                "screenshot_path": screenshot_path,
                "html_snapshot_path": html_path,
                "crawl_depth": p.get("depth", 0),
            },
        )
        repo.add_memory(
            state.audit_id,
            agent="crawler",
            kind="raw",
            payload={
                "page_id": row["id"],
                "url": page_url,
                "title": p.get("title"),
                "text": (p.get("text") or "")[:20000],
                "html_path": html_path,
                "screenshot_path": screenshot_path,
            },
        )
        pages.append(
            PageContext(
                page_id=row["id"],
                url=page_url,
                title=p.get("title"),
                screenshot_path=screenshot_path,
                html_path=html_path,
                visible_text=(p.get("text") or "")[:20000] or None,
                depth=p.get("depth", 0),
            )
        )

    elapsed = time.monotonic() - t0
    logger.info(
        "Audit %s: crawler done in %.1fs — %d pages persisted (screenshots=%d html=%d)",
        state.audit_id, elapsed, len(pages),
        sum(1 for p in pages if p.screenshot_path),
        sum(1 for p in pages if p.html_path),
    )
    return {
        "pending_pages": pages,
        "agent_notes": state.agent_notes + [f"Crawled {len(pages)} page(s)."],
        "next_action": "manager",
    }
