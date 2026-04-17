"""LangGraph state schema for the dark pattern audit pipeline."""

from typing import Annotated

from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class PageContext(BaseModel):
    url: str
    title: str | None = None
    screenshot_path: str | None = None
    html_path: str | None = None
    visible_text: str | None = None


class DetectedFinding(BaseModel):
    category: str
    dp_type: str
    severity: str  # low, medium, high
    title: str
    description: str
    explanation: str | None = None
    evidence_screenshot_path: str | None = None
    bounding_box: dict | None = None
    confidence_score: float | None = None
    is_dynamic: bool = False
    page_url: str | None = None


class AuditState(BaseModel):
    """Top-level state flowing through the LangGraph audit graph."""

    # Core identifiers
    audit_id: int
    target_url: str

    # Messaging (for LLM conversation history)
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Crawl state
    current_page: PageContext | None = None
    visited_pages: list[PageContext] = Field(default_factory=list)
    crawl_queue: list[str] = Field(default_factory=list)

    # Flow tracking (for dynamic DP detection)
    flow_type: str | None = None  # checkout, signup, cancel, browse
    interaction_history: list[dict] = Field(default_factory=list)

    # Results
    findings: list[DetectedFinding] = Field(default_factory=list)

    # Control
    next_action: str = "supervisor"  # which node to route to next
    iteration_count: int = 0
    max_iterations: int = 50
    is_complete: bool = False
