from langgraph.graph import StateGraph, END
from ..models.state import ClaimState
from ..agents.intake_agent import intake_agent
from ..agents.policy_agent import policy_agent
from ..agents.fraud_agent import fraud_agent
from ..agents.risk_agent import risk_agent
from ..agents.settlement_agent import settlement_agent
from ..core.telemetry import telemetry_manager

def traced_intake(state: ClaimState) -> ClaimState:
    """Wraps Intake Agent execution with OpenTelemetry tracing."""
    claim_id = state.get("claim_id", "UNKNOWN")
    with telemetry_manager.trace_agent("intake", claim_id) as span:
        result = intake_agent(state)
        if span and span.is_recording():
            span.set_attribute("claim.completeness", float(result.get("completeness", 0.0)))
            span.set_attribute("claim.status", str(result.get("current_status", "")))
            span.set_attribute("claim.missing_fields_count", len(result.get("missing_fields", [])))
        return result

def traced_policy(state: ClaimState) -> ClaimState:
    """Wraps Policy Agent execution with OpenTelemetry tracing."""
    claim_id = state.get("claim_id", "UNKNOWN")
    with telemetry_manager.trace_agent("policy", claim_id) as span:
        result = policy_agent(state)
        val = result.get("policy_validation", {})
        if span and span.is_recording():
            span.set_attribute("policy.eligible", bool(val.get("eligible", False)))
            span.set_attribute("policy.active", bool(val.get("active", False)))
            span.set_attribute("policy.deductible", float(val.get("deductible", 0.0)))
            span.set_attribute("policy.citations_count", len(val.get("citations", [])))
        return result

def traced_fraud(state: ClaimState) -> ClaimState:
    """Wraps Fraud Detection Agent execution with OpenTelemetry tracing."""
    claim_id = state.get("claim_id", "UNKNOWN")
    with telemetry_manager.trace_agent("fraud", claim_id) as span:
        result = fraud_agent(state)
        rep = result.get("fraud_report", {})
        if span and span.is_recording():
            span.set_attribute("fraud.score", float(rep.get("fraud_score", 0.0)))
            span.set_attribute("fraud.siu_escalate", bool(rep.get("siu_escalate", False)))
            span.set_attribute("fraud.flags_count", len(rep.get("flags", [])))
        return result

def traced_risk(state: ClaimState) -> ClaimState:
    """Wraps Risk Assessment Agent execution with OpenTelemetry tracing."""
    claim_id = state.get("claim_id", "UNKNOWN")
    with telemetry_manager.trace_agent("risk", claim_id) as span:
        result = risk_agent(state)
        ass = result.get("risk_assessment", {})
        if span and span.is_recording():
            span.set_attribute("risk.tier", str(ass.get("risk_tier", "HIGH")))
            span.set_attribute("risk.approved_estimate", float(ass.get("approved_estimate", 0.0)))
            span.set_attribute("risk.depreciation", float(ass.get("depreciation", 0.0)))
        return result

def traced_settle(state: ClaimState) -> ClaimState:
    """Wraps Settlement Agent execution with OpenTelemetry tracing."""
    claim_id = state.get("claim_id", "UNKNOWN")
    with telemetry_manager.trace_agent("settle", claim_id) as span:
        result = settlement_agent(state)
        dec = result.get("settlement_decision", {})
        if span and span.is_recording():
            span.set_attribute("settlement.status", str(dec.get("status", "")))
            span.set_attribute("settlement.payout", float(dec.get("proposed_payout", 0.0)))
            span.set_attribute("settlement.requires_human_approval", bool(dec.get("requires_human_approval", False)))
        return result

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
    
    # 1. Add Traced Agent Nodes
    workflow.add_node("intake", traced_intake)
    workflow.add_node("policy", traced_policy)
    workflow.add_node("fraud", traced_fraud)
    workflow.add_node("risk", traced_risk)
    workflow.add_node("settle", traced_settle)
    
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

