"""LangGraph workflow definition for the dark pattern audit pipeline.

Wires the supervisor and worker agents into a StateGraph with
conditional routing and checkpointing.
"""

from langgraph.graph import END, StateGraph

from app.agents.dynamic_dp_agents import (
    context_tracker_node,
    flow_navigator_node,
    obstruction_detector_node,
)
from app.agents.state import AuditState
from app.agents.static_dp_agent import static_dp_node
from app.agents.supervisor import supervisor_node


def route_next(state: AuditState) -> str:
    """Conditional edge: route based on supervisor's decision."""
    if state.is_complete:
        return END
    return state.next_action


def route_dynamic(state: AuditState) -> str:
    """Route within dynamic analysis based on flow type."""
    if state.flow_type == "cancel":
        return "obstruction_detector"
    return "context_tracker"


def build_audit_graph() -> StateGraph:
    """Build and compile the audit LangGraph."""
    graph = StateGraph(AuditState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("static_analysis", static_dp_node)
    graph.add_node("dynamic_flow", flow_navigator_node)
    graph.add_node("context_tracker", context_tracker_node)
    graph.add_node("obstruction_detector", obstruction_detector_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor routes to workers or END
    graph.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "static_analysis": "static_analysis",
            "dynamic_flow": "dynamic_flow",
            "crawl_next": "supervisor",  # loop back after crawling
            END: END,
        },
    )

    # Workers return to supervisor
    graph.add_edge("static_analysis", "supervisor")

    # Dynamic flow routes to sub-agents based on flow type
    graph.add_conditional_edges(
        "dynamic_flow",
        route_dynamic,
        {
            "context_tracker": "context_tracker",
            "obstruction_detector": "obstruction_detector",
        },
    )
    graph.add_edge("context_tracker", "supervisor")
    graph.add_edge("obstruction_detector", "supervisor")

    return graph.compile()


# Singleton compiled graph
audit_graph = build_audit_graph()
