import json
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models.state import ClaimState
from ..agents.intake_agent import intake_agent
from ..agents.policy_agent import policy_agent
from ..agents.fraud_agent import fraud_agent
from ..agents.risk_agent import risk_agent
from ..agents.settlement_agent import settlement_agent
from ..core.telemetry import telemetry_manager
from ..core.config import FRAUD_THRESHOLD_ESCALATION

# ------------------------------------------------------------------------------
# 1. Generic Traced Node Factory with Resilience & Error Routing
# ------------------------------------------------------------------------------
def create_traced_node(
    node_name: str,
    agent_fn: Callable[[ClaimState], Dict[str, Any]],
    attr_extractor: Optional[Callable[[Dict[str, Any], Any], None]] = None
) -> Callable[[ClaimState], Dict[str, Any]]:
    """
    Higher-order factory wrapping an insurance agent node with:
    - OpenTelemetry distributed span tracing
    - Agent-specific telemetry attribute injection
    - Exception handling and error routing into the claim state
    """
    def traced_node(state: ClaimState) -> Dict[str, Any]:
        claim_id = state.get("claim_id", "UNKNOWN")
        with telemetry_manager.trace_agent(node_name, claim_id) as span:
            try:
                delta = agent_fn(state)
                if span and span.is_recording() and attr_extractor:
                    attr_extractor(delta, span)
                return delta
            except Exception as e:
                err_msg = f"Error executing node '{node_name}': {str(e)}"
                if span and span.is_recording():
                    span.record_exception(e)
                    span.set_attribute("agent.error", str(e))
                    span.set_attribute("error", True)
                
                # Graceful recovery: route to human review rather than unhandled crash
                now_ts = datetime.now(timezone.utc).isoformat()
                event = {
                    "stage": node_name.upper(),
                    "event_type": "NODE_EXECUTION_FAILURE",
                    "route_reason": err_msg,
                    "evidence": {"exception": str(e), "node": node_name},
                    "timestamp": now_ts
                }
                return {
                    "errors": [err_msg],
                    "current_status": "ERROR_HALTED",
                    "route_reason": err_msg,
                    "human_review_required": True,
                    "human_review_type": "SYSTEM_ERROR",
                    "audit_events": [event]
                }
    return traced_node


# Telemetry Attribute Extractors
def extract_intake_telemetry(delta: Dict[str, Any], span: Any):
    span.set_attribute("claim.completeness", float(delta.get("completeness", 0.0)))
    span.set_attribute("claim.status", str(delta.get("current_status", "")))
    span.set_attribute("claim.missing_fields_count", len(delta.get("missing_fields", [])))

def extract_policy_telemetry(delta: Dict[str, Any], span: Any):
    val = delta.get("policy_validation", {})
    span.set_attribute("policy.eligible", bool(val.get("eligible", False)))
    span.set_attribute("policy.active", bool(val.get("active", False)))
    span.set_attribute("policy.deductible", float(val.get("deductible", 0.0)))
    span.set_attribute("policy.citations_count", len(val.get("citations", [])))

def extract_fraud_telemetry(delta: Dict[str, Any], span: Any):
    rep = delta.get("fraud_report", {})
    span.set_attribute("fraud.score", float(rep.get("fraud_score", 0.0)))
    span.set_attribute("fraud.siu_escalate", bool(rep.get("siu_escalate", False)))
    span.set_attribute("fraud.flags_count", len(rep.get("flags", [])))

def extract_risk_telemetry(delta: Dict[str, Any], span: Any):
    ass = delta.get("risk_assessment", {})
    span.set_attribute("risk.tier", str(ass.get("risk_tier", "HIGH")))
    span.set_attribute("risk.approved_estimate", float(ass.get("approved_estimate", 0.0)))
    span.set_attribute("risk.depreciation", float(ass.get("depreciation", 0.0)))

def extract_settle_telemetry(delta: Dict[str, Any], span: Any):
    dec = delta.get("settlement_decision", {})
    span.set_attribute("settlement.status", str(dec.get("status", "")))
    span.set_attribute("settlement.payout", float(dec.get("proposed_payout", 0.0)))
    span.set_attribute("settlement.requires_human_approval", bool(dec.get("requires_human_approval", False)))


# Node instances built via the generic factory
traced_intake = create_traced_node("intake", intake_agent, extract_intake_telemetry)
traced_policy = create_traced_node("policy", policy_agent, extract_policy_telemetry)
traced_fraud = create_traced_node("fraud", fraud_agent, extract_fraud_telemetry)
traced_risk = create_traced_node("risk", risk_agent, extract_risk_telemetry)
traced_settle = create_traced_node("settle", settlement_agent, extract_settle_telemetry)


# ------------------------------------------------------------------------------
# 2. Parallel Join / Evaluator Node
# ------------------------------------------------------------------------------
def fraud_risk_evaluator(state: ClaimState) -> Dict[str, Any]:
    """
    Synchronizes outputs from the parallel Fraud Detection and Risk Assessment nodes.
    Evaluates composite risk and determines whether to proceed to Settlement or route to SIU.
    """
    fraud_rep = state.get("fraud_report", {})
    risk_ass = state.get("risk_assessment", {})
    siu_escalate = fraud_rep.get("siu_escalate", False)
    score = fraud_rep.get("fraud_score", 0)
    risk_tier = risk_ass.get("risk_tier", "HIGH")
    now_ts = datetime.now(timezone.utc).isoformat()

    if siu_escalate:
        status = "PENDING_REVIEW"
        reason = f"Gate 3 Exit: High Fraud Risk (Score: {score} >= {FRAUD_THRESHOLD_ESCALATION}) — Escalated to SIU."
        event = {
            "stage": "FRAUD_RISK_EVALUATION",
            "event_type": "SIU_ESCALATION_JOIN",
            "route_reason": reason,
            "evidence": {
                "fraud_score": score,
                "risk_tier": risk_tier,
                "siu_escalate": True
            },
            "timestamp": now_ts
        }
        return {
            "current_status": status,
            "route_reason": reason,
            "human_review_required": True,
            "human_review_type": "SIU_FRAUD",
            "audit_events": [event]
        }
    else:
        status = "EVALUATED"
        reason = f"Gate 3 Pass: Parallel Fraud cleared (Score: {score} < {FRAUD_THRESHOLD_ESCALATION}) & Risk assessed ({risk_tier} Tier)."
        event = {
            "stage": "FRAUD_RISK_EVALUATION",
            "event_type": "EVALUATION_CONFIRMED",
            "route_reason": reason,
            "evidence": {
                "fraud_score": score,
                "risk_tier": risk_tier,
                "siu_escalate": False
            },
            "timestamp": now_ts
        }
        return {
            "current_status": status,
            "route_reason": reason,
            "audit_events": [event]
        }


# ------------------------------------------------------------------------------
# 3. Human-in-the-Loop (HITL) Graph Node
# ------------------------------------------------------------------------------
def human_review_node(state: ClaimState) -> Dict[str, Any]:
    """
    Human-in-the-Loop review stage within the LangGraph graph.
    Records review pending state or processes human review decisions upon workflow resumption.
    """
    human_dec = state.get("human_decision")
    now_ts = datetime.now(timezone.utc).isoformat()

    if human_dec:
        decision = human_dec.get("decision", "APPROVED")
        reviewer_id = human_dec.get("reviewer_id", "adjuster_01")
        notes = human_dec.get("notes", "")
        payout = human_dec.get("adjusted_payout")

        event = {
            "stage": "HUMAN_REVIEW",
            "event_type": f"DECISION_{decision}",
            "route_reason": f"Human reviewer ({reviewer_id}) recorded decision: {decision}",
            "evidence": {"reviewer": reviewer_id, "notes": notes, "payout": payout},
            "timestamp": now_ts
        }
        return {
            "human_review_required": False,
            "audit_events": [event]
        }

    # First entry: awaiting human action
    return {
        "human_review_required": True
    }


# ------------------------------------------------------------------------------
# 4. Conditional Edge Routers
# ------------------------------------------------------------------------------
def route_after_intake(state: ClaimState) -> str:
    """Gate 1: Incomplete data routes immediately to human_review with NEEDS_INFO."""
    if state.get("completeness", 0.0) < 1.0:
        return "human_review"
    return "policy"

def route_after_policy(state: ClaimState) -> List[str] | str:
    """
    Gate 2:
    - Ineligible policy bypasses fraud/risk to draft denial at settle node.
    - Eligible policy branches in parallel to BOTH Fraud Agent and Risk Agent.
    """
    policy_val = state.get("policy_validation", {})
    if not policy_val.get("eligible", False):
        return "settle"
    return ["fraud", "risk"]

def route_after_evaluator(state: ClaimState) -> str:
    """Gate 3: SIU fraud escalation routes to human_review (freeze); cleared claims proceed to settle."""
    fraud_rep = state.get("fraud_report", {})
    if fraud_rep.get("siu_escalate", False):
        return "human_review"
    return "settle"

def route_after_settle(state: ClaimState) -> str:
    """
    Gate 4:
    - Claims requiring human approval (adjuster queue or draft denial) route to human_review.
    - STP cleared claims complete at END.
    """
    settle_dec = state.get("settlement_decision", {})
    if settle_dec.get("requires_human_approval", False) or state.get("human_review_required", False):
        return "human_review"
    return END


# ------------------------------------------------------------------------------
# 5. Graph Assembly & Compilation
# ------------------------------------------------------------------------------
def build_claims_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Builds and compiles the production-grade LangGraph Claims Orchestrator:
    - Pure state delta updates
    - Parallel Fraud and Risk analysis
    - Explicit Human-in-the-Loop review node
    - State checkpointing for step-level auditability and resumption
    """
    workflow = StateGraph(ClaimState)
    
    # 1. Add Traced Agent & Functional Nodes
    workflow.add_node("intake", traced_intake)
    workflow.add_node("policy", traced_policy)
    workflow.add_node("fraud", traced_fraud)
    workflow.add_node("risk", traced_risk)
    workflow.add_node("evaluator", fraud_risk_evaluator)
    workflow.add_node("settle", traced_settle)
    workflow.add_node("human_review", human_review_node)
    
    # 2. Set Entry Point
    workflow.set_entry_point("intake")
    
    # 3. Add Conditional & Parallel Edges
    # Gate 1: Intake Completeness
    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "human_review": "human_review",
            "policy": "policy"
        }
    )
    
    # Gate 2: Policy Eligibility (Parallel branch to fraud & risk, or direct to settle)
    workflow.add_conditional_edges(
        "policy",
        route_after_policy,
        ["fraud", "risk", "settle"]
    )
    
    # Parallel Fan-In: Both fraud and risk converge at the evaluator join node
    workflow.add_edge("fraud", "evaluator")
    workflow.add_edge("risk", "evaluator")
    
    # Gate 3: Fraud/Risk Evaluator
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "human_review": "human_review",
            "settle": "settle"
        }
    )
    
    # Gate 4: Settlement -> Human Review or Clean STP End
    workflow.add_conditional_edges(
        "settle",
        route_after_settle,
        {
            "human_review": "human_review",
            END: END
        }
    )
    
    # Human Review ends graph execution awaiting or confirming decision
    workflow.add_edge("human_review", END)
    
    cp = checkpointer if checkpointer is not None else MemorySaver()
    return workflow.compile(checkpointer=cp)


# Global compiled orchestrator instance with checkpointing
claims_checkpointer = MemorySaver()
claims_graph = build_claims_graph(checkpointer=claims_checkpointer)


def resume_claim_workflow(
    claim_id: str,
    human_decision: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> ClaimState:
    """
    Resumes an existing checkpointed claim graph run by injecting human decision state.
    Recovers state from SQLite persistence if memory checkpoint was cleared (e.g., after server restart).
    """
    cfg = config or {"configurable": {"thread_id": claim_id}}

    # 1. Verify in-memory checkpoint state; if missing, recover from persistent SQLite store
    curr_state = claims_graph.get_state(cfg)
    if not curr_state or not curr_state.values:
        try:
            from ..db.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT state_json FROM claims WHERE claim_id = ?;", (claim_id,))
            row = cursor.fetchone()
            conn.close()
            if row and row["state_json"]:
                recovered_state = json.loads(row["state_json"])
                claims_graph.update_state(cfg, recovered_state)
        except Exception:
            pass

    # 2. Inject human decision and resume graph execution
    claims_graph.update_state(cfg, {
        "human_decision": human_decision,
        "human_review_resolved": True
    })
    return claims_graph.invoke(None, config=cfg)

