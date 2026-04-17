import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AuditStatus(str, enum.Enum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DPCategory(str, enum.Enum):
    SNEAKING = "sneaking"
    URGENCY = "urgency"
    MISDIRECTION = "misdirection"
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    OBSTRUCTION = "obstruction"
    FORCED_ACTION = "forced_action"


class DPType(str, enum.Enum):
    HIDDEN_COSTS = "hidden_costs"
    HIDDEN_SUBSCRIPTION = "hidden_subscription"
    BAIT_AND_SWITCH = "bait_and_switch"
    COUNTDOWN_TIMER = "countdown_timer"
    LIMITED_TIME_MESSAGE = "limited_time_message"
    CONFIRMSHAMING = "confirmshaming"
    VISUAL_INTERFERENCE = "visual_interference"
    TRICK_QUESTION = "trick_question"
    FAKE_ACTIVITY = "fake_activity"
    FAKE_TESTIMONIAL = "fake_testimonial"
    LOW_STOCK_MESSAGE = "low_stock_message"
    HIGH_DEMAND_MESSAGE = "high_demand_message"
    HARD_TO_CANCEL = "hard_to_cancel"
    FORCED_ENROLLMENT = "forced_enrollment"
    PRESELECTION = "preselection"


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus), default=AuditStatus.QUEUED, nullable=False
    )
    progress_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    pages: Mapped[list["AuditPage"]] = relationship(back_populates="audit", cascade="all, delete")
    findings: Mapped[list["Finding"]] = relationship(back_populates="audit", cascade="all, delete")
    report: Mapped["Report | None"] = relationship(back_populates="audit", cascade="all, delete")


class AuditPage(Base):
    __tablename__ = "audit_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"))
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(500))
    html_snapshot_path: Mapped[str | None] = mapped_column(String(500))
    page_title: Mapped[str | None] = mapped_column(String(500))
    crawl_depth: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    audit: Mapped["Audit"] = relationship(back_populates="pages")
    findings: Mapped[list["Finding"]] = relationship(back_populates="page", cascade="all, delete")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"))
    page_id: Mapped[int | None] = mapped_column(ForeignKey("audit_pages.id", ondelete="SET NULL"))
    category: Mapped[DPCategory] = mapped_column(Enum(DPCategory), nullable=False)
    dp_type: Mapped[DPType] = mapped_column(Enum(DPType), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    evidence_screenshot_path: Mapped[str | None] = mapped_column(String(500))
    bounding_box: Mapped[dict | None] = mapped_column(JSON)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    is_dynamic: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    audit: Mapped["Audit"] = relationship(back_populates="findings")
    page: Mapped["AuditPage | None"] = relationship(back_populates="findings")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), unique=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(nullable=False)  # 0-100, 100 = clean
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    generated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    audit: Mapped["Audit"] = relationship(back_populates="report")
