"""One-way notifications (Slack + WhatsApp).

Best-effort: a failure to notify never fails an audit. Notifications are sent
when an audit starts and when it finishes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any
import json

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# TODO: Fix slack integration error
@lru_cache(maxsize=1)
def _slack():
    from slack_sdk import WebClient
    return WebClient(token=settings.slack_bot_token)

@lru_cache(maxsize=1)
def _twilio():
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _send_slack(text: str) -> None:
    if not (settings.slack_bot_token and settings.slack_channel):
        return
    try:
        _slack().chat_postMessage(channel=settings.slack_channel, text=text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Slack notify failed: %s", e)


def _send_whatsapp(text: str) -> None:
    if not (settings.twilio_account_sid and settings.twilio_whatsapp_from and settings.notify_whatsapp_to):
        return
    try:
        _twilio().messages.create(
            from_=settings.twilio_whatsapp_from,
            to=settings.notify_whatsapp_to,
            content_sid="HXb5b62575e6e4ff6129ad7c8efe1f983e",
            content_variables=json.dumps({"1": "Audit completed.", "2": text})
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("WhatsApp notify failed: %s", e)


def _broadcast(text: str) -> None:
    _send_slack(text)
    _send_whatsapp(text)


def notify_started(audit: dict[str, Any]) -> None:
    _broadcast(f"🔍 Pattern Proof audit #{audit['id']} started for {audit['url']}")


def notify_completed(audit: dict[str, Any]) -> None:
    report_url = f"{settings.public_base_url}/api/audits/{audit['id']}/report"
    status = audit.get("status", "completed")
    icon = "✅" if status == "completed" else "⚠️"
    _broadcast(
        f"{icon} Pattern Proof audit #{audit['id']} for {audit['url']} finished "
        f"({status}). Report: {report_url}"
    )
