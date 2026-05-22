"""Apify-backed website crawler.

Runs an Apify browser crawler actor to fetch pages (HTML, visible text, and —
when the actor supports it — full-page screenshots). Honours robots.txt via the
actor's ``respectRobotsTxtFile`` option and applies exponential backoff around
the actor invocation to avoid hammering the target site.

Returns a list of normalized page dicts:
    {url, title, html, text, screenshot_bytes (optional), depth}
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from apify_client import ApifyClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class CrawlError(RuntimeError):
    pass


def _build_actor_input(start_url: str) -> dict[str, Any]:
    return {
        "startUrls": [{"url": start_url}],
        "maxCrawlPages": settings.crawl_max_pages,
        "maxCrawlDepth": settings.crawl_max_depth,
        # Compliance: obey the site's robots.txt.
        "respectRobotsTxtFile": True,
        # Use a real browser so we get rendered HTML + screenshots.
        "crawlerType": "playwright:chromium",
        "saveHtml": True,
        "saveScreenshots": True,
        "readableTextCharThreshold": 100,
        # Be a polite crawler.
        "maxConcurrency": 3,
        "requestTimeoutSecs": max(10, settings.crawl_timeout_ms // 1000),
        "proxyConfiguration": {"useApifyProxy": True},
    }


@retry(
    retry=retry_if_exception_type((CrawlError, httpx.HTTPError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def _run_actor(client: ApifyClient, start_url: str) -> str:
    """Start the actor and block until it finishes; return the dataset id.

    Wrapped with exponential backoff: transient Apify/network failures are
    retried with growing delays (4s, 8s, 16s ...).
    """
    run = client.actor(settings.apify_actor).call(run_input=_build_actor_input(start_url))
    if not run:
        raise CrawlError("Apify actor returned no run")
    if run.get("status") != "SUCCEEDED":
        raise CrawlError(f"Apify run status: {run.get('status')}")
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise CrawlError("Apify run has no dataset")
    return dataset_id


def _fetch_screenshot(client: ApifyClient, item: dict[str, Any]) -> bytes | None:
    """Best-effort screenshot retrieval from the actor output.

    Browser crawlers expose the screenshot either inline (rare) or as a URL /
    key-value-store reference. We try the common shapes and degrade to None.
    """
    url = item.get("screenshotUrl") or item.get("screenshot")
    if isinstance(url, str) and url.startswith("http"):
        try:
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPError as e:  # noqa: PERF203
            logger.warning("Screenshot fetch failed for %s: %s", item.get("url"), e)
    return None


def crawl(start_url: str) -> list[dict[str, Any]]:
    """Crawl ``start_url`` and return normalized page dicts."""
    if not settings.apify_token:
        raise CrawlError("Apify is not configured: set PP_APIFY_TOKEN")

    client = ApifyClient(settings.apify_token)
    dataset_id = _run_actor(client, start_url)

    pages: list[dict[str, Any]] = []
    for item in client.dataset(dataset_id).iterate_items():
        url = item.get("url") or item.get("loadedUrl")
        if not url:
            continue
        pages.append(
            {
                "url": url,
                "title": item.get("title") or item.get("metadata", {}).get("title"),
                "html": item.get("html") or "",
                "text": item.get("text") or item.get("markdown") or "",
                "screenshot_bytes": _fetch_screenshot(client, item),
                "depth": item.get("depth", 0),
            }
        )

    logger.info("Apify crawl of %s returned %d pages", start_url, len(pages))
    if not pages:
        raise CrawlError(f"Crawl of {start_url} returned no pages")
    return pages
