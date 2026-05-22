"""Supabase Storage helpers — upload crawl artifacts and reports, return paths.

Stored objects are keyed by ``<audit_id>/<name>``. Buckets are private; serve
content to clients via :func:`signed_url`.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.supabase import get_client

logger = logging.getLogger(__name__)

# Default validity for signed URLs (1 week, in seconds).
SIGNED_URL_TTL = 60 * 60 * 24 * 7


def _upload(bucket: str, key: str, data: bytes, content_type: str) -> str:
    """Upload bytes (upsert) and return the object key ``bucket/key``."""
    get_client().storage.from_(bucket).upload(
        path=key,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return f"{bucket}/{key}"


def upload_screenshot(audit_id: int, name: str, data: bytes) -> str:
    return _upload(settings.bucket_screenshots, f"{audit_id}/{name}", data, "image/png")


def upload_html(audit_id: int, name: str, html: str) -> str:
    return _upload(
        settings.bucket_html, f"{audit_id}/{name}", html.encode("utf-8"), "text/html"
    )


def upload_report_pdf(audit_id: int, data: bytes) -> str:
    return _upload(
        settings.bucket_reports, f"{audit_id}/report.pdf", data, "application/pdf"
    )


def signed_url(object_path: str, ttl: int = SIGNED_URL_TTL) -> str | None:
    """Create a signed URL for an object stored as ``bucket/key``."""
    if not object_path or "/" not in object_path:
        return None
    bucket, key = object_path.split("/", 1)
    try:
        res = get_client().storage.from_(bucket).create_signed_url(key, ttl)
        return res.get("signedURL") or res.get("signedUrl")
    except Exception as e:  # noqa: BLE001 - best effort
        logger.warning("Failed to sign %s: %s", object_path, e)
        return None


def download(object_path: str) -> bytes | None:
    """Download an object stored as ``bucket/key``."""
    if not object_path or "/" not in object_path:
        return None
    bucket, key = object_path.split("/", 1)
    try:
        return get_client().storage.from_(bucket).download(key)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to download %s: %s", object_path, e)
        return None
