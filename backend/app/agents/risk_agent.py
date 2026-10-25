from datetime import datetime, timezone
from ..models.state import ClaimState
from ..services.cost_service import CostService

def risk_agent(state: ClaimState) -> ClaimState:
    """
    Risk Assessment Agent: Benchmarks repair line items against OEM parts catalog
    and labor guides, applies component depreciation, and assigns a risk tier.
    """
    intake = state.get("intake_data", {})
    claimed_amt = float(intake.get("claimed_amt", 0.0))
    loss_type = intake.get("loss_type", "collision")
    make_model = intake.get("vehicle_make_model", "")
    
    valuation = CostService.benchmark_repair(claimed_amt, loss_type, make_model)
    
    risk_assessment = {
        "claimed_amount": claimed_amt,
        "approved_estimate": valuation["approved_estimate"],
        "depreciation": valuation["depreciation"],
        "risk_tier": valuation["risk_tier"],
        "valuation_notes": valuation["valuation_notes"]
    }
    
    state["risk_assessment"] = risk_assessment
    audit_events = state.get("audit_events", [])
    
    state["current_status"] = "RISK_ASSESSED"
    state["route_reason"] = f"Risk Assessment Complete: Assigned {valuation['risk_tier']} Risk Tier."
    audit_events.append({
        "stage": "RISK_ASSESSMENT",
        "event_type": "RISK_ASSESSED",
        "route_reason": state["route_reason"],
        "evidence": {
            "approved_estimate": valuation["approved_estimate"],
            "depreciation": valuation["depreciation"],
            "risk_tier": valuation["risk_tier"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    state["audit_events"] = audit_events
    return state
