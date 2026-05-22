import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audits, reports, ws
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging(debug=settings.debug)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audits.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(ws.router)


@app.on_event("startup")
def _startup() -> None:
    logger.info("Pattern Proof API starting up (debug=%s)", settings.debug)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
