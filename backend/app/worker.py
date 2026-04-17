from celery import Celery

from app.core.config import settings

celery_app = Celery("pattern_proof", broker=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="run_audit")
def run_audit(audit_id: int):
    """Orchestrate a full dark-pattern audit pipeline.

    Steps:
      1. Crawl the website (collect pages, screenshots, HTML)
      2. Run the LangGraph agent system (static + dynamic DP detection)
      3. Build and persist the report
      4. Mark audit as completed
    """
    # TODO: implement in Phase 6
    pass
