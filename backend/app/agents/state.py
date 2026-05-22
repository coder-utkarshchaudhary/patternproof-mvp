"""LangGraph state schema for the dark pattern audit pipeline."""

from typing import Annotated

from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from app.core.config import settings


class PageContext(BaseModel):
    page_id: int | None = None  # audit_pages.id once persisted
    url: str
    title: str | None = None
    screenshot_path: str | None = None  # Supabase Storage object key (bucket/key)
    html_path: str | None = None  # Supabase Storage object key
    visible_text: str | None = None
    depth: int = 0
    # Set by the static detector to drive the manager's feedback loop.
    analyzed: bool = False
    analysis_ok: bool = True


class Ticket(BaseModel):
    """A task ticket produced by the Planner."""

    id: int
    title: str
    detail: str
    priority: str = "normal"  # low | normal | high


class DetectedFinding(BaseModel):
    category: str
    dp_type: str
    ccpa_pattern: str | None = None
    severity: str  # low, medium, high
    title: str
    description: str
    explanation: str | None = None
    evidence_screenshot_path: str | None = None
    bounding_box: dict | None = None
    confidence_score: float | None = None
    is_dynamic: bool = False
    page_url: str | None = None
    page_id: int | None = None
    source: str = "visual"  # visual | semantic


class AuditState(BaseModel):
    """Top-level state flowing through the LangGraph audit graph."""

    # Core identifiers
    audit_id: int
    target_url: str

    # Messaging (for LLM conversation history)
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Planner output
    tickets: list[Ticket] = Field(default_factory=list)
    agent_notes: list[str] = Field(default_factory=list)

    # Crawl state
    current_page: PageContext | None = None
    visited_pages: list[PageContext] = Field(default_factory=list)
    pending_pages: list[PageContext] = Field(default_factory=list)  # awaiting analysis

    # Results
    findings: list[DetectedFinding] = Field(default_factory=list)

    # Control
    next_action: str = "manager"
    iteration_count: int = 0
    max_iterations: int = Field(default_factory=lambda: settings.agent_max_iterations)
    feedback_count: int = 0
    is_complete: bool = False
