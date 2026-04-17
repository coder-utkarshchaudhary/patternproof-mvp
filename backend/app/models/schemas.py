from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.database import AuditStatus, DPCategory, DPType, Severity


# ── Audit ────────────────────────────────────────────────────────────────

class AuditCreate(BaseModel):
    url: HttpUrl


class AuditProgress(BaseModel):
    status: AuditStatus
    progress_message: str | None = None


class AuditPageOut(BaseModel):
    id: int
    page_url: str
    page_title: str | None = None
    screenshot_path: str | None = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: int
    url: str
    status: AuditStatus
    progress_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class AuditDetail(AuditOut):
    pages: list[AuditPageOut] = []


# ── Finding ──────────────────────────────────────────────────────────────

class FindingOut(BaseModel):
    id: int
    page_id: int | None = None
    category: DPCategory
    dp_type: DPType
    severity: Severity
    title: str
    description: str
    explanation: str | None = None
    evidence_screenshot_path: str | None = None
    bounding_box: dict | None = None
    confidence_score: float | None = None
    is_dynamic: bool

    model_config = {"from_attributes": True}


# ── Report ───────────────────────────────────────────────────────────────

class ReportOut(BaseModel):
    id: int
    audit_id: int
    summary: str
    score: int
    pdf_path: str | None = None
    generated_at: datetime
    findings: list[FindingOut] = []

    model_config = {"from_attributes": True}
