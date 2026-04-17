"""Page interaction engine for simulating user flows.

Drives Playwright to simulate checkout, signup, and cancellation flows
while recording interaction sequences for dynamic dark pattern detection.
"""

import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class PageInteractor:
    """Simulate user interactions on a webpage."""

    async def dismiss_popups(self, page: Page) -> None:
        """Try to dismiss common popups: cookie banners, modals, overlays."""
        dismiss_selectors = [
            # Cookie consent
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('Got it')",
            "button:has-text('I agree')",
            "[id*='cookie'] button",
            "[class*='cookie'] button",
            "[class*='consent'] button",
            # Generic modals
            "button[aria-label='Close']",
            "button:has-text('Close')",
            "button:has-text('✕')",
            "button:has-text('×')",
        ]

        for selector in dismiss_selectors:
            try:
                el = page.locator(selector).first
                if await el.is_visible(timeout=500):
                    await el.click(timeout=1000)
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    async def find_flow_entry_points(self, page: Page) -> dict[str, list[str]]:
        """Identify entry points for common user flows on the page."""
        flows: dict[str, list[str]] = {
            "checkout": [],
            "signup": [],
            "cancel": [],
        }

        checkout_keywords = [
            "add to cart", "buy now", "purchase", "checkout", "order",
            "subscribe", "start trial", "get started", "pricing",
        ]
        signup_keywords = [
            "sign up", "register", "create account", "join",
        ]
        cancel_keywords = [
            "cancel", "unsubscribe", "delete account", "close account",
        ]

        buttons = await page.query_selector_all("a, button, [role='button']")
        for btn in buttons:
            text = (await btn.text_content() or "").strip().lower()
            for kw in checkout_keywords:
                if kw in text:
                    flows["checkout"].append(text)
                    break
            for kw in signup_keywords:
                if kw in text:
                    flows["signup"].append(text)
                    break
            for kw in cancel_keywords:
                if kw in text:
                    flows["cancel"].append(text)
                    break

        return flows

    async def record_interaction(
        self, page: Page, action: str, selector: str | None = None
    ) -> dict:
        """Perform an action and record the before/after state."""
        before_url = page.url
        before_title = await page.title()

        if action == "click" and selector:
            await page.click(selector, timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)

        after_url = page.url
        after_title = await page.title()

        return {
            "action": action,
            "selector": selector,
            "before_url": before_url,
            "before_title": before_title,
            "after_url": after_url,
            "after_title": after_title,
            "url_changed": before_url != after_url,
        }
