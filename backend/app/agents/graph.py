"""LangGraph workflow for the dark-pattern audit pipeline.

Manager–slave (supervisor) topology: the Claude-backed manager routes to slave
nodes and they return to the manager, forming the feedback loop. Static-only
for the MVP; dynamic multi-page flow nodes can be added as new branches.
"""

from langgraph.graph import END, StateGraph

from app.agents.crawler_agent import crawler_node
from app.agents.manager import manager_node
from app.agents.planner import planner_node
from app.agents.report_agent import report_node
from app.agents.state import AuditState
from app.agents.static_detector import static_detector_node


def _route(state: AuditState) -> str:
    """Conditional edge from the manager based on its decision."""
    if state.is_complete or state.next_action == "complete":
        return END
    return state.next_action


def build_audit_graph():
    graph = StateGraph(AuditState)

    graph.add_node("manager", manager_node)
    graph.add_node("plan", planner_node)
    graph.add_node("crawl", crawler_node)
    graph.add_node("static_analysis", static_detector_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("manager")

    graph.add_conditional_edges(
        "manager",
        _route,
        {
            "plan": "plan",
            "crawl": "crawl",
            "static_analysis": "static_analysis",
            "report": "report",
            END: END,
        },
    )

    # Slaves return to the manager; the report node terminates the run.
    graph.add_edge("plan", "manager")
    graph.add_edge("crawl", "manager")
    graph.add_edge("static_analysis", "manager")
    graph.add_edge("report", END)

    return graph.compile()


audit_graph = build_audit_graph()
