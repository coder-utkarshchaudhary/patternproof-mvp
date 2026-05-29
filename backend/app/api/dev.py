"""Development-only utilities.

All routes here return 403 when PP_DEBUG is False so they can be registered
unconditionally without any risk of exposure in production.
"""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db import repo

logger = get_logger(__name__)
router = APIRouter(tags=["dev"])


def _require_debug() -> None:
    if not settings.debug:
        raise HTTPException(status_code=403, detail="This endpoint is only available in debug mode.")


@router.post("/dev/reset", status_code=200)
def reset_dev_data():
    """Truncate all audit data and restart identity sequences (debug only).

    Equivalent to running:
        TRUNCATE ticket_archive, agent_memory, tickets, findings,
                 reports, audit_pages, audits
        RESTART IDENTITY CASCADE;

    After this call the next audit will receive id=1.
    """
    _require_debug()
    try:
        repo.reset_dev_data()
        logger.info("Dev reset: all audit tables truncated and sequences restarted")
    except Exception as e:  # noqa: BLE001
        logger.error("Dev reset failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reset failed: {e}") from e
    return {"reset": True, "message": "All audit data cleared. Next audit_id will be 1."}
