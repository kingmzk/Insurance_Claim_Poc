from langgraph.graph import StateGraph, END
from ..models.state import ClaimState
from ..agents.intake_agent import intake_agent
from ..agents.policy_agent import policy_agent
from ..agents.fraud_agent import fraud_agent
from ..agents.risk_agent import risk_agent
from ..agents.settlement_agent import settlement_agent

def route_after_intake(state: ClaimState) -> str:
    """Gate 1: Incomplete data halts immediately with NEEDS_INFO."""
    if state.get("completeness", 0.0) < 1.0:
        return END
    return "policy"

def route_after_policy(state: ClaimState) -> str:
    """Gate 2: Ineligible/excluded policy bypasses fraud/risk to draft denial."""
    policy_val = state.get("policy_validation", {})
    if not policy_val.get("eligible", False):
        return "settle"
    return "fraud"

def route_after_fraud(state: ClaimState) -> str:
    """Gate 3: High fraud risk (>=75) halts immediately for SIU review."""
    fraud_rep = state.get("fraud_report", {})
    if fraud_rep.get("siu_escalate", False):
        return END
    return "risk"

def build_claims_graph():
    """Builds and compiles the 5-Agent LangGraph Claims Orchestrator."""
    workflow = StateGraph(ClaimState)
    
    # 1. Add Agent Nodes
    workflow.add_node("intake", intake_agent)
    workflow.add_node("policy", policy_agent)
    workflow.add_node("fraud", fraud_agent)
    workflow.add_node("risk", risk_agent)
    workflow.add_node("settle", settlement_agent)
    
    # 2. Set Entry Point
    workflow.set_entry_point("intake")
    
    # 3. Add Conditional Edges
    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            END: END,
            "policy": "policy"
        }
    )
    
    workflow.add_conditional_edges(
        "policy",
        route_after_policy,
        {
            "fraud": "fraud",
            "settle": "settle"
        }
    )
    
    workflow.add_conditional_edges(
        "fraud",
        route_after_fraud,
        {
            END: END,
            "risk": "risk"
        }
    )
    
    # 4. Standard Edges
    workflow.add_edge("risk", "settle")
    workflow.add_edge("settle", END)
    
    return workflow.compile()

# Global compiled orchestrator instance
claims_graph = build_claims_graph()
