"""Playwright-based website crawler.

Crawls a website starting from a given URL, captures screenshots,
extracts HTML/text, and discovers internal links for multi-page crawling.
"""

import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from app.agents.state import PageContext
from app.core.config import settings

logger = logging.getLogger(__name__)


class Crawler:
    def __init__(
        self,
        max_depth: int = settings.crawl_max_depth,
        max_pages: int = settings.crawl_max_pages,
        timeout_ms: int = settings.crawl_timeout_ms,
        storage_dir: str = settings.storage_dir,
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout_ms = timeout_ms
        self.storage_dir = Path(storage_dir)

    async def crawl(self, start_url: str, audit_id: int) -> list[PageContext]:
        """Crawl a website and return page contexts with screenshots."""
        visited: set[str] = set()
        pages: list[PageContext] = []
        queue: list[tuple[str, int]] = [(start_url, 0)]

        audit_dir = self.storage_dir / str(audit_id)
        audit_dir.mkdir(parents=True, exist_ok=True)

        base_domain = urlparse(start_url).netloc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="PatternProof/1.0 (Dark Pattern Auditor)",
            )
            page = await context.new_page()

            while queue and len(pages) < self.max_pages:
                url, depth = queue.pop(0)
                normalized = self._normalize_url(url)

                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    page_ctx = await self._crawl_page(
                        page, url, audit_id, len(pages), audit_dir
                    )
                    pages.append(page_ctx)

                    # Discover links for further crawling
                    if depth < self.max_depth:
                        links = await self._extract_links(page, base_domain)
                        for link in links:
                            if self._normalize_url(link) not in visited:
                                queue.append((link, depth + 1))

                except Exception as e:
                    logger.error("Failed to crawl %s: %s", url, e)

            await browser.close()

        logger.info("Crawled %d pages for audit %d", len(pages), audit_id)
        return pages

    async def _crawl_page(
        self, page, url: str, audit_id: int, page_idx: int, audit_dir: Path
    ) -> PageContext:
        """Navigate to a page and capture screenshot + HTML."""
        await page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
        await page.wait_for_timeout(1000)  # extra settle time

        # Screenshot
        screenshot_path = audit_dir / f"page_{page_idx}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)

        # HTML snapshot
        html_path = audit_dir / f"page_{page_idx}.html"
        html = await page.content()
        html_path.write_text(html, encoding="utf-8")

        # Visible text
        visible_text = await page.evaluate("() => document.body.innerText")
        title = await page.title()

        return PageContext(
            url=url,
            title=title,
            screenshot_path=str(screenshot_path),
            html_path=str(html_path),
            visible_text=visible_text[:10000] if visible_text else None,
        )

    async def _extract_links(self, page, base_domain: str) -> list[str]:
        """Extract same-domain links from the current page."""
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(href => href.startsWith('http'));
        }""")

        same_domain = []
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == base_domain:
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean not in same_domain:
                    same_domain.append(clean)

        return same_domain[:50]  # cap discovery

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
