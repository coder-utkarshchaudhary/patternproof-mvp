"""Exa web search — pull regulatory / remediation references for the report.

Given the set of CCPA dark-pattern types found in an audit, fetch a few
authoritative references (DPDP / CCPA guidance, remediation best-practice) to
cite in the PDF report.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    from exa_py import Exa

    return Exa(api_key=settings.exa_api_key)


def references_for(ccpa_patterns: list[str], *, per_pattern: int = 1, cap: int = 6) -> list[dict]:
    """Return a deduped list of {title, url, snippet} reference dicts."""
    if not settings.exa_api_key or not ccpa_patterns:
        return []

    seen: set[str] = set()
    refs: list[dict] = []
    for pattern in dict.fromkeys(ccpa_patterns):  # preserve order, dedupe
        label = pattern.replace("_", " ")
        query = (
            f"India CCPA 2023 dark pattern guidelines DPDP Act: {label} "
            f"definition and how to fix"
        )
        try:
            res = _client().search_and_contents(
                query, num_results=per_pattern, type="auto", text={"max_characters": 400}
            )
        except Exception as e:  # noqa: BLE001 - references are best-effort
            logger.warning("Exa search failed for %s: %s", pattern, e)
            continue

        for r in getattr(res, "results", []) or []:
            url = getattr(r, "url", None)
            if not url or url in seen:
                continue
            seen.add(url)
            refs.append(
                {
                    "title": getattr(r, "title", None) or label.title(),
                    "url": url,
                    "snippet": (getattr(r, "text", "") or "")[:300] or None,
                }
            )
            if len(refs) >= cap:
                return refs
    return refs
